"""하위호환 shim — 설정은 lions_core.config로 이동했다.

기존 `from config import settings` 호출부를 유지하기 위한 재노출.
"""
from lions_core.config import Settings, settings  # noqa: F401
