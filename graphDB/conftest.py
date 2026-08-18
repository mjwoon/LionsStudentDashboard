"""pytest 부트스트랩: 실험 코드가 두 환경(graphDB 3.11 / 루트 3.12)에서 균일하게
임포트되도록 sys.path 를 구성한다.
  - graphDB/      → `experiment.*`, `similarity_engine`, `text_features`
  - ../backend/   → `services.*` (RQ2 주입 평가용, 루트 3.12 환경에서만 실제 사용)
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(os.path.dirname(_here), "backend")
# backend 를 graphDB 보다 앞에 둔다: `config` 등 동명 모듈이 backend 로 해석되도록
# (graphDB/config.py 는 sklearn 을 import → 루트 3.12 환경에서 shadow 시 실패).
# 삽입 순서상 나중에 insert(0,...) 한 것이 앞선다 → graphDB 먼저, backend 나중.
for p in (_here, _backend):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)
