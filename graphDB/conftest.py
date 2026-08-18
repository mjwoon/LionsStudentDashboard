"""pytest 부트스트랩: 실험 코드가 두 환경(graphDB 3.11 / 루트 3.12)에서 균일하게
임포트되도록 sys.path 를 구성한다.
  - graphDB/      → `experiment.*`, `similarity_engine`, `text_features`
  - ../backend/   → `services.*` (RQ2 주입 평가용, 루트 3.12 환경에서만 실제 사용)
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(os.path.dirname(_here), "backend")
for p in (_backend, _here):
    if p not in sys.path:
        sys.path.insert(0, p)
