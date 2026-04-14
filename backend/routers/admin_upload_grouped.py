"""
통합 데이터 업로드 API 엔드포인트 (5개 그룹)

1. 단과대학 + 학과 → colleges, departments
2. 학생 + 희망전공조사 → students, major_surveys
3. 과목 → courses
4. 교육과정 → curriculums
5. 진입요건 + 권장과목 → department_entry_requirements, requirement_courses, course_recommendations
6. 수강 데이터 → student_courses
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import (
    CollegeDataUpload, DepartmentDataUpload,
    StudentDataUpload, MajorSurveyDataUpload,
    RequirementDataUpload, RequirementCourseDataUpload, RecommendationDataUpload,
    CourseDataUpload, CurriculumDataUpload,
    EnrollmentDataUpload,
    DataUploadResponse,
)
from services.admin_service import AdminService
from routers.admin import parse_upload_file
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/upload-grouped",
    tags=["admin-grouped-upload"]
)


class GroupedUploadResponse(DataUploadResponse):
    """통합 업로드 응답 (하위 결과 포함)"""
    sub_results: Optional[List[dict]] = None


def _make_sub_result(label: str, resp: DataUploadResponse) -> dict:
    return {
        "label": label,
        "success": resp.success,
        "message": resp.message,
        "uploaded_count": resp.uploaded_count,
        "updated_count": resp.updated_count,
        "errors": resp.errors,
        "detailed_errors": [e.dict() for e in resp.detailed_errors] if resp.detailed_errors else None,
    }


# ─────────────────────────────────────────────
# 그룹 1: 단과대학 + 학과
# ─────────────────────────────────────────────
@router.post("/org", response_model=GroupedUploadResponse)
async def upload_org(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    단과대학 + 학과 통합 업로드

    CSV 컬럼:
    college_id, college_name, dept_id, dept_code, dept_name, min_credits
    (또는 한국어 alias 사용 가능)

    후처리:
    1. 고유 college_id/name 추출 → colleges upsert
    2. 학과 행 → departments upsert (college FK 연결)
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        sub_results = []
        total_uploaded = 0
        total_updated = 0

        # Step 1: colleges 추출 및 업로드
        college_map = {}  # (college_id or college_name) -> CollegeDataUpload
        for row in data:
            c_id = row.get("college_id")
            c_name = row.get("college_name") or row.get("단과대학") or row.get("단과대학명")
            if c_name:
                key = c_id if c_id else c_name
                if key not in college_map:
                    college_map[key] = CollegeDataUpload(id=c_id, name=c_name)

        if college_map:
            colleges_resp = AdminService.upload_colleges(db, list(college_map.values()))
            sub_results.append(_make_sub_result("대학", colleges_resp))
            total_uploaded += colleges_resp.uploaded_count
            total_updated += colleges_resp.updated_count
        else:
            sub_results.append({"label": "대학", "success": True, "message": "대학 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        # Step 2: departments 업로드
        dept_list = []
        for row in data:
            d_code = row.get("dept_code") or row.get("학과코드")
            d_name = row.get("dept_name") or row.get("학과명") or row.get("학과")
            if d_code and d_name:
                dept_list.append(DepartmentDataUpload(
                    id=row.get("dept_id"),
                    code=d_code,
                    name=d_name,
                    college_id=row.get("college_id"),
                    college_name=row.get("college_name") or row.get("단과대학") or row.get("단과대학명"),
                    min_credits=row.get("min_credits", 130) or 130,
                ))

        if dept_list:
            depts_resp = AdminService.upload_departments(db, dept_list)
            sub_results.append(_make_sub_result("학과", depts_resp))
            total_uploaded += depts_resp.uploaded_count
            total_updated += depts_resp.updated_count
        else:
            sub_results.append({"label": "학과", "success": True, "message": "학과 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        all_success = all(r.get("success", True) for r in sub_results)
        return GroupedUploadResponse(
            success=all_success,
            message=f"단과대학+학과 업로드 완료 (추가: {total_uploaded}, 업데이트: {total_updated})",
            uploaded_count=total_uploaded,
            updated_count=total_updated,
            sub_results=sub_results,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped org upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


# ─────────────────────────────────────────────
# 그룹 2: 학생 + 희망전공조사
# ─────────────────────────────────────────────
@router.post("/students", response_model=GroupedUploadResponse)
async def upload_students_grouped(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    학생 + 희망전공조사 통합 업로드

    CSV 컬럼:
    student_id, name, email, phone, department_id, pride, class_number, track,
    survey_round_id, first_choice_id, second_choice_id, decision_status_id, decision_scale
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        sub_results = []
        total_uploaded = 0
        total_updated = 0

        # Step 1: students 업로드 (student_id 기준 중복 제거)
        seen_student_ids = set()
        students_list = []
        for row in data:
            sid = row.get("student_id") or row.get("학번")
            name = row.get("name") or row.get("이름") or row.get("성명")
            email = row.get("email") or row.get("이메일")
            if sid and name and email and sid not in seen_student_ids:
                seen_student_ids.add(sid)
                students_list.append(StudentDataUpload(**row))

        if students_list:
            students_resp = AdminService.upload_students(db, students_list)
            sub_results.append(_make_sub_result("학생", students_resp))
            total_uploaded += students_resp.uploaded_count
            total_updated += students_resp.updated_count
        else:
            sub_results.append({"label": "학생", "success": True, "message": "학생 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        # Step 2: major_surveys 추출 (survey_round_id가 있는 행만)
        surveys_list = []
        for row in data:
            sr_id = row.get("survey_round_id") or row.get("회차") or row.get("회차ID")
            fc_id = row.get("first_choice_id") or row.get("1지망") or row.get("1지망학과ID")
            if sr_id and fc_id:
                surveys_list.append(MajorSurveyDataUpload(**row))

        if surveys_list:
            surveys_resp = AdminService.upload_major_surveys(db, surveys_list)
            sub_results.append(_make_sub_result("희망전공조사", surveys_resp))
            total_uploaded += surveys_resp.uploaded_count
            total_updated += surveys_resp.updated_count
        else:
            sub_results.append({"label": "희망전공조사", "success": True, "message": "설문 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        all_success = all(r.get("success", True) for r in sub_results)
        return GroupedUploadResponse(
            success=all_success,
            message=f"학생+희망전공 업로드 완료 (추가: {total_uploaded}, 업데이트: {total_updated})",
            uploaded_count=total_uploaded,
            updated_count=total_updated,
            sub_results=sub_results,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped students upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

# ─────────────────────────────────────────────
# 그룹 3: 과목 
# ─────────────────────────────────────────────
@router.post("/courses", response_model=GroupedUploadResponse)
async def upload_courses_grouped(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    과목 업로드

    CSV 컬럼:
    학수번호, 교과목이름, 학점, 이수구분, 학년, 설강학과, 교과목개요
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        sub_results = []
        total_uploaded = 0
        total_updated = 0

        # Step 1: courses 업로드
        courses_list = []
        for row in data:
            code = row.get("course_code") or row.get("학수번호") or row.get("과목코드")
            name = row.get("course_name") or row.get("과목명") or row.get("교과목이름") or row.get("교과목 이름") or row.get("교과목명")
            if code and name:
                courses_list.append(CourseDataUpload(**row))

        if courses_list:
            courses_resp = AdminService.upload_courses(db, courses_list)
            sub_results.append(_make_sub_result("과목", courses_resp))
            total_uploaded += courses_resp.uploaded_count
            total_updated += courses_resp.updated_count
        else:
            sub_results.append({"label": "과목", "success": True, "message": "과목 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        all_success = all(r.get("success", True) for r in sub_results)
        return GroupedUploadResponse(
            success=all_success,
            message=f"과목 업로드 완료 (추가: {total_uploaded}, 업데이트: {total_updated})",
            uploaded_count=total_uploaded,
            updated_count=total_updated,
            sub_results=sub_results,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped courses upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


# ─────────────────────────────────────────────
# 그룹 4: 교육과정
# ─────────────────────────────────────────────
@router.post("/curriculum", response_model=GroupedUploadResponse)
async def upload_curriculum_grouped(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    교육과정 업로드

    CSV 컬럼:
    학수번호, 교과목이름, 학점, 이수구분, 학년, 학기, 설강학과, 교육과정학과코드
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        sub_results = []
        total_uploaded = 0
        total_updated = 0

        # Step 1: curriculums 업로드
        curr_list = []
        for row in data:
            curr_list.append(CurriculumDataUpload(**row))

        if curr_list:
            curr_resp = AdminService.upload_curriculums(db, curr_list)
            sub_results.append(_make_sub_result("교육과정", curr_resp))
            total_uploaded += curr_resp.uploaded_count
            total_updated += curr_resp.updated_count
        else:
            sub_results.append({"label": "교육과정", "success": True, "message": "교육과정 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        all_success = all(r.get("success", True) for r in sub_results)
        return GroupedUploadResponse(
            success=all_success,
            message=f"교육과정 업로드 완료 (추가: {total_uploaded}, 업데이트: {total_updated})",
            uploaded_count=total_uploaded,
            updated_count=total_updated,
            sub_results=sub_results,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped curriculum upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

# ─────────────────────────────────────────────
# 그룹 5: 진입요건 + 권장과목
# ─────────────────────────────────────────────
@router.post("/requirements", response_model=GroupedUploadResponse)
async def upload_requirements_grouped(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    진입요건 + 요건과목매핑 + 권장과목 통합 업로드

    CSV 컬럼:
    dept_code, admission_year, requirement_group, target_grade_level, required_count,
    requirement_text, is_alert_required, logic_operator, course_code, recommended_course
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        sub_results = []
        total_uploaded = 0
        total_updated = 0

        # Step 1: requirements 업로드 (중복 제거: dept_code + admission_year + requirement_group)
        reqs_list = []
        seen_req_keys = set()
        for row in data:
            dept_code = row.get("department_code") or row.get("dept_code") or row.get("학과코드") or row.get("소속학과") or row.get("학과")
            adm_year = row.get("admission_year") or row.get("적용학번")
            req_group = row.get("requirement_group") or row.get("요건그룹") or row.get("그룹")
            if dept_code and adm_year and req_group:
                key = (str(dept_code), str(adm_year), str(req_group))
                if key not in seen_req_keys:
                    seen_req_keys.add(key)
                    reqs_list.append(RequirementDataUpload(**row))

        if reqs_list:
            reqs_resp = AdminService.upload_requirements(db, reqs_list)
            sub_results.append(_make_sub_result("진입요건", reqs_resp))
            total_uploaded += reqs_resp.uploaded_count
            total_updated += reqs_resp.updated_count
        else:
            sub_results.append({"label": "진입요건", "success": True, "message": "요건 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        # Step 2: requirement_courses 추출 (course_code가 있는 행)
        # requirement_id가 없으면 (dept_code, admission_year, requirement_group)으로 자동 조회
        req_courses_list = []
        for row in data:
            req_id = row.get("requirement_id") or row.get("요건 ID") or row.get("요건ID")
            course_code = row.get("course_code") or row.get("학수번호") or row.get("과목코드")
            if not course_code:
                continue

            # requirement_id가 없으면 dept_code + admission_year + requirement_group으로 조회
            if not req_id:
                dept_code = row.get("department_code") or row.get("dept_code") or row.get("학과코드") or row.get("소속학과") or row.get("학과")
                adm_year = row.get("admission_year") or row.get("적용학번")
                req_group = row.get("requirement_group") or row.get("요건그룹") or row.get("그룹")
                if dept_code and adm_year and req_group:
                    from models.models import DepartmentEntryRequirement, Department as DeptModel
                    dept = db.query(DeptModel).filter(DeptModel.code == str(dept_code)).first()
                    if dept:
                        try:
                            adm_year_int = int(float(adm_year))
                            req_group_int = int(float(req_group))
                        except (ValueError, TypeError):
                            continue
                        req_obj = db.query(DepartmentEntryRequirement).filter(
                            DepartmentEntryRequirement.department_id == dept.id,
                            DepartmentEntryRequirement.admission_year == adm_year_int,
                            DepartmentEntryRequirement.requirement_group == req_group_int
                        ).first()
                        if req_obj:
                            req_id = req_obj.id

            if req_id and course_code:
                req_courses_list.append(RequirementCourseDataUpload(
                    requirement_id=int(req_id),
                    course_code=str(course_code)
                ))

        if req_courses_list:
            rc_resp = AdminService.upload_requirement_courses(db, req_courses_list)
            sub_results.append(_make_sub_result("요건 과목 매핑", rc_resp))
            total_uploaded += rc_resp.uploaded_count
            total_updated += rc_resp.updated_count
        else:
            sub_results.append({"label": "요건 과목 매핑", "success": True, "message": "매핑 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        # Step 3: recommendations 추출
        recs_list = []
        for row in data:
            rec_name = row.get("recommended_course") or row.get("권장과목명") or row.get("권장과목")
            dept_code = row.get("department_code") or row.get("dept_code") or row.get("학과코드") or row.get("소속학과") or row.get("학과")
            if rec_name and dept_code:
                recs_list.append(RecommendationDataUpload(
                    department_code=dept_code,
                    department_id=row.get("department_id") or row.get("소속학과ID") or row.get("학과ID"),
                    course_name=rec_name,
                ))

        if recs_list:
            recs_resp = AdminService.upload_recommendations(db, recs_list)
            sub_results.append(_make_sub_result("권장과목", recs_resp))
            total_uploaded += recs_resp.uploaded_count
            total_updated += recs_resp.updated_count
        else:
            sub_results.append({"label": "권장과목", "success": True, "message": "권장과목 데이터 없음", "uploaded_count": 0, "updated_count": 0})

        all_success = all(r.get("success", True) for r in sub_results)
        return GroupedUploadResponse(
            success=all_success,
            message=f"진입요건+권장과목 업로드 완료 (추가: {total_uploaded}, 업데이트: {total_updated})",
            uploaded_count=total_uploaded,
            updated_count=total_updated,
            sub_results=sub_results,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped requirements upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


# ─────────────────────────────────────────────
# 그룹 6: 수강 데이터
# ─────────────────────────────────────────────
@router.post("/enrollments", response_model=GroupedUploadResponse)
async def upload_enrollments_grouped(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    수강 데이터 업로드

    CSV 컬럼:
    학번, 학수번호, 과목명, 학점, 이수구분, 성적, 평점, 재수강여부, 년도, 학기
    """
    try:
        data = await parse_upload_file(file)
        if not data:
            raise ValueError("파일에 데이터가 없습니다.")

        enrollments_list = [EnrollmentDataUpload(**row) for row in data]
        enr_resp = AdminService.upload_enrollments(db, enrollments_list)

        return GroupedUploadResponse(
            success=enr_resp.success,
            message=f"수강 데이터 업로드 완료 (추가: {enr_resp.uploaded_count}, 업데이트: {enr_resp.updated_count})",
            uploaded_count=enr_resp.uploaded_count,
            updated_count=enr_resp.updated_count,
            errors=enr_resp.errors,
            detailed_errors=enr_resp.detailed_errors,
            sub_results=[_make_sub_result("수강", enr_resp)],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grouped enrollments upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")
