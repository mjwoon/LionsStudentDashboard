"""
관리자용 서비스 로직
- 대량 데이터 업로드
- 진단 결과 캐싱
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import (
    Student, Course, Department, StudentCourse,
    StudentRequirementStatus, College, Advisor,
    Curriculum, CourseRecommendation, DepartmentEntryRequirement,
    MajorSurvey, RequirementCourse
)
from models.schemas import (
    CourseDataUpload, StudentDataUpload, EnrollmentDataUpload, MajorSurveyDataUpload,
    CurriculumDataUpload, RecommendationDataUpload, RequirementDataUpload, RequirementCourseDataUpload,
    CollegeDataUpload, DepartmentDataUpload, AdvisorDataUpload,
    DataUploadResponse, ErrorDetail, BulkEvaluationRequest, BulkEvaluationResponse,
    CachedEvaluationStats
)
from services.evaluation_service import EvaluationService
from typing import List, Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AdminService:
    """관리자 기능 서비스"""
    
    @staticmethod
    def upload_colleges(db: Session, colleges_data: List[CollegeDataUpload]) -> DataUploadResponse:
        """대학 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for college_data in colleges_data:
            try:
                existing = db.query(College).filter(College.name == college_data.name).first()
                
                if existing:
                    updated_count += 1
                else:
                    new_college = College(name=college_data.name)
                    if college_data.id is not None:
                        new_college.id = college_data.id
                    db.add(new_college)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=college_data.name, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True,
                message="대학 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            logger.error(f"대학 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False, message=f"대학 데이터 업로드 실패: {str(e)}",
                uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None
            )
    
    @staticmethod
    def upload_advisors(db: Session, advisors_data: List[AdvisorDataUpload]) -> DataUploadResponse:
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in advisors_data:
            try:
                existing = None
                if data.id is not None:
                    existing = db.query(Advisor).filter(Advisor.id == data.id).first()
                if not existing and data.email:
                    existing = db.query(Advisor).filter(Advisor.email == data.email).first()
                
                if existing:
                    existing.name = data.name
                    if data.department_id is not None:
                        existing.department_id = data.department_id
                    updated_count += 1
                else:
                    new_item = Advisor(
                        id=data.id,
                        name=data.name,
                        email=data.email,
                        department_id=data.department_id
                    )
                    db.add(new_item)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=data.name, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True, message="지도교수 데이터 업로드 완료", uploaded_count=uploaded_count,
                updated_count=updated_count, detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            return DataUploadResponse(success=False, message=str(e), uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None)

    @staticmethod
    def upload_departments(db: Session, departments_data: List[DepartmentDataUpload]) -> DataUploadResponse:
        """학과 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for dept_data in departments_data:
            try:
                # college_id 결정: 직접 지정 또는 college_name으로 매칭
                college_id = dept_data.college_id
                if not college_id and dept_data.college_name:
                    college = db.query(College).filter(College.name == dept_data.college_name).first()
                    if college:
                        college_id = college.id
                    else:
                        raise ValueError(f"대학 '{dept_data.college_name}'을 찾을 수 없습니다.")
                
                existing = db.query(Department).filter(Department.code == dept_data.code).first()
                
                if existing:
                    existing.name = dept_data.name
                    existing.min_credits = dept_data.min_credits
                    if college_id:
                        existing.college_id = college_id
                    updated_count += 1
                else:
                    new_dept = Department(
                        code=dept_data.code,
                        name=dept_data.name,
                        college_id=college_id,
                        min_credits=dept_data.min_credits
                    )
                    if dept_data.id is not None:
                        new_dept.id = dept_data.id
                    db.add(new_dept)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=dept_data.code, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True,
                message="학과 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            logger.error(f"학과 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False, message=f"학과 데이터 업로드 실패: {str(e)}",
                uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None
            )
    
    @staticmethod
    def upload_major_surveys(db: Session, surveys_data: List[MajorSurveyDataUpload]) -> DataUploadResponse:
        """희망 전공 조사 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for survey_data in surveys_data:
            try:
                # 학생 존재 확인
                student = db.query(Student).filter(Student.student_id == survey_data.student_id).first()
                if not student:
                    raise ValueError(f"학생 {survey_data.student_id}를 찾을 수 없습니다.")

                # survey_round가 없으면 생성
                from models.models import SurveyRound, DecisionStatus
                round_obj = db.query(SurveyRound).filter(SurveyRound.round_number == survey_data.survey_round_id).first()
                if not round_obj:
                    round_obj = SurveyRound(
                        round_number=survey_data.survey_round_id,
                        title=f"제{survey_data.survey_round_id}차 희망전공 수요조사",
                        status="CLOSED"
                    )
                    db.add(round_obj)
                    db.flush()
                
                # decision_status_id가 있으면 존재 여부 확인, 없으면 자동 생성
                if survey_data.decision_status_id is not None:
                    ds = db.query(DecisionStatus).filter(DecisionStatus.id == survey_data.decision_status_id).first()
                    if not ds:
                        ds = DecisionStatus(id=survey_data.decision_status_id, status_name=f"상태{survey_data.decision_status_id}")
                        db.add(ds)
                        db.flush()
                
                # 기존 데이터 확인 (동일 학생, 동일 회차)
                existing = db.query(MajorSurvey).filter(
                    MajorSurvey.student_id == survey_data.student_id,
                    MajorSurvey.survey_round_id == round_obj.id
                ).first()
                
                if existing:
                    existing.first_choice_id = survey_data.first_choice_id
                    existing.second_choice_id = survey_data.second_choice_id
                    existing.decision_status_id = survey_data.decision_status_id
                    existing.decision_scale = survey_data.decision_scale
                    updated_count += 1
                else:
                    new_survey = MajorSurvey(
                        student_id=survey_data.student_id,
                        survey_round_id=round_obj.id,
                        first_choice_id=survey_data.first_choice_id,
                        second_choice_id=survey_data.second_choice_id,
                        decision_status_id=survey_data.decision_status_id,
                        decision_scale=survey_data.decision_scale
                    )
                    if survey_data.id is not None:
                        new_survey.id = survey_data.id
                    db.add(new_survey)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=str(survey_data.student_id), reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True,
                message="희망 전공 조사 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            logger.error(f"희망전공조사 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False, message=f"희망전공조사 업로드 실패: {str(e)}",
                uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None
            )
    
    @staticmethod
    def upload_courses(db: Session, courses_data: List[CourseDataUpload]) -> DataUploadResponse:
        """과목 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        # 같은 파일 내 중복 처리를 위한 로컬 캐시 (새로 추가되거나 업데이트된 항목 추적)
        processed_courses = {}

        row_index = 2
        for course_data in courses_data:
            try:
                # 학과 찾기
                department = None
                dept_identifier = course_data.department_name or course_data.department_code
                if dept_identifier:
                    department = db.query(Department).filter(
                        (Department.name == dept_identifier) | (Department.code == dept_identifier)
                    ).first()
                
                # 먼저 이번 업로드 배치의 캐시를 확인
                if course_data.course_code in processed_courses:
                    existing_course = processed_courses[course_data.course_code]
                    updated_count += 1
                    # 이전에 '새로 생성'으로 카운트되었다면 깎지 않고 그냥 덮어씀
                else:
                    # 캐시에 없으면 DB에서 확인
                    existing_course = db.query(Course).filter(
                        Course.course_code == course_data.course_code
                    ).first()

                if existing_course:
                    existing_course.course_name = course_data.course_name
                    if course_data.course_type:
                        existing_course.course_type = course_data.course_type
                    if department:
                        existing_course.course_department = department.name
                    if course_data.course_year is not None:
                        existing_course.course_year = course_data.course_year
                    if course_data.credits is not None:
                        existing_course.credits = course_data.credits
                    if course_data.semester is not None:
                        existing_course.semester = course_data.semester
                    if course_data.description is not None:
                        existing_course.description = course_data.description
                    
                    if course_data.course_code not in processed_courses:
                        updated_count += 1
                        processed_courses[course_data.course_code] = existing_course
                else:
                    new_course = Course(
                        course_code=course_data.course_code,
                        course_name=course_data.course_name,
                        credits=course_data.credits or 3,
                        course_type=course_data.course_type,
                        course_department=department.name if department else None,
                        course_year=course_data.course_year or 1,
                        semester=course_data.semester or 1,
                        description=course_data.description
                    )
                    db.add(new_course)
                    
                    if course_data.course_code not in processed_courses:
                        uploaded_count += 1
                        processed_courses[course_data.course_code] = new_course
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=course_data.course_code, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True,
                message="과목 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            logger.error(f"과목 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False, message=f"과목 데이터 업로드 실패: {str(e)}",
                uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None
            )

    @staticmethod
    def upload_students(db: Session, students_data: List[StudentDataUpload]) -> DataUploadResponse:
        """학생 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for student_data in students_data:
            try:
                # department_id 직접 사용 (파일에서 바로 제공됨)
                department = db.query(Department).filter(
                    Department.id == student_data.department_id
                ).first()
                
                if not department:
                    raise ValueError(f"학과 ID {student_data.department_id}를 찾을 수 없습니다.")
                
                # advisor_id 검증: DB에 없으면 null 처리
                advisor_id = student_data.advisor_id
                if advisor_id is not None:
                    from models.models import Advisor
                    advisor = db.query(Advisor).filter(Advisor.id == advisor_id).first()
                    if not advisor:
                        advisor_id = None
                
                # 기존 학생 확인
                existing_student = db.query(Student).filter(
                    Student.student_id == student_data.student_id
                ).first()
                
                if existing_student:
                    # 업데이트
                    existing_student.name = student_data.name
                    existing_student.email = student_data.email
                    existing_student.phone = student_data.phone
                    existing_student.department_id = student_data.department_id
                    existing_student.advisor_id = advisor_id
                    existing_student.pride = student_data.pride
                    existing_student.class_number = student_data.class_number
                    existing_student.track = student_data.track
                    existing_student.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # 새로 생성
                    new_student = Student(
                        student_id=student_data.student_id,
                        name=student_data.name,
                        email=student_data.email,
                        phone=student_data.phone,
                        department_id=student_data.department_id,
                        advisor_id=advisor_id,
                        pride=student_data.pride,
                        class_number=student_data.class_number,
                        track=student_data.track
                    )
                    db.add(new_student)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=str(student_data.student_id), reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            
            return DataUploadResponse(
                success=True,
                message=f"학생 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"학생 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False,
                message=f"학생 데이터 업로드 실패: {str(e)}",
                uploaded_count=0,
                updated_count=0,
                errors=[str(e)],
                detailed_errors=detailed_errors if detailed_errors else None
            )
    
    @staticmethod
    def upload_enrollments(db: Session, enrollments_data: List[EnrollmentDataUpload]) -> DataUploadResponse:
        """수강 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for enrollment_data in enrollments_data:
            try:
                # 학생 찾기
                student = db.query(Student).filter(
                    Student.student_id == enrollment_data.student_id
                ).first()
                
                if not student:
                    raise ValueError(f"학생 {enrollment_data.student_id}를 찾을 수 없습니다.")
                
                # 기존 수강 기록 확인
                existing_enrollment = db.query(StudentCourse).filter(
                    StudentCourse.student_id == student.student_id,
                    StudentCourse.course_code == enrollment_data.course_code,
                    StudentCourse.year == enrollment_data.year,
                    StudentCourse.semester == enrollment_data.semester
                ).first()
                
                if existing_enrollment:
                    # 업데이트
                    existing_enrollment.course_name = enrollment_data.course_name
                    existing_enrollment.credits = enrollment_data.credits
                    existing_enrollment.completion_type = enrollment_data.completion_type
                    existing_enrollment.is_retake = enrollment_data.is_retake
                    existing_enrollment.grade = enrollment_data.grade
                    existing_enrollment.numeric_grade = enrollment_data.numeric_grade
                    updated_count += 1
                else:
                    # 새로 생성
                    new_enrollment = StudentCourse(
                        student_id=student.student_id,
                        course_code=enrollment_data.course_code,
                        course_name=enrollment_data.course_name,
                        credits=enrollment_data.credits,
                        year=enrollment_data.year,
                        semester=enrollment_data.semester,
                        completion_type=enrollment_data.completion_type,
                        is_retake=enrollment_data.is_retake,
                        grade=enrollment_data.grade,
                        numeric_grade=enrollment_data.numeric_grade
                    )
                    db.add(new_enrollment)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=f"{enrollment_data.student_id}-{enrollment_data.course_code}", reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            
            return DataUploadResponse(
                success=True,
                message=f"수강 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"수강 데이터 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False,
                message=f"수강 데이터 업로드 실패: {str(e)}",
                uploaded_count=0,
                updated_count=0,
                errors=[str(e)],
                detailed_errors=detailed_errors if detailed_errors else None
            )
    
    @staticmethod
    def upload_curriculums(db: Session, curriculums_data: List[CurriculumDataUpload]) -> DataUploadResponse:
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in curriculums_data:
            try:
                department = None
                if getattr(data, 'department_id', None):
                    department = db.query(Department).filter(Department.id == data.department_id).first()
                elif getattr(data, 'department_code', None):
                    # department_code가 숫자면 Department.id를 먼저 시도 (CSV의 교육과정학과코드가 ID인 경우)
                    if data.department_code.isdigit():
                        department = db.query(Department).filter(Department.id == int(data.department_code)).first()
                    if not department:
                        department = db.query(Department).filter(Department.code == data.department_code).first()
                    # 학과명으로도 시도
                    if not department:
                        department = db.query(Department).filter(Department.name == data.department_code).first()
                
                if not department:
                    dept_info = data.department_id or data.department_code
                    raise ValueError(f"학과 정보({dept_info})를 찾을 수 없습니다.")
                
                existing = db.query(Curriculum).filter(
                    Curriculum.department_id == department.id,
                    Curriculum.course_code == data.course_code
                ).first()
                
                if existing:
                    existing.course_year = data.course_year
                    existing.course_name = data.course_name
                    existing.credits = data.credits
                    existing.course_type = data.course_type
                    existing.semester = data.semester
                    updated_count += 1
                else:
                    new_item = Curriculum(
                        department_id=department.id,
                        course_year=data.course_year,
                        course_code=data.course_code,
                        course_name=data.course_name,
                        credits=data.credits,
                        course_type=data.course_type,
                        semester=data.semester
                    )
                    db.add(new_item)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=data.course_code, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True, message=f"교육과정 데이터 업로드 완료", uploaded_count=uploaded_count,
                updated_count=updated_count, detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            return DataUploadResponse(success=False, message=str(e), uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None)

    @staticmethod
    def upload_recommendations(db: Session, recs_data: List[RecommendationDataUpload]) -> DataUploadResponse:
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in recs_data:
            try:
                department = None
                if data.department_id:
                    department = db.query(Department).filter(Department.id == data.department_id).first()
                elif data.department_code:
                    department = db.query(Department).filter(Department.code == data.department_code).first()
                
                if not department:
                    raise ValueError(f"학과 정보(ID: {data.department_id}, 코드: {data.department_code})를 찾을 수 없습니다.")
                
                existing = None
                if getattr(data, 'id', None) is not None:
                     existing = db.query(CourseRecommendation).filter(
                        CourseRecommendation.id == data.id
                    ).first()
                     
                if not existing:
                    existing = db.query(CourseRecommendation).filter(
                        CourseRecommendation.department_id == department.id,
                        CourseRecommendation.course_name == data.course_name
                    ).first()
                
                if existing:
                     if getattr(data, 'id', None) is not None and existing.id != data.id:
                         pass
                     updated_count += 1
                else:
                    new_item = CourseRecommendation(department_id=department.id, course_name=data.course_name)
                    if getattr(data, 'id', None) is not None:
                        new_item.id = data.id
                    db.add(new_item)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=data.course_name, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True, message=f"권장과목 데이터 업로드 완료", uploaded_count=uploaded_count,
                updated_count=updated_count, detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            return DataUploadResponse(success=False, message=str(e), uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None)

    @staticmethod
    def upload_requirements(db: Session, reqs_data: List[RequirementDataUpload]) -> DataUploadResponse:
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in reqs_data:
            try:
                department = None
                if data.department_id:
                    department = db.query(Department).filter(Department.id == data.department_id).first()
                elif data.department_code:
                    department = db.query(Department).filter(Department.code == data.department_code).first()
                
                if not department:
                    raise ValueError(f"학과 정보(ID: {data.department_id}, 코드: {data.department_code})를 찾을 수 없습니다.")
                
                existing = None
                if getattr(data, 'id', None) is not None:
                     existing = db.query(DepartmentEntryRequirement).filter(
                        DepartmentEntryRequirement.id == data.id
                    ).first()
                     
                if not existing:
                    existing = db.query(DepartmentEntryRequirement).filter(
                        DepartmentEntryRequirement.department_id == department.id,
                        DepartmentEntryRequirement.admission_year == data.admission_year,
                        DepartmentEntryRequirement.requirement_group == data.requirement_group
                    ).first()
                
                if existing:
                    existing.target_grade_level = data.target_grade_level
                    existing.required_count = data.required_count
                    if hasattr(data, 'requirement_text') and data.requirement_text is not None:
                        existing.requirement_text = data.requirement_text
                    
                    if hasattr(data, 'is_alert_required') and data.is_alert_required is not None:
                        existing.is_alert_required = data.is_alert_required
                    
                    if hasattr(data, 'logic_operator') and data.logic_operator is not None:
                        existing.logic_operator = data.logic_operator
                        
                    if getattr(data, 'id', None) is not None and existing.id != data.id:
                         pass
                        
                    updated_count += 1
                else:
                    new_item = DepartmentEntryRequirement(
                        department_id=department.id,
                        admission_year=data.admission_year,
                        requirement_group=data.requirement_group,
                        target_grade_level=data.target_grade_level,
                        required_count=data.required_count,
                        requirement_text=getattr(data, 'requirement_text', ""),
                        is_alert_required=getattr(data, 'is_alert_required', False),
                        logic_operator=getattr(data, 'logic_operator', "AND")
                    )
                    if getattr(data, 'id', None) is not None:
                        new_item.id = data.id

                    db.add(new_item)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=f"ReqGrp {data.requirement_group}", reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True, message=f"학과요건 데이터 업로드 완료", uploaded_count=uploaded_count,
                updated_count=updated_count, detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            return DataUploadResponse(success=False, message=str(e), uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None)

    @staticmethod
    def upload_requirement_courses(db: Session, req_courses_data: List[RequirementCourseDataUpload]) -> DataUploadResponse:
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in req_courses_data:
            try:
                # 요건 찾기
                requirement = db.query(DepartmentEntryRequirement).filter(
                    DepartmentEntryRequirement.id == data.requirement_id
                ).first()
                if not requirement:
                    raise ValueError(f"요건 ID {data.requirement_id}를 찾을 수 없습니다.")
                    
                # 기존 맵핑 존재 여부 체크
                existing = None
                if getattr(data, 'id', None) is not None:
                     existing = db.query(RequirementCourse).filter(
                         RequirementCourse.id == data.id
                     ).first()
                     
                if not existing:
                    existing = db.query(RequirementCourse).filter(
                        RequirementCourse.requirement_id == requirement.id,
                        RequirementCourse.course_code == data.course_code
                    ).first()
                
                if existing:
                    if getattr(data, 'id', None) is not None and existing.id != data.id:
                        pass
                    updated_count += 1
                else:
                    new_item = RequirementCourse(
                        requirement_id=requirement.id,
                        course_code=data.course_code
                    )
                    if getattr(data, 'id', None) is not None:
                         new_item.id = data.id
                    db.add(new_item)
                    uploaded_count += 1
            except Exception as e:
                detailed_errors.append(ErrorDetail(row=row_index, item_id=data.course_code, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True, message=f"요건 대상 과목 매핑 데이터 업로드 완료", uploaded_count=uploaded_count,
                updated_count=updated_count, detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            return DataUploadResponse(success=False, message=str(e), uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None)

    @staticmethod
    def bulk_evaluate(db: Session, request: BulkEvaluationRequest) -> BulkEvaluationResponse:
        """대량 진단 실행 및 결과 캐싱"""
        success_count = 0
        error_count = 0
        errors = []
        
        try:
            # 학생 목록 가져오기
            students_query = db.query(Student)
            if request.student_ids:
                students_query = students_query.filter(Student.student_id.in_(request.student_ids))
            students = students_query.all()
            
            # 학과 목록 가져오기
            departments_query = db.query(Department)
            if request.department_ids:
                departments_query = departments_query.filter(Department.id.in_(request.department_ids))
            departments = departments_query.all()
            
            total_evaluations = len(students) * len(departments)
            
            # 각 학생-학과 조합에 대해 진단 수행
            for student in students:
                # 학생의 입학년도 계산 (학번 앞 4자리)
                try:
                    admission_year = int(student.student_id[:4])
                except:
                    admission_year = 2025  # 기본값
                
                for department in departments:
                    try:
                        # 기존 캐시 확인
                        existing_cache = db.query(StudentRequirementStatus).filter(
                            StudentRequirementStatus.student_id == student.student_id,
                            StudentRequirementStatus.department_id == department.id
                        ).first()
                        
                        # force_recalculate가 True이거나 캐시가 없으면 계산
                        if request.force_recalculate or not existing_cache:
                            # 진단 수행
                            evaluation_result = EvaluationService.evaluate_major_suitability(
                                db=db,
                                student_id=student.student_id,
                                department_id=department.id,
                                admission_year=admission_year
                            )
                            
                            # 결과를 JSON으로 변환
                            analysis_json = {
                                "overall_score": evaluation_result.overall_score,
                                "grade": evaluation_result.grade,
                                "required_courses": evaluation_result.required_courses,
                                "recommended_courses": evaluation_result.recommended_courses,
                                "related_credits": evaluation_result.related_credits
                            }
                            
                            # AI 요약 생성 (간단한 버전)
                            ai_summary = f"{evaluation_result.summary_message}"
                            
                            if existing_cache:
                                # 업데이트
                                existing_cache.is_satisfied = evaluation_result.overall_score >= 70
                                existing_cache.analysis_json = analysis_json
                                existing_cache.ai_summary = ai_summary
                                existing_cache.calculated_at = datetime.utcnow()
                            else:
                                # 새로 생성
                                new_cache = StudentRequirementStatus(
                                    student_id=student.student_id,
                                    department_id=department.id,
                                    is_satisfied=evaluation_result.overall_score >= 70,
                                    analysis_json=analysis_json,
                                    ai_summary=ai_summary
                                )
                                db.add(new_cache)
                            
                            success_count += 1
                        else:
                            # 캐시 사용
                            success_count += 1
                    
                    except Exception as e:
                        error_count += 1
                        errors.append(f"학생 {student.student_id} - 학과 {department.name}: {str(e)}")
                        logger.error(f"진단 오류 - 학생: {student.student_id}, 학과: {department.name}, 오류: {str(e)}")
            
            db.commit()
            
            return BulkEvaluationResponse(
                success=True,
                message=f"대량 진단 완료",
                total_students=len(students),
                total_departments=len(departments),
                total_evaluations=total_evaluations,
                success_count=success_count,
                error_count=error_count,
                errors=errors if errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"대량 진단 오류: {str(e)}")
            return BulkEvaluationResponse(
                success=False,
                message=f"대량 진단 실패: {str(e)}",
                total_students=0,
                total_departments=0,
                total_evaluations=0,
                success_count=0,
                error_count=0,
                errors=[str(e)]
            )
    
    @staticmethod
    def get_cached_evaluation_stats(db: Session) -> CachedEvaluationStats:
        """캐시된 진단 결과 통계 조회"""
        try:
            # 전체 캐시 수
            total_cached = db.query(StudentRequirementStatus).count()
            
            # 학과별 캐시 수
            cached_by_department_query = db.query(
                Department.name,
                func.count(StudentRequirementStatus.id).label('count')
            ).join(
                StudentRequirementStatus,
                Department.id == StudentRequirementStatus.department_id
            ).group_by(Department.name).all()
            
            cached_by_department = {
                dept_name: count for dept_name, count in cached_by_department_query
            }
            
            # 마지막 업데이트 시간
            last_update_result = db.query(
                func.max(StudentRequirementStatus.calculated_at)
            ).scalar()
            
            return CachedEvaluationStats(
                total_cached=total_cached,
                cached_by_department=cached_by_department,
                last_update=last_update_result
            )
        
        except Exception as e:
            logger.error(f"통계 조회 오류: {str(e)}")
            return CachedEvaluationStats(
                total_cached=0,
                cached_by_department={},
                last_update=None
            )
    
    @staticmethod
    def clear_cached_evaluations(db: Session, department_id: Optional[int] = None) -> Dict:
        """캐시된 진단 결과 삭제"""
        try:
            query = db.query(StudentRequirementStatus)
            if department_id:
                query = query.filter(StudentRequirementStatus.department_id == department_id)
            
            deleted_count = query.delete()
            db.commit()
            
            return {
                "success": True,
                "message": f"{deleted_count}개의 캐시된 진단 결과를 삭제했습니다.",
                "deleted_count": deleted_count
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f"캐시 삭제 오류: {str(e)}")
            return {
                "success": False,
                "message": f"캐시 삭제 실패: {str(e)}",
                "deleted_count": 0
            }

    @staticmethod
    def delete_all_data(db: Session) -> dict:
        """모든 업로드 데이터 삭제 (FK 순서 준수)"""
        try:
            db.query(StudentRequirementStatus).delete()
            db.query(MajorSurvey).delete()
            db.query(StudentCourse).delete()
            db.query(RequirementCourse).delete()
            db.query(CourseRecommendation).delete()
            db.query(Curriculum).delete()
            db.query(DepartmentEntryRequirement).delete()
            db.query(Student).delete()
            db.query(Advisor).delete()
            db.query(Course).delete()
            db.query(Department).delete()
            db.query(College).delete()
            db.commit()
            return {"success": True, "message": "모든 데이터가 삭제되었습니다."}
        except Exception as e:
            db.rollback()
            logger.error(f"전체 데이터 삭제 오류: {str(e)}")
            return {"success": False, "message": f"삭제 실패: {str(e)}"}
