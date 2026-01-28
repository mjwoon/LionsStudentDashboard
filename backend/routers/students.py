from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from database import get_db
from models.database import Student, Department, Advisor, CourseEnrollment, Course, MajorSurvey
from models.schemas import (
    StudentListResponse, StudentDetail, StudentInList, StudentCreate, 
    StudentCreateResponse, StudentCoursesResponse, StudentSurveysResponse,
    DepartmentBase, AcademicInfo, CourseEnrollmentDetail, SurveyHistoryItem,
    SurveyChoiceBase
)
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
    db: Session = Depends(get_db)
):
    """학생 목록 조회 (필터링 및 페이징 지원)"""
    
    # Base query with joins
    query = db.query(Student).options(
        joinedload(Student.department).joinedload(Department.college),
        joinedload(Student.advisor)
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
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    students = query.offset(offset).limit(per_page).all()
    
    # Format response
    students_list = []
    for student in students:
        # 최신 희망 학과 조회
        latest_survey = db.query(MajorSurvey).filter(
            MajorSurvey.student_id == student.id
        ).order_by(MajorSurvey.round_id.desc()).first()
        
        latest_major_choice = None
        decision_certainty = None
        first_choice_dept_id = None
        if latest_survey:
            first_choice_dept = db.query(Department).filter(
                Department.id == latest_survey.first_choice_dept_id
            ).first()
            if first_choice_dept:
                latest_major_choice = first_choice_dept.name
                first_choice_dept_id = first_choice_dept.id
            decision_certainty = latest_survey.decision_scale
        
        # 이수현황 계산: 최신 희망학과의 1학년 과목 이수 현황
        completion_status = "0/0"
        course_suitability = "0%"
        
        if first_choice_dept_id:
            # 희망학과의 1학년 과목 목록 조회
            first_year_courses = db.query(Course).filter(
                Course.department_id == first_choice_dept_id,
                Course.course_year == 1
            ).all()
            
            if first_year_courses:
                total_first_year = len(first_year_courses)
                first_year_course_ids = [c.id for c in first_year_courses]
                
                # 학생이 해당 학과 1학년 과목 중 이수한 과목 수
                completed_first_year = db.query(CourseEnrollment).filter(
                    CourseEnrollment.student_id == student.id,
                    CourseEnrollment.course_id.in_(first_year_course_ids),
                    CourseEnrollment.grade.isnot(None),
                    CourseEnrollment.grade != 'F'
                ).count()
                
                completion_status = f"{completed_first_year}/{total_first_year}"
                
                # 수강과목 적합성: 희망학과 1학년 과목 이수율
                completion_rate = (completed_first_year / total_first_year) * 100 if total_first_year > 0 else 0
                course_suitability = f"{completion_rate:.1f}%"
        
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
    
    enrollments = db.query(CourseEnrollment).options(
        joinedload(CourseEnrollment.course)
    ).filter(CourseEnrollment.student_id == student.id).all()
    
    total_credits = sum(enrollment.course.credits for enrollment in enrollments)
    
    course_history = []
    for enrollment in enrollments:
        course_detail = CourseEnrollmentDetail(
            course_id=enrollment.course.id,
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
    ).filter(MajorSurvey.student_id == student.id).order_by(
        MajorSurvey.submitted_at.desc()
    ).all()
    
    history = []
    for survey in surveys:
        survey_item = SurveyHistoryItem(
            survey_id=survey.id,
            round=survey.survey_round.round_number,
            submitted_at=survey.submitted_at.strftime("%Y-%m-%d"),
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
