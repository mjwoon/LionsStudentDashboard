"""
트랜잭션 경계(Unit of Work).

여러 쓰기(예: 그룹 업로드의 대학+학과)를 하나의 트랜잭션으로 묶어 원자적으로
커밋/롤백한다. run_upsert(commit=False)와 함께 쓰면 엔티티별 개별 커밋 대신
엔드포인트 단위 원자성을 얻는다.
"""

from contextlib import contextmanager

from sqlalchemy.orm import Session


# 세션 단위 플래그 키: 이 UoW 안에서는 run_upsert가 개별 commit을 건너뛴다.
IN_UOW_FLAG = "in_unit_of_work"


@contextmanager
def unit_of_work(db: Session):
    """정상 종료 시 commit, 예외 발생 시 rollback 후 재전파.

    세션에 플래그를 세워, 내부에서 호출되는 run_upsert가 개별 commit을 건너뛰고
    이 UoW의 단일 commit에 참여하도록 한다(원자적 그룹 업로드). 라우터는 엔드포인트
    본문을 `with unit_of_work(db):`로 감싸기만 하면 된다.
    """
    db.info[IN_UOW_FLAG] = True
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.info.pop(IN_UOW_FLAG, None)
