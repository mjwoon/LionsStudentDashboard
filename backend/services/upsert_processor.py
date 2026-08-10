"""
업서트 처리 엔진.

대량 업로드의 공통 골격(행 순회 → 조회 → 수정/생성 → 오류 수집 → 커밋)을 한 곳에 둔다.
이전에는 이 골격이 UploadService._generic_upload와 upload_courses(손으로 재작성)에
중복돼 있었다.

batch_key를 주면 '배치 내 동일 키'를 이미 처리한 엔티티로 취급한다. 이는 과목 업로드처럼
한 번의 업로드에 같은 학수번호가 여러 번 등장할 때, 커밋 전이라 DB 조회로는 잡히지 않는
중복을 올바르게 수정(update)으로 처리하기 위한 것이다.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from models.schemas import DataUploadResponse, ErrorDetail

logger = logging.getLogger(__name__)


def run_upsert(
    db: Session,
    data_list: List[Any],
    *,
    find_existing: Callable[[Session, Any], Any],
    create_new: Callable[[Session, Any], Any],
    update_existing: Callable[[Session, Any, Any], None],
    item_id_accessor: Callable[[Any], str],
    success_message: str,
    batch_key: Optional[Callable[[Any], Any]] = None,
    commit: bool = True,
) -> DataUploadResponse:
    """행 목록을 순회하며 조회→수정/생성한다.

    commit=True(기본): 여기서 db.commit()까지 수행(단독 업로드).
    commit=False: 커밋하지 않고 세션에만 반영(상위 unit_of_work가 일괄 커밋; 원자적 그룹 업로드).
    """
    uploaded_count = 0
    updated_count = 0
    detailed_errors: List[ErrorDetail] = []
    batch_cache: Dict[Any, Any] = {}

    row_index = 2
    for data in data_list:
        try:
            key = batch_key(data) if batch_key is not None else None

            if key is not None and key in batch_cache:
                # 배치 내에서 이미 처리한 엔티티 → 수정으로 취급
                update_existing(db, batch_cache[key], data)
                updated_count += 1
            else:
                existing = find_existing(db, data)
                if existing:
                    update_existing(db, existing, data)
                    updated_count += 1
                else:
                    existing = create_new(db, data)
                    if existing:
                        db.add(existing)
                        uploaded_count += 1
                if key is not None and existing is not None:
                    batch_cache[key] = existing
        except Exception as e:
            item_id = ""
            try:
                item_id = str(item_id_accessor(data))
            except Exception:
                pass
            detailed_errors.append(
                ErrorDetail(row=row_index, item_id=item_id, reason=str(e))
            )
        row_index += 1

    # 명시적 commit=False 이거나, 상위 unit_of_work 안이면 개별 커밋을 건너뛴다.
    should_commit = commit and not db.info.get("in_unit_of_work", False)
    if not should_commit:
        # 커밋은 상위 unit_of_work가 담당. 여기서는 세션 반영 결과(카운트)만 돌려준다.
        return DataUploadResponse(
            success=True,
            message=success_message,
            uploaded_count=uploaded_count,
            updated_count=updated_count,
            detailed_errors=detailed_errors if detailed_errors else None,
        )

    try:
        db.commit()
        return DataUploadResponse(
            success=True,
            message=success_message,
            uploaded_count=uploaded_count,
            updated_count=updated_count,
            detailed_errors=detailed_errors if detailed_errors else None,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"{success_message.split(' ')[0]} 업로드 커밋 오류: {str(e)}")
        return DataUploadResponse(
            success=False,
            message=f"{success_message.split(' ')[0]} 실패: {str(e)}",
            uploaded_count=0,
            updated_count=0,
            errors=[str(e)],
            detailed_errors=detailed_errors if detailed_errors else None,
        )
