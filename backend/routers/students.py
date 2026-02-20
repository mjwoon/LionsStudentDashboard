from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Optional, List
from database import get_db
from models.models import Student, Department, Advisor, StudentCourse, Course, MajorSurvey
from models.schemas import (
    StudentListResponse, StudentDetail, StudentInList, StudentCreate, 
    StudentCreateResponse, StudentCoursesResponse, StudentSurveysResponse,
    DepartmentBase, AcademicInfo, CourseEnrollmentDetail, SurveyHistoryItem,
    SurveyChoiceBase
)
from services.student_service import calculate_first_year_completion
from datetime import datetime
import math

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students", response_model=StudentListResponse)
def get_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    department_id: Optional[int] = None,
    pride: Optional[str] = None,
    class_number: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """학생 목록 조회 (필터링 및 페이징 지원)"""
    
    # Base query with joins (optimize N+1 queries)
    query = db.query(Student).options(
        joinedload(Student.department).joinedload(Department.college),
        joinedload(Student.advisor),
        selectinload(Student.surveys)
    )
    
    # Apply filters
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if pride:
        query = query.filter(Student.pride == pride)
    if class_number:
        query = query.filter(Student.class_number == class_number)
    if status:
        query = query.filter(Student.status == status)
    if search:
        # Search in student_id, name, email
        search_pattern = f"%{search}%"
        query = query.filter(
            (Student.student_id.like(search_pattern)) |
            (Student.name.like(search_pattern)) |
            (Student.email.like(search_pattern))
        )
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    students = query.offset(offset).limit(per_page).all()
    
    # Pre-load departments for efficiency (cache)
    all_departments = {dept.id: dept for dept in db.query(Department).all()}
    
    # Format response
    students_list = []
    for student in students:
        # 최신 희망 학과 조회 (이미 selectinload로 로드됨)
        latest_survey = None
        if student.surveys:
            latest_survey = max(student.surveys, key=lambda s: s.survey_round_id)
        
        latest_major_choice = None
        decision_certainty = None
        first_choice_dept_id = None
        
        if latest_survey:
            first_choice_dept = all_departments.get(latest_survey.first_choice_id)
            if first_choice_dept:
                latest_major_choice = first_choice_dept.name
                first_choice_dept_id = first_choice_dept.id
            decision_certainty = latest_survey.decision_scale
        
        # 이수현황 계산: 최신 희망학과의 1학년 과목 이수 현황 (헬퍼 함수 사용)
        completion_status = "0/0"
        course_suitability = None
        
        if first_choice_dept_id:
            completed, total = calculate_first_year_completion(
                db, student.student_id, first_choice_dept_id
            )
            completion_status = f"{completed}/{total}"
            
            # 수강과목 적합성: 전체 적합도 점수 (평가 시스템 사용)
            from services.evaluation_service import EvaluationService
            evaluator = EvaluationService(db)
            try:
                eval_result = evaluator.evaluate_student(
                    student.student_id, first_choice_dept_id, save_to_db=False
                )
                # overall_score를 백분율 형식으로 반환
                course_suitability = f"{eval_result['overall_score']:.0f}점"
            except:
                # 평가 실패 시 기본값
                course_suitability = None
        
        student_data = StudentInList(
            student_id=student.student_id,
            name=student.name,
            email=student.email,
            phone=student.phone,
            department=DepartmentBase(
                id=student.department.id,
                name=student.department.name
            ),
            academic_info=AcademicInfo(
                pride=student.pride,
                class_number=student.class_number,
                track=student.track,
                advisor_name=student.advisor.name if student.advisor else None,
                status=student.status,
                updated_at=student.updated_at
            ),
            latest_major_choice=latest_major_choice,
            decision_certainty=decision_certainty,
            completion_status=completion_status,
            course_suitability=course_suitability
        )
        students_list.append(student_data)
    
    return StudentListResponse(
        count=total_count,
        page=page,
        per_page=per_page,
        students=students_list
    )


@router.get("/students/{student_id}", response_model=StudentDetail)
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """특정 학생 상세 프로필 조회"""
    
    student = db.query(Student).options(
        joinedload(Student.department).joinedload(Department.college),
        joinedload(Student.advisor)
    ).filter(Student.student_id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    
    return StudentDetail(
        student_id=student.student_id,
        name=student.name,
        email=student.email,
        phone=student.phone,
        department=DepartmentBase(
            id=student.department.id,
            name=student.department.name
        ),
        academic_info=AcademicInfo(
            pride=student.pride,
            class_number=student.class_number,
            track=student.track,
            advisor_id=student.advisor_id,
            advisor_name=student.advisor.name if student.advisor else None,
            status=student.status,
            updated_at=student.updated_at
        )
    )


@router.get("/students/{student_id}/courses", response_model=StudentCoursesResponse)
def get_student_courses(student_id: str, db: Session = Depends(get_db)):
    """학생 수강 이력 조회"""
    
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    
    enrollments = db.query(StudentCourse).options(
        joinedload(StudentCourse.course)
    ).filter(StudentCourse.student_id == student.student_id).all()
    
    total_credits = sum(enrollment.course.credits for enrollment in enrollments)
    
    course_history = []
    for enrollment in enrollments:
        course_detail = CourseEnrollmentDetail(
            course_id=enrollment.course.course_id,
            course_code=enrollment.course.course_code,
            course_name=enrollment.course.course_name,
            credits=enrollment.course.credits,
            year=enrollment.year,
            semester=enrollment.semester,
            completion_type=enrollment.completion_type,
            is_retake=enrollment.is_retake,
            grade=enrollment.grade,
            numeric_grade=float(enrollment.numeric_grade) if enrollment.numeric_grade else None
        )
        course_history.append(course_detail)
    
    return StudentCoursesResponse(
        student_id=student_id,
        total_credits=total_credits,
        course_history=course_history
    )


@router.get("/students/{student_id}/surveys", response_model=StudentSurveysResponse)
def get_student_surveys(student_id: str, db: Session = Depends(get_db)):
    """학생의 전공 희망 조사 이력 조회"""
    
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    
    surveys = db.query(MajorSurvey).options(
        joinedload(MajorSurvey.survey_round),
        joinedload(MajorSurvey.first_choice),
        joinedload(MajorSurvey.second_choice)
    ).filter(MajorSurvey.student_id == student.student_id).order_by(
        MajorSurvey.survey_date.desc()
    ).all()
    
    history = []
    for survey in surveys:
        survey_item = SurveyHistoryItem(
            survey_id=survey.id,
            round=survey.survey_round.round_number,
            submitted_at=survey.survey_date.strftime("%Y-%m-%d"),
            first_choice=SurveyChoiceBase(
                id=survey.first_choice.id,
                name=survey.first_choice.name
            ),
            second_choice=SurveyChoiceBase(
                id=survey.second_choice.id,
                name=survey.second_choice.name
            ) if survey.second_choice else None,
            decision_scale=survey.decision_scale
        )
        history.append(survey_item)
    
    return StudentSurveysResponse(history=history)


@router.post("/students", response_model=StudentCreateResponse, status_code=201)
def create_student(student_data: StudentCreate, db: Session = Depends(get_db)):
    """신규 학생 등록"""
    
    # Check if student already exists
    existing_student = db.query(Student).filter(
        Student.student_id == student_data.student_id
    ).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")
    
    # Check if email already exists
    existing_email = db.query(Student).filter(
        Student.email == student_data.email
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
    
    # Verify department exists
    department = db.query(Department).filter(
        Department.id == student_data.department_id
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="학과를 찾을 수 없습니다.")
    
    # Verify advisor exists if provided
    if student_data.advisor_id:
        advisor = db.query(Advisor).filter(Advisor.id == student_data.advisor_id).first()
        if not advisor:
            raise HTTPException(status_code=404, detail="지도교수를 찾을 수 없습니다.")
    
    # Create new student
    new_student = Student(
        student_id=student_data.student_id,
        name=student_data.name,
        email=student_data.email,
        phone=student_data.phone,
        department_id=student_data.department_id,
        advisor_id=student_data.advisor_id,
        pride=student_data.pride,
        class_number=student_data.class_number,
        status="재학"
    )
    
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    
    return StudentCreateResponse(
        message="학생이 성공적으로 등록되었습니다.",
        student_id=new_student.student_id
    )
