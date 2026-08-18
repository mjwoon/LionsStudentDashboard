# 교과목 유사도 임계값 실험 (RQ1·RQ2) 설계

**작성일**: 2026-08-13
**대상 논문**: KSC2026 — Lions Student Dashboard 전공 적합도 평가 시스템
**근거 문서**: `~/Downloads/KSC2026_실험계획서_초안_v3.md`

## 1. 목적

대체 인정 판정에 쓰이는 유사도 임계값을 실험적으로 검증한다.

- **RQ1**: 한국어 교과목 유사도에서 대체 인정 판정의 최적 임계값 `t*`는?
- **RQ2**: 임계값 변화가 학생별 적합도 점수·학과 순위를 얼마나 바꾸는가?

(RQ3 UI/UX USE 설문은 본 실험 범위 밖 — 별도 트랙.)

## 2. 현행 시스템 사실 (코드 확인 결과)

- 유사도는 **프로덕션 하이브리드** `0.7·SBERT + 0.3·TF-IDF`로 계산된다
  (`graphDB/similarity_engine.py` `SimilarityEngine`, `hybrid_weight=0.7`).
  SBERT 모델은 `paraphrase-multilingual-MiniLM-L12-v2`.
- 엣지 생성(`compute_similarity`)과 인정 판정(`constants.SIMILARITY_THRESHOLD = 0.7`,
  `evaluation_service._find_best_similar_course`)이 임계값을 각각 참조한다.
  엣지는 유사도 점수를 그대로 실어 나른다 → 그래프를 낮은 임계값으로 한 번 만들면
  인정 임계값만 스윕 가능.
- 유효 쌍 규칙: 같은 학수번호 쌍·연계과목(1,2 시리즈) 쌍 제외
  (`SimilarityEngine.compute_similarity`, `threshold_experiment._get_valid_pairs`와 동일).
- 평가는 `EvaluationService.batch_evaluate_students`가 SQLAlchemy DB 기반으로 수행하며,
  유사도는 `_get_similarity_from_graph`(Neo4j) + `_similarity_threshold`를 통해 주입식으로
  `scoring.find_best_similar_course`에 전달된다 → **주입 오버라이드로 Neo4j 없이 재현 가능**.
- 데이터셋: `graphDB/course_all_aggregated.csv` (1,493 과목; 프로덕션 그래프 정본),
  `sample_students_300.csv`(고유 학생 300명; 파일은 학생당 2행이라 600행이나 학번 기준 300명), `sample_enrollments_300.csv`, `group5_requirements_recs.csv`.
- LLM 연동은 OpenAI (`ai/ai_services/ai_service.py`, `.env`의 `OPENAI_API_KEY`).

## 3. 공통 전제

- **유사도 정의**: 프로덕션 하이브리드 `0.7·SBERT + 0.3·TF-IDF`. RQ1 임계값은 이 하이브리드
  점수에 적용한다(순수 SBERT 아님) — 실제 `SIMILAR_TO` 엣지를 만드는 점수와 일치시킨다.
- **유효 쌍**: 같은 학수번호·연계과목 제외 (실측 1,113,585쌍).
- **재현성**: 모든 무작위 과정(표본추출·부트스트랩·LLM 순서 섞기)에 시드 고정.
- **산출 위치**: `graphDB/results/rq1/`, `graphDB/results/rq2/`.

## 4. RQ1 — 최적 임계값

산출 스크립트: `graphDB/experiment_rq1.py`

### 4.1 유사도 계산
전 유효쌍의 하이브리드 유사도를 계산한다. 기존 `SimilarityEngine`/임베딩 캐시를 재사용해
SBERT 임베딩·TF-IDF 벡터를 각 1회만 계산한다.

### 4.2 층화표본 (상위 3구간 전수 + 하위 표본, ≈335쌍)
유사도 구간별 층화(시드 고정). 층별 모집단 크기 `N_k`를 기록한다. 실측 결과 고유사도
구간이 극히 희박(≥0.7이 총 115쌍)하므로, 하위 3구간은 표본추출하고 **상위 3구간(≥0.7)은
전수 레이블링**한다(추정 오차 제거 + 레이블링 비용 절감).

| 구간 | 0.0–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | 0.9–1.0 |
|---|---|---|---|---|---|---|
| 모집단 `N_k` | 1,100,048 | 6,984 | 634 | 64 | 34 | 17 |
| 표본 | 100 | 60 | 60 | 64 (전수) | 34 (전수) | 17 (전수) |

구현: `per_bin = [100, 60, 60, ∞, ∞, ∞]`(상위 3구간은 큰 값 → `min(per_bin, N_k)`로 전수).

### 4.3 블라인드 채점표 산출
`graphDB/results/rq1/labeling_sheet.csv` 생성:
`pair_id, 과목A_이름, 과목A_개요, 과목B_이름, 과목B_개요, label(공란)`.
유사도·구간·정답은 노출하지 않고 제시 순서를 무작위화한다.
→ 사람 2인이 이 표를 채우면 LLM 골드를 그대로 교체할 수 있는 산출물.

### 4.4 LLM 골드 레이블
- 모델: **OpenAI `gpt-4o`** (`.env` 키 사용, 약 800 호출).
- 판정 문항: "과목 A를 이수했을 때 과목 B를 대체 인정할 수 있는가?" (이진).
  과목명 + 개요만 제시, 유사도 비노출, 순서 무작위화.
- **2회 독립 실행** → LLM 간 **Cohen's κ** 산출 (설계서의 레이블러 2인 구조 모사).
  불일치 건은 규칙 기반 adjudication(2회 중 다수결 불가 → 보수적으로 "인정 안 함")으로
  gold label 확정하되, 정책을 코드/문서에 명시.
- 프롬프트·원 응답·파싱 결과를 `rq1/llm_labels_pass1.csv`, `pass2.csv`에 저장.

### 4.5 TF-IDF silver 레이블
같은 표본(≈335쌍)에 대해 이름 char n-gram TF-IDF ≥ 0.30으로 이진 레이블
(`threshold_experiment._build_gt_name_tfidf`와 동일 규칙). `rq1/tfidf_labels.csv`에 저장.

### 4.6 GT 간 비교 (핵심)
LLM 골드 ↔ TF-IDF silver 간 **Cohen's κ**와 혼동표를 산출 →
값싼 자동 GT가 LLM GT와 얼마나 일치하는지 정량화. `rq1/gt_agreement.json`.

### 4.7 임계값 스윕 (모집단 가중 보정)
t = 0.30 ~ 1.00, 0.01 단위. 0.01 해상도를 위해 구간 단위가 아니라 **표본 쌍 단위**로 가중한다.
각 표본 쌍 i에 역표집확률 가중치 `w_i = N_k(i) / n_k(i)`를 부여(Horvitz–Thompson):

```
w_i = N_k(i) / n_k(i)                          (층 k(i)의 표본 쌍 가중치)

TP(t) = Σ_i w_i · [sim_i ≥ t] · [y_i = 1]
FP(t) = Σ_i w_i · [sim_i ≥ t] · [y_i = 0]
FN(t) = Σ_i w_i · [sim_i <  t] · [y_i = 1]
```

t가 구간 경계일 때 `Σ_{구간 ≥ t} N_k · p_k`(p_k = 층 양성 비율)와 정확히 일치하는 일반화 형태.

**두 GT(LLM 골드·TF-IDF) 각각**에 대해 P/R/F1을 산출. 부트스트랩 1,000회(층 내 재표집)로
95% 신뢰구간. 산출물:

- `rq1/sweep_metrics_llm.csv`, `rq1/sweep_metrics_tfidf.csv` (t별 P/R/F1 + CI)
- `rq1/pr_curve.png`, `rq1/f1_threshold.png` (두 GT 겹쳐 표시, CI 밴드)
- PR-AUC, **`t*` (GT별)** → `rq1/summary.md`

## 5. RQ2 — 하위 시스템 영향

산출 스크립트: `graphDB/experiment_rq2.py`

### 5.1 DB 시딩
CSV(course/student/enrollment/requirement/recommendation)를 로컬 **SQLite**에 적재.
`backend/services/upload_service.py`의 업로드 함수를 재사용해 실제 모델·검증 경로를 탄다.
멱등 시딩 후 세션 재사용.

### 5.2 유사도 사전계산
code→code 하이브리드 유사도 dict를 **1회** 계산(유사도 ≥ 0.6만 보관, 스윕 범위 커버).
`rq2/similarity_lookup.parquet`(또는 pickle) 캐시.

### 5.3 평가 서비스 주입
`EvaluationService`를 서브클래싱/오버라이드하여
`_get_similarity_from_graph`(사전계산 dict 조회)와 `_similarity_threshold`(가변)를 주입.
Neo4j·그래프 가용성 검사를 우회 → 완전 재현 가능한 오프라인 재계산.

### 5.4 재계산
임계값 **{0.6, 0.7, 0.8, t\*}** 각각에 대해 300 학생 × 40 학과 = 12,000건 재계산.
결과를 long-format 테이블로 저장: `rq2/evaluations_{t}.csv`
(student_id, department_id, overall_score, grade, entry/recommended/curriculum 하위 점수).

### 5.5 지표
0.8(현행 실효값) 기준선 대비:

- **학과 순위 변동**: 학생별 40개 학과 순위의 **Spearman ρ** 분포, **Top-1 변경 학생 비율**
- **적합도 점수 분포 변화**: overall_score 히스토그램/요약통계 이동
- **등급 이동**: A~F 전이 행렬
- **추가 인정 관계 수**: 사각지대(0.7–0.8) 복구 시 늘어나는 인정 관계 수

산출물: `rq2/ranking_stability.csv`, `rq2/score_shift.png`, `rq2/grade_migration.csv`,
`rq2/summary.md`.

## 6. 산출물 요약

```
graphDB/results/rq1/
  labeling_sheet.csv          # 사람 교체용 블라인드 채점표
  llm_labels_pass1.csv, pass2.csv
  tfidf_labels.csv
  gt_agreement.json           # LLM↔TFIDF κ
  sweep_metrics_llm.csv, sweep_metrics_tfidf.csv
  pr_curve.png, f1_threshold.png
  summary.md                  # t*(GT별), PR-AUC, κ
graphDB/results/rq2/
  similarity_lookup.*          # 캐시
  evaluations_{0.6,0.7,0.8,tstar}.csv
  ranking_stability.csv, score_shift.png, grade_migration.csv
  summary.md
```

## 7. 방법론 한계 (논문 명시)

- LLM 골드 레이블은 사람 학사 판단의 대리물 — "LLM 보조 레이블"로 명시.
  블라인드 채점표를 제공해 사람 2인 레이블로 교체 가능함을 서술.
- 하이브리드 유사도를 TF-IDF로 채점하는 GT는 순환성이 있어 보조 비교 지표로만 사용.
- 하위 구간 양성 0건 시 Recall 추정은 가능하나 CI가 넓어질 수 있음 → 해당 층 증량으로 대응.

## 8. 결정 사항 (확정)

- 유사도: 프로덕션 하이브리드 `0.7·SBERT + 0.3·TF-IDF`.
- LLM 레이블러: OpenAI `gpt-4o`, 2회 독립 실행, 불일치 보수적 확정.
- GT 비교축: LLM 골드(주) ↔ TF-IDF silver(비교), κ로 정량화.
- RQ2: Neo4j 우회(주입), SQLite 시딩, 임계값 {0.6,0.7,0.8,t*}.
