# 🦁 Lions Student Dashboard

**한양대학교 LIONS 학생 관리 대시보드**  
학생 이수 내역 파악, 학과 요건 평가, 교과목 추천 및 AI 기반 종합 피드백을 제공하는 학생 통합 관리 및 분석 시스템입니다.

## 📖 프로젝트 개요

Lions Student Dashboard는 한양대학교 ERICA 자율전공학부 학생들의 교과목 이수 내역, 학과별 진입 요건, 그리고 전공 선호도 설문조사 데이터를 통합적으로 분석하는 **지능형 학생 관리 플랫폼**입니다. 

단순한 데이터 조회를 넘어, **그래프 데이터베이스(Neo4j)를 활용한 맞춤형 교과목 추천**, **AI 기반 종합 피드백(OpenAI)**, 그리고 **다중 메트릭(3-Metric) 평가 알고리즘**을 통해 학생의 주도적인 진로 탐색 및 학업 설계를 깊이 있게 지원합니다.

## ✨ 핵심 기능

### 1. 🎓 통합 학생 데이터 관리 (Comprehensive Student Management)
- **학생 프로필 및 이수 내역 조회**: 학생별 기본 정보, 수강 완료한 교과목 목록 및 성적, 전체 학점 이수 현황을 한눈에 파악할 수 있는 통합 뷰.
- **다중전공 설문 추적**: 학생이 응답한 선호 전공 설문 데이터를 바탕으로, 실제 학과 진학과 요건 충족률의 상관관계를 분석 및 트래킹합니다.

### 2. 🤖 AI 기반 학생 맞춤형 코멘트 (AI-Powered Feedback)
- **GPT 기반 종합 분석**: 학생의 기존 수강 내역, 누적 학점, 설문 응답을 종합적으로 분석하여 앞으로의 학업 방향성을 제시하는 맞춤형 'AI 튜터 총평'을 자동 생성합니다.
- **신속한 비동기 일괄 처리**: 대규모 학생 데이터 평가와 AI 총평 생성을 Celery Worker를 통해 백그라운드에서 신속하고 안정적으로 처리합니다.

### 3. 🕸️ 그래프 기반 교과목 추천 (Course Recommendation System)
- **교과목 유사도 임베딩 분석**: 다국어 임베딩 모델을 활용하여 교내 수많은 교과목들의 이름 및 설명의 의미론적 유사도(Semantic Similarity) 점수를 도출합니다.
- **Neo4j 맞춤형 연관 교과목 추천**: 학생이 기이수했거나 관심 있어 하는 교과목을 바탕으로 가장 연관성 높은 다음 학기 추천/선수 교과목을 그래프 탐색을 통해 지능적으로 선별 제공합니다.

### 4. 📊 다중 메트릭 진입 요건 평가 (Multi-metric Evaluation System)
- **3-Metric 알고리즘 평가**: 학생이 특정 학과 진입을 시도할 때 요건 충족률을 세 가지 핵심 지표(필수 과목 이수율, 권장 과목 이수율, 평점 평균)에서 정밀하게 계산합니다.
- **전 학과 적합도 시각화**: 학생의 현재 이수 상태 데이터를 기준으로 전체 학과에 대한 진입 적합도(%)를 직관적인 차트와 점수로 시각화합니다.

### 5. 🛠️ 관리자 대시보드 및 확장 가능한 데이터 파이프라인
- **대규모 데이터 일괄 업로드**: 엑셀/CSV 형태의 방대한 학생, 강좌 리스트, 각 학과별 요건, 수강 이력 데이터를 카테고리화(5-Group)하여 시스템에 한 번에 손쉽게 적재합니다.
- **시스템 통계 및 모니터링**: 대시보드를 통해 데이터 적재 상황, 학과별 학생 분포 및 접속 상태를 실시간으로 모니터링합니다.

## 🛠️ 기술 스택 및 아키텍처

아키텍처의 중심은 빠르고 가벼운 FastAPI 백엔드에 있으며, Celery 및 Redis를 통한 비동기 이벤트 처리와 Neo4j를 결합한 분산 데이터 처리 구조를 띄고 있습니다.

### Backend & AI Worker
- **Framework & API**: FastAPI (Python 3.12)
- **Database**: PostgreSQL (with pgvector), SQLAlchemy 2.0
- **Graph Database**: Neo4j (교과목 지식 그래프 활용)
- **AI & Data Processing**: OpenAI API (gpt-4o-mini), `paraphrase-multilingual-MiniLM-L12-v2` (GraphDB 파이프라인)
- **Task Queue**: Celery, Redis (비동기 처리)

### Frontend
- **Framework**: React 19, TypeScript, Vite
- **UI & Styling**: Tailwind CSS, Recharts, Lucide-React
- **State & Structure**: Component-based Architecture

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Environment Management**: uv (고속 파이썬 패키지 관리자)

---

> 💡 **주석 (Note)**: 본 프로젝트의 설치 및 로컬 개발 환경 구성 방법(설치 가이드)은 [INSTALL.md](./INSTALL.md)에서 확인하실 수 있습니다. 개발을 진행하시려는 분들은 해당 문서를 참고하여 주시기 바랍니다.

## 📄 라이선스

This project is licensed under the MIT License.
