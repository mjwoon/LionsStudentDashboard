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
from typing import List, Optional, Dict, Callable, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AdminService:
    """관리자 기능 서비스"""
    
    @staticmethod
    def _generic_upload(
        db: Session,
        data_list: List[Any],
        find_existing_callback: Callable[[Session, Any], Any],
        create_new_callback: Callable[[Session, Any], Any],
        update_existing_callback: Callable[[Session, Any, Any], None],
        item_id_accessor: Callable[[Any], str],
        success_message: str
    ) -> DataUploadResponse:
        """
        제네릭 업로드 헬퍼
        """
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for data in data_list:
            try:
                existing = find_existing_callback(db, data)
                
                if existing:
                    update_existing_callback(db, existing, data)
                    updated_count += 1
                else:
                    new_item = create_new_callback(db, data)
                    if new_item:
                        db.add(new_item)
                        uploaded_count += 1
            except Exception as e:
                item_id = ""
                try:
                    item_id = str(item_id_accessor(data))
                except:
                    pass
                detailed_errors.append(ErrorDetail(row=row_index, item_id=item_id, reason=str(e)))
            row_index += 1
            
        try:
            db.commit()
            return DataUploadResponse(
                success=True,
                message=success_message,
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                detailed_errors=detailed_errors if detailed_errors else None
            )
        except Exception as e:
            db.rollback()
            logger.error(f"{success_message.split(' ')[0]} 업로드 커밋 오류: {str(e)}")
            return DataUploadResponse(
                success=False, message=f"{success_message.split(' ')[0]} 실패: {str(e)}",
                uploaded_count=0, updated_count=0, errors=[str(e)], detailed_errors=detailed_errors if detailed_errors else None
            )

    @staticmethod
    def upload_colleges(db: Session, colleges_data: List[CollegeDataUpload]) -> DataUploadResponse:
        """대학 데이터 일괄 업로드/업데이트"""
        
        def find_existing(db: Session, data: CollegeDataUpload):
            return db.query(College).filter(College.name == data.name).first()
            
        def create_new(db: Session, data: CollegeDataUpload):
            new_college = College(name=data.name)
            if data.id is not None:
                new_college.id = data.id
            return new_college
            
        def update_existing(db: Session, existing: College, data: CollegeDataUpload):
            pass # No updates needed for college name
            
        return AdminService._generic_upload(
            db=db,
            data_list=colleges_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.name,
            success_message="대학 데이터 업로드 완료"
        )
    
    @staticmethod
    def upload_advisors(db: Session, advisors_data: List[AdvisorDataUpload]) -> DataUploadResponse:
        def find_existing(db: Session, data: AdvisorDataUpload):
            existing = None
            if data.id is not None:
                existing = db.query(Advisor).filter(Advisor.id == data.id).first()
            if not existing and data.email:
                existing = db.query(Advisor).filter(Advisor.email == data.email).first()
            return existing
            
        def create_new(db: Session, data: AdvisorDataUpload):
            return Advisor(
                id=data.id,
                name=data.name,
                email=data.email,
                department_id=data.department_id
            )
            
        def update_existing(db: Session, existing: Advisor, data: AdvisorDataUpload):
            existing.name = data.name
            if data.department_id is not None:
                existing.department_id = data.department_id

        return AdminService._generic_upload(
            db=db,
            data_list=advisors_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.name,
            success_message="지도교수 데이터 업로드 완료"
        )

    @staticmethod
    def upload_departments(db: Session, departments_data: List[DepartmentDataUpload]) -> DataUploadResponse:
        """학과 데이터 일괄 업로드/업데이트"""
        
        def _get_college_id(db: Session, dept_data: DepartmentDataUpload):
            college_id = dept_data.college_id
            if not college_id and dept_data.college_name:
                college = db.query(College).filter(College.name == dept_data.college_name).first()
                if college:
                    college_id = college.id
                else:
                    raise ValueError(f"대학 '{dept_data.college_name}'을 찾을 수 없습니다.")
            return college_id

        def find_existing(db: Session, data: DepartmentDataUpload):
            return db.query(Department).filter(Department.code == data.code).first()
            
        def create_new(db: Session, data: DepartmentDataUpload):
            college_id = _get_college_id(db, data)
            new_dept = Department(
                code=data.code,
                name=data.name,
                college_id=college_id,
                min_credits=data.min_credits
            )
            if data.id is not None:
                new_dept.id = data.id
            return new_dept
            
        def update_existing(db: Session, existing: Department, data: DepartmentDataUpload):
            college_id = _get_college_id(db, data)
            existing.name = data.name
            existing.min_credits = data.min_credits
            if college_id:
                existing.college_id = college_id

        return AdminService._generic_upload(
            db=db,
            data_list=departments_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.code,
            success_message="학과 데이터 업로드 완료"
        )
    
    @staticmethod
    def upload_major_surveys(db: Session, surveys_data: List[MajorSurveyDataUpload]) -> DataUploadResponse:
        """희망 전공 조사 데이터 일괄 업로드/업데이트"""
        
        def _prepare_survey_env(db: Session, data: MajorSurveyDataUpload):
            student = db.query(Student).filter(Student.student_id == data.student_id).first()
            if not student:
                raise ValueError(f"학생 {data.student_id}를 찾을 수 없습니다.")

            from models.models import SurveyRound, DecisionStatus
            round_obj = db.query(SurveyRound).filter(SurveyRound.round_number == data.survey_round_id).first()
            if not round_obj:
                round_obj = SurveyRound(
                    round_number=data.survey_round_id,
                    title=f"제{data.survey_round_id}차 희망전공 수요조사",
                    status="CLOSED"
                )
                db.add(round_obj)
                db.flush()
            
            if data.decision_status_id is not None:
                ds = db.query(DecisionStatus).filter(DecisionStatus.id == data.decision_status_id).first()
                if not ds:
                    ds = DecisionStatus(id=data.decision_status_id, status_name=f"상태{data.decision_status_id}")
                    db.add(ds)
                    db.flush()
            return round_obj

        def find_existing(db: Session, data: MajorSurveyDataUpload):
            round_obj = _prepare_survey_env(db, data)
            return db.query(MajorSurvey).filter(
                MajorSurvey.student_id == data.student_id,
                MajorSurvey.survey_round_id == round_obj.id
            ).first()
            
        def create_new(db: Session, data: MajorSurveyDataUpload):
            round_obj = _prepare_survey_env(db, data)
            new_survey = MajorSurvey(
                student_id=data.student_id,
                survey_round_id=round_obj.id,
                first_choice_id=data.first_choice_id,
                second_choice_id=data.second_choice_id,
                decision_status_id=data.decision_status_id,
                decision_scale=data.decision_scale
            )
            if data.id is not None:
                new_survey.id = data.id
            return new_survey
            
        def update_existing(db: Session, existing: MajorSurvey, data: MajorSurveyDataUpload):
            existing.first_choice_id = data.first_choice_id
            existing.second_choice_id = data.second_choice_id
            existing.decision_status_id = data.decision_status_id
            existing.decision_scale = data.decision_scale

        return AdminService._generic_upload(
            db=db,
            data_list=surveys_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: str(d.student_id),
            success_message="희망 전공 조사 데이터 업로드 완료"
        )
    
    @staticmethod
    def upload_courses(db: Session, courses_data: List[CourseDataUpload]) -> DataUploadResponse:
        """과목 데이터 일괄 업로드/업데이트"""
        processed_courses = {}

        def _get_department(db: Session, data: CourseDataUpload):
            dept_identifier = data.department_name or data.department_code
            if dept_identifier:
                return db.query(Department).filter(
                    (Department.name == dept_identifier) | (Department.code == dept_identifier)
                ).first()
            return None

        # Re-implementing correctly due to processed_courses dict requiring access across items
        uploaded_count = 0
        updated_count = 0
        detailed_errors = []
        
        row_index = 2
        for course_data in courses_data:
            try:
                department = _get_department(db, course_data)
                
                if course_data.course_code in processed_courses:
                    existing_course = processed_courses[course_data.course_code]
                    updated_count += 1
                else:
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
                    if getattr(course_data, 'semester', None) is not None:
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
                        semester=getattr(course_data, 'semester', None) or 1,
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
        
        def _get_advisor_id(db: Session, data: StudentDataUpload):
            advisor_id = data.advisor_id
            if advisor_id is not None:
                from models.models import Advisor
                advisor = db.query(Advisor).filter(Advisor.id == advisor_id).first()
                if not advisor:
                    advisor_id = None
            return advisor_id

        def find_existing(db: Session, data: StudentDataUpload):
            department = db.query(Department).filter(
                Department.id == data.department_id
            ).first()
            if not department:
                raise ValueError(f"학과 ID {data.department_id}를 찾을 수 없습니다.")
            return db.query(Student).filter(Student.student_id == data.student_id).first()
            
        def create_new(db: Session, data: StudentDataUpload):
            advisor_id = _get_advisor_id(db, data)
            return Student(
                student_id=data.student_id,
                name=data.name,
                email=data.email,
                phone=data.phone,
                department_id=data.department_id,
                advisor_id=advisor_id,
                pride=data.pride,
                class_number=data.class_number,
                track=data.track
            )
            
        def update_existing(db: Session, existing: Student, data: StudentDataUpload):
            advisor_id = _get_advisor_id(db, data)
            existing.name = data.name
            existing.email = data.email
            existing.phone = data.phone
            existing.department_id = data.department_id
            existing.advisor_id = advisor_id
            existing.pride = data.pride
            existing.class_number = data.class_number
            existing.track = data.track
            existing.updated_at = datetime.utcnow()

        return AdminService._generic_upload(
            db=db,
            data_list=students_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: str(d.student_id),
            success_message="학생 데이터 업로드 완료"
        )
    
    @staticmethod
    def upload_enrollments(db: Session, enrollments_data: List[EnrollmentDataUpload]) -> DataUploadResponse:
        """수강 데이터 일괄 업로드/업데이트"""
        
        def _get_student(db: Session, data: EnrollmentDataUpload):
            student = db.query(Student).filter(
                Student.student_id == data.student_id
            ).first()
            if not student:
                raise ValueError(f"학생 {data.student_id}를 찾을 수 없습니다.")
            return student

        def find_existing(db: Session, data: EnrollmentDataUpload):
            student = _get_student(db, data)
            return db.query(StudentCourse).filter(
                StudentCourse.student_id == student.student_id,
                StudentCourse.course_code == data.course_code,
                StudentCourse.year == data.year,
                StudentCourse.semester == data.semester
            ).first()
            
        def create_new(db: Session, data: EnrollmentDataUpload):
            student = _get_student(db, data)
            return StudentCourse(
                student_id=student.student_id,
                course_code=data.course_code,
                course_name=data.course_name,
                credits=data.credits,
                year=data.year,
                semester=data.semester,
                completion_type=data.completion_type,
                is_retake=data.is_retake,
                grade=data.grade,
                numeric_grade=data.numeric_grade
            )
            
        def update_existing(db: Session, existing: StudentCourse, data: EnrollmentDataUpload):
            existing.course_name = data.course_name
            existing.credits = data.credits
            existing.completion_type = data.completion_type
            existing.is_retake = data.is_retake
            existing.grade = data.grade
            existing.numeric_grade = data.numeric_grade

        return AdminService._generic_upload(
            db=db,
            data_list=enrollments_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: f"{d.student_id}-{d.course_code}",
            success_message="수강 데이터 업로드 완료"
        )
    
    @staticmethod
    def upload_curriculums(db: Session, curriculums_data: List[CurriculumDataUpload]) -> DataUploadResponse:
        def _get_department(db: Session, data: CurriculumDataUpload):
            department = None
            if getattr(data, 'department_id', None):
                department = db.query(Department).filter(Department.id == data.department_id).first()
            elif getattr(data, 'department_code', None):
                if data.department_code.isdigit():
                    department = db.query(Department).filter(Department.id == int(data.department_code)).first()
                if not department:
                    department = db.query(Department).filter(Department.code == data.department_code).first()
                if not department:
                    department = db.query(Department).filter(Department.name == data.department_code).first()
            if not department:
                dept_info = data.department_id or data.department_code
                raise ValueError(f"학과 정보({dept_info})를 찾을 수 없습니다.")
            return department

        def find_existing(db: Session, data: CurriculumDataUpload):
            department = _get_department(db, data)
            return db.query(Curriculum).filter(
                Curriculum.department_id == department.id,
                Curriculum.course_code == data.course_code
            ).first()

        def create_new(db: Session, data: CurriculumDataUpload):
            department = _get_department(db, data)
            return Curriculum(
                department_id=department.id,
                course_year=data.course_year,
                course_code=data.course_code,
                course_name=data.course_name,
                credits=data.credits,
                course_type=data.course_type,
                semester=data.semester
            )
            
        def update_existing(db: Session, existing: Curriculum, data: CurriculumDataUpload):
            existing.course_year = data.course_year
            existing.course_name = data.course_name
            existing.credits = data.credits
            existing.course_type = data.course_type
            existing.semester = data.semester

        return AdminService._generic_upload(
            db=db,
            data_list=curriculums_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.course_code,
            success_message="교육과정 데이터 업로드 완료"
        )

    @staticmethod
    def upload_recommendations(db: Session, recs_data: List[RecommendationDataUpload]) -> DataUploadResponse:
        def _get_department(db: Session, data: RecommendationDataUpload):
            department = None
            if data.department_id:
                department = db.query(Department).filter(Department.id == data.department_id).first()
            elif data.department_code:
                department = db.query(Department).filter(Department.code == data.department_code).first()
            
            if not department:
                raise ValueError(f"학과 정보(ID: {data.department_id}, 코드: {data.department_code})를 찾을 수 없습니다.")
            return department

        def find_existing(db: Session, data: RecommendationDataUpload):
            department = _get_department(db, data)
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
            return existing

        def create_new(db: Session, data: RecommendationDataUpload):
            department = _get_department(db, data)
            new_item = CourseRecommendation(department_id=department.id, course_name=data.course_name)
            if getattr(data, 'id', None) is not None:
                new_item.id = data.id
            return new_item

        def update_existing(db: Session, existing: CourseRecommendation, data: RecommendationDataUpload):
            pass

        return AdminService._generic_upload(
            db=db,
            data_list=recs_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.course_name,
            success_message="권장과목 데이터 업로드 완료"
        )

    @staticmethod
    def upload_requirements(db: Session, reqs_data: List[RequirementDataUpload]) -> DataUploadResponse:
        def _get_department(db: Session, data: RequirementDataUpload):
            department = None
            if data.department_id:
                department = db.query(Department).filter(Department.id == data.department_id).first()
            elif data.department_code:
                department = db.query(Department).filter(Department.code == data.department_code).first()
            
            if not department:
                raise ValueError(f"학과 정보(ID: {data.department_id}, 코드: {data.department_code})를 찾을 수 없습니다.")
            return department

        def find_existing(db: Session, data: RequirementDataUpload):
            department = _get_department(db, data)
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
            return existing

        def create_new(db: Session, data: RequirementDataUpload):
            department = _get_department(db, data)
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
            return new_item

        def update_existing(db: Session, existing: DepartmentEntryRequirement, data: RequirementDataUpload):
            existing.target_grade_level = data.target_grade_level
            existing.required_count = data.required_count
            if hasattr(data, 'requirement_text') and data.requirement_text is not None:
                existing.requirement_text = data.requirement_text
            if hasattr(data, 'is_alert_required') and data.is_alert_required is not None:
                existing.is_alert_required = data.is_alert_required
            if hasattr(data, 'logic_operator') and data.logic_operator is not None:
                existing.logic_operator = data.logic_operator

        return AdminService._generic_upload(
            db=db,
            data_list=reqs_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: f"ReqGrp {d.requirement_group}",
            success_message="학과요건 데이터 업로드 완료"
        )

    @staticmethod
    def upload_requirement_courses(db: Session, req_courses_data: List[RequirementCourseDataUpload]) -> DataUploadResponse:
        def _get_requirement(db: Session, data: RequirementCourseDataUpload):
            requirement = db.query(DepartmentEntryRequirement).filter(
                DepartmentEntryRequirement.id == data.requirement_id
            ).first()
            if not requirement:
                raise ValueError(f"요건 ID {data.requirement_id}를 찾을 수 없습니다.")
            return requirement

        def find_existing(db: Session, data: RequirementCourseDataUpload):
            requirement = _get_requirement(db, data)
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
            return existing

        def create_new(db: Session, data: RequirementCourseDataUpload):
            requirement = _get_requirement(db, data)
            new_item = RequirementCourse(
                requirement_id=requirement.id,
                course_code=data.course_code
            )
            if getattr(data, 'id', None) is not None:
                new_item.id = data.id
            return new_item

        def update_existing(db: Session, existing: RequirementCourse, data: RequirementCourseDataUpload):
            pass

        return AdminService._generic_upload(
            db=db,
            data_list=req_courses_data,
            find_existing_callback=find_existing,
            create_new_callback=create_new,
            update_existing_callback=update_existing,
            item_id_accessor=lambda d: d.course_code,
            success_message="요건 대상 과목 매핑 데이터 업로드 완료"
        )

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
                            evaluation_result = EvaluationService.evaluate_student(
                                student_id=student.student_id,
                                department_id=department.id,
                                admission_year=admission_year,
                                save_to_db=True
                            )
                            
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
