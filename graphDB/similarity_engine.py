"""
교과목 유사도/관계 계산 엔진 (순수 계산 — Neo4j/IO 없음).

기존 CourseGraphBuilder 가 한 클래스에서 하던 일 중 '계산' 책임만 떼어낸 것이다.
DB 쓰기는 graph_repository.GraphWriter, 조회는 GraphReader 가 담당한다.

설계 포인트
  - 임베딩 모델은 지연 로딩 + 주입 가능(model=) → 모델 다운로드 없이 단위 테스트 가능.
  - TF-IDF 하이브리드 상태(_tfidf_vectorizer, _tfidf_vectors)를 __init__ 에서 명시적으로
    초기화 → 예전의 hasattr 기반 암묵적 시간 결합 제거.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from text_features import (
    PREREQ_STOPWORDS,
    PRODUCTION_MODEL_NAME,
    STOPWORDS,
    build_outline_tfidf,
    filter_stopwords,
    filter_stopwords_many,
    is_sequential_course,
)

logger = logging.getLogger(__name__)

# 엣지 타입 별칭 (가독성)
SimilarityEdge = Tuple[int, int, float]              # (i, j, similarity)
IdenticalIdEdge = Tuple[int, int, str, str]          # (i, j, dept_i, dept_j)
PrereqEdge = Tuple[int, int, float, str]             # (source, target, sim, raw_text)


def load_course_data(csv_path: str) -> pd.DataFrame:
    """
    교과목 CSV 로드 + feature_text 컬럼(교과목 이름 + 교과목개요) 생성.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["feature_text"] = df["교과목 이름"] + " " + df["교과목개요"].fillna("")

    if "학수번호" not in df.columns:
        logger.info("데이터 로드 완료: %d개 교과목 (학수번호 컬럼 없음)", len(df))
        return df

    # 보강된 학수번호의 빈 셀은 CSV 왕복 시 NaN 으로 로딩된다. 다운스트림(엔진/라이터)이
    # 일관된 문자열만 보도록 여기서 "" 로 정규화한다. (NaN 코드가 노드 code 로 새는 것 방지)
    df["학수번호"] = df["학수번호"].fillna("").astype(str).str.strip().replace({"nan": ""})

    # 여러 학과가 공유하는 학수번호 개수(빈 코드는 제외)
    non_empty = df[df["학수번호"] != ""]
    shared = non_empty.groupby("학수번호")["설강학과"].nunique()
    n_shared = int((shared > 1).sum())
    logger.info("데이터 로드 완료: %d개 교과목 (학수번호 보유 %d개, 여러 학과 공유 %d개)",
                len(df), len(non_empty), n_shared)
    return df


class SimilarityEngine:
    """교과목 임베딩·유사도·관계 계산 (순수)."""

    def __init__(
        self,
        model_name: str = PRODUCTION_MODEL_NAME,
        hybrid_weight: float = 0.7,
        model=None,
    ):
        self.model_name = model_name
        self.hybrid_weight = hybrid_weight
        self._model = model
        # 하이브리드 상태(명시적 초기화)
        self._tfidf_vectorizer = None
        self._tfidf_vectors: Optional[np.ndarray] = None

    @property
    def model(self):
        """SentenceTransformer 지연 로딩(주입되지 않은 경우에만 실제 로드)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("임베딩 모델 로드: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def uses_hybrid(self) -> bool:
        return self._tfidf_vectors is not None

    # ── 임베딩 ─────────────────────────────────────────────────────────
    def create_embeddings(
        self, df: pd.DataFrame, use_tfidf_weighting: bool = True
    ) -> np.ndarray:
        """
        feature_text 를 임베딩. use_tfidf_weighting=True 면 TF-IDF 하이브리드 상태를
        구성하고 정규화된 임베딩을 반환한다.
        """
        texts = df["feature_text"].tolist()
        texts_filtered = filter_stopwords_many(texts, STOPWORDS)

        logger.info("임베딩 생성 중... (상투적 표현 %d개 제거)", len(STOPWORDS))
        embeddings = self.model.encode(
            texts_filtered, batch_size=32, show_progress_bar=True, convert_to_numpy=True
        )

        if use_tfidf_weighting:
            embeddings = self._build_hybrid_state(texts, embeddings)
            logger.info("TF-IDF 하이브리드 구성 완료 (임베딩 %.0f%% + TF-IDF %.0f%%)",
                        self.hybrid_weight * 100, (1 - self.hybrid_weight) * 100)

        logger.info("임베딩 생성 완료: shape=%s", embeddings.shape)
        return embeddings

    def _build_hybrid_state(self, texts: List[str], embeddings: np.ndarray) -> np.ndarray:
        """
        TF-IDF 벡터라이저/벡터를 계산해 하이브리드 유사도용 상태로 보관하고,
        정규화된 임베딩을 반환한다.
        """
        tfidf = build_outline_tfidf()
        tfidf_dense = tfidf.fit_transform(texts).toarray()
        logger.info("  - TF-IDF 어휘 크기: %d", len(tfidf.get_feature_names_out()))

        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        tfidf_norm = tfidf_dense / (np.linalg.norm(tfidf_dense, axis=1, keepdims=True) + 1e-8)

        self._tfidf_vectorizer = tfidf
        self._tfidf_vectors = tfidf_norm
        return emb_norm

    # ── 유사도 엣지 ────────────────────────────────────────────────────
    def compute_similarity(
        self, df: pd.DataFrame, embeddings: np.ndarray, threshold: float = 0.7
    ) -> List[SimilarityEdge]:
        """
        코사인 유사도 엣지 생성. 같은 학수번호 쌍과 연계과목(1,2 시리즈) 쌍은 제외.
        상삼각만 벡터로 뽑아 임계값 이상 후보에 대해서만 제외 규칙을 검사한다.
        """
        logger.info("유사도 계산 중... (임계값: %s)", threshold)
        similarity_matrix = self._similarity_matrix(embeddings)

        codes = df["학수번호"].tolist() if "학수번호" in df.columns else [""] * len(df)
        names = df["교과목 이름"].tolist()
        n = len(similarity_matrix)

        iu, ju = np.triu_indices(n, k=1)
        sims = similarity_matrix[iu, ju]
        above = np.nonzero(sims >= threshold)[0]

        edges: List[SimilarityEdge] = []
        same_code_skipped = sequential_skipped = 0
        for k in above:
            i, j = int(iu[k]), int(ju[k])
            if codes[i] and codes[i] == codes[j]:
                same_code_skipped += 1
                continue
            if is_sequential_course(names[i], names[j]):
                sequential_skipped += 1
                continue
            edges.append((i, j, float(sims[k])))

        logger.info("유사도 엣지 %d개 (임계값 이상 후보 중 같은 학수번호 %d, 연계과목 %d 제외)",
                    len(edges), same_code_skipped, sequential_skipped)
        return edges

    def _similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """임베딩(+하이브리드) 코사인 유사도 행렬."""
        sim_emb = cosine_similarity(embeddings)
        if not self.uses_hybrid:
            return sim_emb
        sim_tfidf = cosine_similarity(self._tfidf_vectors)
        w = self.hybrid_weight
        logger.info("  - 하이브리드 유사도: 임베딩 %.0f%% + TF-IDF %.0f%%", w * 100, (1 - w) * 100)
        return w * sim_emb + (1 - w) * sim_tfidf

    # ── 동일 학수번호(다른 학과) 엣지 ─────────────────────────────────
    def compute_identical_id_edges(self, df: pd.DataFrame) -> List[IdenticalIdEdge]:
        """학수번호는 같으나 설강학과가 다른 교과목 쌍."""
        if "학수번호" not in df.columns:
            logger.info("학수번호 컬럼이 없어 동일 학수번호 엣지 계산을 생략합니다.")
            return []

        codes = df["학수번호"].tolist()
        depts = df["설강학과"].tolist()

        code_to_indices: dict = {}
        for idx, code in enumerate(codes):
            # 빈/결측 학수번호는 그룹핑에서 제외한다. (미매칭 과목의 빈 코드끼리
            # 묶여 가짜 IDENTICAL_ID 엣지가 생기는 것을 방지)
            if pd.isna(code) or str(code).strip() == "":
                continue
            code_to_indices.setdefault(code, []).append(idx)

        edges: List[IdenticalIdEdge] = []
        for indices in code_to_indices.values():
            if len(indices) < 2:
                continue
            for a in range(len(indices)):
                for b in range(a + 1, len(indices)):
                    i, j = indices[a], indices[b]
                    if depts[i] != depts[j]:
                        edges.append((i, j, depts[i], depts[j]))

        logger.info("동일 학수번호 엣지 %d개", len(edges))
        return edges

    # ── 선수강 매핑 엣지 ──────────────────────────────────────────────
    def compute_prerequisite_edges(
        self, df: pd.DataFrame, course_embeddings: np.ndarray, threshold: float = 0.7
    ) -> Tuple[List[PrereqEdge], dict]:
        """
        선수강 과목 텍스트를 파싱해 (1) 정확 일치, (2) 임베딩/TF-IDF 하이브리드
        의미 매칭으로 교과목 노드에 연결한다. 미매칭 텍스트는 unmapped 로 반환.

        미매칭 후보 항목들을 모아 '한 번에' 인코딩하여 예전의 항목별 encode 병목을 제거.
        """
        logger.info("선수강 과목 매핑 중... (임계값: %s)", threshold)

        col = "선수강 과목" if "선수강 과목" in df.columns else "선수강과목"
        if col not in df.columns:
            logger.info("선수강 과목 컬럼을 찾을 수 없습니다.")
            return [], {}

        names_clean = [str(n).strip().replace(" ", "").lower() for n in df["교과목 이름"]]
        name_to_idx = {name: idx for idx, name in enumerate(names_clean)}

        edges: List[PrereqEdge] = []
        unmapped: dict = {}
        exact = 0
        # 의미 매칭 후보: (course_idx, raw_item, filtered_item)
        pending: List[Tuple[int, str, str]] = []

        for idx, row in df.iterrows():
            prereq_text = row.get(col)
            if pd.isna(prereq_text) or str(prereq_text).strip() == "":
                continue
            for raw in (item.strip() for item in str(prereq_text).split(",")):
                if not raw:
                    continue
                clean = raw.replace(" ", "").lower()
                if clean in name_to_idx:  # 1) 정확 일치
                    edges.append((idx, name_to_idx[clean], 1.0, raw))
                    exact += 1
                    continue
                filtered = filter_stopwords(raw, PREREQ_STOPWORDS)  # 2) 의미 매칭 후보
                if filtered:
                    pending.append((idx, raw, filtered))
                else:
                    unmapped.setdefault(idx, []).append(raw)

        semantic = self._match_pending_prerequisites(
            pending, course_embeddings, threshold, edges, unmapped
        )

        unmapped_count = sum(len(v) for v in unmapped.values())
        logger.info("선수강 매핑 완료: 정확 %d / 의미 %d / 미매핑 %d",
                    exact, semantic, unmapped_count)
        return edges, unmapped

    def _match_pending_prerequisites(
        self,
        pending: List[Tuple[int, str, str]],
        course_embeddings: np.ndarray,
        threshold: float,
        edges: List[PrereqEdge],
        unmapped: dict,
    ) -> int:
        """의미 매칭 후보를 배치 인코딩해 best-match 를 찾는다. 매칭 건수 반환."""
        if not pending:
            return 0

        filtered_items = [f for _, _, f in pending]
        item_emb = self.model.encode(filtered_items, convert_to_numpy=True)
        item_emb = item_emb / (np.linalg.norm(item_emb, axis=1, keepdims=True) + 1e-8)
        sim_emb = cosine_similarity(item_emb, course_embeddings)  # (P, n_courses)

        if self.uses_hybrid and self._tfidf_vectorizer is not None:
            item_tfidf = self._tfidf_vectorizer.transform(filtered_items).toarray()
            item_tfidf = item_tfidf / (np.linalg.norm(item_tfidf, axis=1, keepdims=True) + 1e-8)
            sim_tfidf = cosine_similarity(item_tfidf, self._tfidf_vectors)
            w = self.hybrid_weight
            sim_final = w * sim_emb + (1 - w) * sim_tfidf
        else:
            sim_final = sim_emb

        best_idx = sim_final.argmax(axis=1)
        best_score = sim_final[np.arange(len(pending)), best_idx]

        semantic = 0
        for p, (course_idx, raw, _) in enumerate(pending):
            score = float(best_score[p])
            if score >= threshold:
                edges.append((course_idx, int(best_idx[p]), score, raw))
                semantic += 1
            else:
                unmapped.setdefault(course_idx, []).append(raw)
        return semantic
