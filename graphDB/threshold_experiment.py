"""
교과목 유사도 threshold 최적화 실험

실험 1: 순수 S-BERT threshold 분석
         - GT: 교과목개요 TF-IDF >= 0.30
         - 대상: 순수 SBERT 점수
실험 2: 프로덕션 하이브리드 threshold 검증
         - GT: 교과목 이름 TF-IDF(char n-gram) >= 0.30  ← 독립적
         - 대상: 현재 하이브리드(SBERT 70% + TF-IDF 30%)
실험 3: 하이브리드 비율(α) × threshold grid search
         - GT: 실험 2와 동일
         - 대상: α * SBERT + (1-α) * TF-IDF
"""

import argparse
import os
import re
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')  # 헤드리스 환경 대응
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


STOPWORDS = {
    '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
    '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
    '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
    '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
    '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
    '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
    '이', '그', '저', '것', '수', '등', '및', '또', '더', '매우',
}


class ThresholdExperiment:
    """교과목 유사도 threshold 최적화 실험"""

    def __init__(
        self,
        csv_path: str,
        model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    ):
        self.csv_path = csv_path
        self.model_name = model_name
        self.df: pd.DataFrame | None = None
        self.model: SentenceTransformer | None = None

        # 캐시 (한 번만 계산)
        self._valid_pairs: list[tuple[int, int]] | None = None
        self._sbert_emb: np.ndarray | None = None
        self._tfidf_outline_vecs: np.ndarray | None = None

    # ─────────────────────────────────────────────────────────────
    # 데이터 로드
    # ─────────────────────────────────────────────────────────────

    def load_data(self) -> None:
        self.df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        print(f"데이터 로드 완료: {len(self.df)}개 교과목")

    # ─────────────────────────────────────────────────────────────
    # 공통 유틸
    # ─────────────────────────────────────────────────────────────

    def _filter_stopwords(self, texts: list[str]) -> list[str]:
        return [
            ' '.join(w for w in t.split() if w not in STOPWORDS and len(w) > 1)
            for t in texts
        ]

    def _load_model(self) -> None:
        if self.model is None:
            print(f"모델 로드 중: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print("모델 로드 완료")

    def _compute_sbert_embeddings(self) -> np.ndarray:
        """순수 SBERT 임베딩 (캐시)"""
        if self._sbert_emb is not None:
            return self._sbert_emb

        self._load_model()
        texts = self.df['교과목개요'].fillna('').tolist()
        texts_filtered = self._filter_stopwords(texts)

        print("SBERT 임베딩 생성 중...")
        emb = self.model.encode(
            texts_filtered,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        emb = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-8)
        self._sbert_emb = emb
        return emb

    def _fit_tfidf_outline(self) -> np.ndarray:
        """교과목개요 TF-IDF 벡터 (캐시)"""
        if self._tfidf_outline_vecs is not None:
            return self._tfidf_outline_vecs

        texts = self.df['교과목개요'].fillna('').tolist()
        tfidf = TfidfVectorizer(
            max_features=3000, min_df=2, max_df=0.7,
            sublinear_tf=True, ngram_range=(1, 2),
        )
        mat = tfidf.fit_transform(texts).toarray()
        mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)
        self._tfidf_outline_vecs = mat
        print(f"교과목개요 TF-IDF 완료: 어휘 크기 {len(tfidf.get_feature_names_out())}")
        return mat

    def _fit_tfidf_name(self) -> np.ndarray:
        """교과목 이름 char n-gram TF-IDF (실험 2, 3 GT용 — 개요와 독립적)"""
        names = self.df['교과목 이름'].fillna('').tolist()
        tfidf = TfidfVectorizer(
            analyzer='char_wb', ngram_range=(2, 4), min_df=1,
        )
        mat = tfidf.fit_transform(names).toarray()
        mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)
        print(f"교과목 이름 TF-IDF(char n-gram) 완료: 어휘 크기 {len(tfidf.get_feature_names_out())}")
        return mat

    # ─────────────────────────────────────────────────────────────
    # 연계과목 / 유효 쌍
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_sequential_course(name1: str, name2: str) -> bool:
        def get_base(name: str) -> str:
            base = re.sub(r'[0-9IⅠⅡ]+$', '', name.strip())
            base = re.sub(r'\([^)]*\)$', '', base.strip())
            return base.strip()

        def get_seq(name: str) -> str | None:
            m = re.search(r'([0-9IⅠⅡ]+)$', name.strip())
            if m:
                return (m.group(1)
                        .replace('Ⅰ', '1').replace('Ⅱ', '2')
                        .replace('I', '1').replace('II', '2'))
            return None

        b1, b2 = get_base(name1), get_base(name2)
        s1, s2 = get_seq(name1), get_seq(name2)
        return bool(b1 == b2 and s1 and s2 and s1 != s2)

    def _get_valid_pairs(self) -> list[tuple[int, int]]:
        """같은 학수번호 / 연계과목 제외한 유효 쌍 (캐시)"""
        if self._valid_pairs is not None:
            return self._valid_pairs

        codes = self.df['학수번호'].tolist()
        names = self.df['교과목 이름'].tolist()
        n = len(self.df)

        pairs: list[tuple[int, int]] = []
        skipped_code = skipped_seq = 0
        for i in range(n):
            for j in range(i + 1, n):
                if codes[i] == codes[j]:
                    skipped_code += 1
                    continue
                if self._is_sequential_course(names[i], names[j]):
                    skipped_seq += 1
                    continue
                pairs.append((i, j))

        print(f"유효 쌍: {len(pairs)}개 (학수번호 중복 {skipped_code}쌍, 연계과목 {skipped_seq}쌍 제외)")
        self._valid_pairs = pairs
        return pairs

    # ─────────────────────────────────────────────────────────────
    # GT 생성
    # ─────────────────────────────────────────────────────────────

    def _build_gt_outline_tfidf(
        self, pairs: list[tuple[int, int]], threshold: float = 0.30
    ) -> np.ndarray:
        """실험 1 GT: 교과목개요 TF-IDF >= threshold"""
        vecs = self._fit_tfidf_outline()
        sim = cosine_similarity(vecs)
        labels = np.array([1 if sim[i][j] >= threshold else 0 for i, j in pairs])
        pos = labels.sum()
        print(f"GT(개요 TF-IDF >= {threshold}): 유사 쌍 {pos}개 / {len(labels)}개 ({pos/len(labels)*100:.1f}%)")
        return labels

    def _build_gt_name_tfidf(
        self, pairs: list[tuple[int, int]], threshold: float = 0.30
    ) -> np.ndarray:
        """실험 2, 3 GT: 교과목 이름 char n-gram TF-IDF >= threshold"""
        vecs = self._fit_tfidf_name()
        sim = cosine_similarity(vecs)
        labels = np.array([1 if sim[i][j] >= threshold else 0 for i, j in pairs])
        pos = labels.sum()
        print(f"GT(이름 TF-IDF >= {threshold}): 유사 쌍 {pos}개 / {len(labels)}개 ({pos/len(labels)*100:.1f}%)")
        return labels

    # ─────────────────────────────────────────────────────────────
    # 지표 계산
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _metrics(scores: np.ndarray, labels: np.ndarray, threshold: float) -> dict:
        pred = (scores >= threshold).astype(int)
        tp = int(((pred == 1) & (labels == 1)).sum())
        fp = int(((pred == 1) & (labels == 0)).sum())
        fn = int(((pred == 0) & (labels == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        return {
            'threshold': threshold,
            'precision': round(precision, 4),
            'recall':    round(recall,    4),
            'f1':        round(f1,        4),
            'n_pred': int(pred.sum()),
            'tp': tp, 'fp': fp, 'fn': fn,
        }

    # ─────────────────────────────────────────────────────────────
    # 실험 1: 순수 S-BERT threshold 분석
    # ─────────────────────────────────────────────────────────────

    def run_experiment1(
        self,
        thresholds: list[float] | None = None,
        gt_tfidf_threshold: float = 0.30,
        output_dir: str = 'graphDB/results/exp1',
    ) -> pd.DataFrame:
        if thresholds is None:
            thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

        print("\n" + "=" * 60)
        print("실험 1: 순수 S-BERT threshold 분석")
        print("=" * 60)
        os.makedirs(output_dir, exist_ok=True)

        pairs = self._get_valid_pairs()
        emb   = self._compute_sbert_embeddings()

        sim_mat = cosine_similarity(emb)
        scores  = np.array([sim_mat[i][j] for i, j in pairs])
        labels  = self._build_gt_outline_tfidf(pairs, gt_tfidf_threshold)

        rows = [self._metrics(scores, labels, t) for t in thresholds]
        df_result = pd.DataFrame(rows)
        df_result.to_csv(f'{output_dir}/exp1_metrics.csv', index=False)
        print("\n" + df_result[['threshold', 'precision', 'recall', 'f1', 'n_pred']].to_string(index=False))

        # 그래프 1: P / R / F1 커브
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(df_result['threshold'], df_result['precision'], 'o-', label='Precision')
        ax.plot(df_result['threshold'], df_result['recall'],    's-', label='Recall')
        ax.plot(df_result['threshold'], df_result['f1'],        '^-', label='F1', linewidth=2)
        ax.axvline(x=0.70, color='red', linestyle='--', alpha=0.7, label='current=0.70')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Score')
        ax.set_title('실험 1: 순수 S-BERT — Precision / Recall / F1')
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f'{output_dir}/exp1_pr_curve.png', dpi=150)
        plt.close(fig)

        # 그래프 2: SBERT 점수 분포 (GT=0 vs GT=1)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(scores[labels == 0], bins=50, alpha=0.55, label='GT=0 (비유사)', color='steelblue')
        ax.hist(scores[labels == 1], bins=50, alpha=0.55, label='GT=1 (유사)',   color='tomato')
        ax.axvline(x=0.70, color='red', linestyle='--', alpha=0.8, label='threshold=0.70')
        ax.set_xlabel('S-BERT Cosine 유사도')
        ax.set_ylabel('빈도')
        ax.set_title('실험 1: S-BERT 점수 분포 (GT 기준)')
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f'{output_dir}/exp1_score_distribution.png', dpi=150)
        plt.close(fig)

        print(f"\n결과 저장: {output_dir}/")
        return df_result

    # ─────────────────────────────────────────────────────────────
    # 실험 2: 프로덕션 하이브리드 threshold 검증
    # ─────────────────────────────────────────────────────────────

    def run_experiment2(
        self,
        thresholds: list[float] | None = None,
        gt_name_tfidf_threshold: float = 0.30,
        sbert_weight: float = 0.7,
        output_dir: str = 'graphDB/results/exp2',
    ) -> pd.DataFrame:
        if thresholds is None:
            thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

        print("\n" + "=" * 60)
        print("실험 2: 프로덕션 하이브리드 threshold 검증")
        print("=" * 60)
        os.makedirs(output_dir, exist_ok=True)

        pairs       = self._get_valid_pairs()
        emb         = self._compute_sbert_embeddings()
        tfidf_vecs  = self._fit_tfidf_outline()

        sim_sbert = cosine_similarity(emb)
        sim_tfidf = cosine_similarity(tfidf_vecs)
        s_sbert   = np.array([sim_sbert[i][j] for i, j in pairs])
        s_tfidf   = np.array([sim_tfidf[i][j] for i, j in pairs])
        scores    = sbert_weight * s_sbert + (1 - sbert_weight) * s_tfidf

        labels = self._build_gt_name_tfidf(pairs, gt_name_tfidf_threshold)

        rows = [self._metrics(scores, labels, t) for t in thresholds]
        df_result = pd.DataFrame(rows)
        df_result.to_csv(f'{output_dir}/exp2_metrics.csv', index=False)
        print("\n" + df_result[['threshold', 'precision', 'recall', 'f1', 'n_pred']].to_string(index=False))

        # 그래프 1: P / R / F1 커브
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(df_result['threshold'], df_result['precision'], 'o-', label='Precision')
        ax.plot(df_result['threshold'], df_result['recall'],    's-', label='Recall')
        ax.plot(df_result['threshold'], df_result['f1'],        '^-', label='F1', linewidth=2)
        ax.axvline(x=0.70, color='red', linestyle='--', alpha=0.7, label='current=0.70')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Score')
        ax.set_title(
            f'실험 2: 하이브리드(SBERT {sbert_weight*100:.0f}% + TF-IDF {(1-sbert_weight)*100:.0f}%) — P/R/F1'
        )
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f'{output_dir}/exp2_pr_curve.png', dpi=150)
        plt.close(fig)

        # 그래프 2: threshold별 엣지 수
        fig, ax = plt.subplots(figsize=(8, 4))
        colors = ['tomato' if t == 0.70 else 'steelblue' for t in df_result['threshold']]
        bars = ax.bar([str(t) for t in df_result['threshold']], df_result['n_pred'], color=colors)
        ax.bar_label(bars, fmt='%d', padding=3)
        ax.set_xlabel('Threshold')
        ax.set_ylabel('엣지 수')
        ax.set_title('실험 2: threshold별 생성 엣지 수 (빨간 막대 = 현재 기준)')
        ax.grid(axis='y', alpha=0.3)
        fig.tight_layout()
        fig.savefig(f'{output_dir}/exp2_edge_count.png', dpi=150)
        plt.close(fig)

        print(f"\n결과 저장: {output_dir}/")
        return df_result

    # ─────────────────────────────────────────────────────────────
    # 실험 3: α × threshold grid search
    # ─────────────────────────────────────────────────────────────

    def run_experiment3(
        self,
        alphas: list[float] | None = None,
        thresholds: list[float] | None = None,
        gt_name_tfidf_threshold: float = 0.30,
        output_dir: str = 'graphDB/results/exp3',
    ) -> pd.DataFrame:
        if alphas is None:
            alphas = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        if thresholds is None:
            thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

        print("\n" + "=" * 60)
        print("실험 3: 하이브리드 비율(α) × threshold grid search")
        print("=" * 60)
        os.makedirs(output_dir, exist_ok=True)

        pairs      = self._get_valid_pairs()
        emb        = self._compute_sbert_embeddings()
        tfidf_vecs = self._fit_tfidf_outline()

        # 행렬 연산 1회
        sim_sbert = cosine_similarity(emb)
        sim_tfidf = cosine_similarity(tfidf_vecs)
        s_sbert   = np.array([sim_sbert[i][j] for i, j in pairs])
        s_tfidf   = np.array([sim_tfidf[i][j] for i, j in pairs])

        labels = self._build_gt_name_tfidf(pairs, gt_name_tfidf_threshold)

        rows = []
        for alpha in alphas:
            scores = alpha * s_sbert + (1 - alpha) * s_tfidf
            for t in thresholds:
                m = self._metrics(scores, labels, t)
                m['alpha'] = alpha
                rows.append(m)

        df_result = pd.DataFrame(rows)
        df_result.to_csv(f'{output_dir}/exp3_grid_results.csv', index=False)

        # 히트맵 저장 헬퍼
        def save_heatmap(metric: str, title: str, filename: str, integer_fmt: bool = False) -> None:
            pivot = df_result.pivot(index='alpha', columns='threshold', values=metric)
            pivot = pivot.iloc[::-1]  # alpha 높은 값이 위로

            vmin, vmax = pivot.values.min(), pivot.values.max()
            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=vmin, vmax=vmax)
            plt.colorbar(im, ax=ax)

            ax.set_xticks(range(len(thresholds)))
            ax.set_xticklabels([str(t) for t in pivot.columns])
            ax.set_yticks(range(len(alphas)))
            ax.set_yticklabels([str(a) for a in pivot.index])
            ax.set_xlabel('Threshold')
            ax.set_ylabel('α (SBERT 비율)')
            ax.set_title(title)

            # 셀 수치 표시
            span = vmax - vmin + 1e-8
            for r in range(pivot.shape[0]):
                for c in range(pivot.shape[1]):
                    val = pivot.values[r, c]
                    text = f'{int(val)}' if integer_fmt else f'{val:.3f}'
                    relative = (val - vmin) / span
                    color = 'black' if 0.25 < relative < 0.75 else 'white'
                    ax.text(c, r, text, ha='center', va='center', fontsize=8, color=color)

            # 최대값 강조 (파란 테두리)
            ri, ci = np.unravel_index(pivot.values.argmax(), pivot.shape)
            ax.add_patch(plt.Rectangle(
                (ci - 0.5, ri - 0.5), 1, 1,
                fill=False, edgecolor='blue', linewidth=3,
            ))

            fig.tight_layout()
            fig.savefig(filename, dpi=150)
            plt.close(fig)

        save_heatmap('f1',        '실험 3: F1 히트맵 (α × threshold)',    f'{output_dir}/exp3_f1_heatmap.png')
        save_heatmap('precision', '실험 3: Precision 히트맵',              f'{output_dir}/exp3_precision_heatmap.png')
        save_heatmap('recall',    '실험 3: Recall 히트맵',                 f'{output_dir}/exp3_recall_heatmap.png')
        save_heatmap('n_pred',    '실험 3: 엣지 수 히트맵',               f'{output_dir}/exp3_edge_count_heatmap.png', integer_fmt=True)

        best = df_result.loc[df_result['f1'].idxmax()]
        print(f"\n최적 조합: α={best['alpha']}, threshold={best['threshold']}, F1={best['f1']:.4f}")
        print(f"결과 저장: {output_dir}/")
        return df_result


# ─────────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='교과목 유사도 threshold 최적화 실험')
    parser.add_argument(
        '--exp', nargs='+', choices=['1', '2', '3', 'all'], default=['all'],
        help='실행할 실험 번호 (예: --exp 1 3, --exp all)',
    )
    parser.add_argument('--csv',        type=str,   default='final_course.csv')
    parser.add_argument('--output-dir', type=str,   default='results')
    parser.add_argument('--gt-threshold', type=float, default=0.30,
                        help='GT 레이블 생성용 TF-IDF threshold (기본값: 0.30)')
    args = parser.parse_args()

    to_run = {'1', '2', '3'} if 'all' in args.exp else set(args.exp)

    exp = ThresholdExperiment(csv_path=args.csv)
    exp.load_data()

    if '1' in to_run:
        exp.run_experiment1(
            gt_tfidf_threshold=args.gt_threshold,
            output_dir=f'{args.output_dir}/exp1',
        )
    if '2' in to_run:
        exp.run_experiment2(
            gt_name_tfidf_threshold=args.gt_threshold,
            output_dir=f'{args.output_dir}/exp2',
        )
    if '3' in to_run:
        exp.run_experiment3(
            gt_name_tfidf_threshold=args.gt_threshold,
            output_dir=f'{args.output_dir}/exp3',
        )

    print("\n모든 실험 완료.")


if __name__ == '__main__':
    main()
