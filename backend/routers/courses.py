from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from database import get_db
from models.database import Course, Department, College
from models.schemas import (
    CourseListResponse, CourseInList, CourseFlags, DepartmentBase,
    EntryRequirementsResponse, EntryRequirementCourse,
    DepartmentListResponse, DepartmentDetail, DepartmentCurriculum
)

router = APIRouter(prefix="/api", tags=["courses"])


@router.get("/courses", response_model=CourseListResponse)
def get_courses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    course_type: Optional[str] = None,
    department_id: Optional[int] = None,
    is_entry_requirement: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """전체 과목 목록 조회 (유형별 필터)"""
    
    # Base query with joins
    query = db.query(Course).options(
        joinedload(Course.department)
    )
    
    # Apply filters
    if course_type:
        query = query.filter(Course.course_type == course_type)
    if department_id:
        query = query.filter(Course.department_id == department_id)
    if is_entry_requirement is not None:
        query = query.filter(Course.is_entry_requirement == is_entry_requirement)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    courses = query.offset(offset).limit(per_page).all()
    
    # Format response
    courses_list = []
    for course in courses:
        course_data = CourseInList(
            course_id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department=DepartmentBase(
                id=course.department.id,
                name=course.department.name
            ),
            flags=CourseFlags(
                is_entry_requirement=course.is_entry_requirement,
                is_recommended=course.is_recommended,
                is_retake_only=course.is_retake_only
            ),
            description=course.description
        )
        courses_list.append(course_data)
    
    return CourseListResponse(
        count=total_count,
        page=page,
        per_page=per_page,
        courses=courses_list
    )


@router.get("/courses/entry-requirements", response_model=EntryRequirementsResponse)
def get_entry_requirements(db: Session = Depends(get_db)):
    """전공 진입 필수 과목 목록 조회"""
    
    courses = db.query(Course).options(
        joinedload(Course.department)
    ).filter(Course.is_entry_requirement == True).all()
    
    courses_list = []
    for course in courses:
        course_data = EntryRequirementCourse(
            course_id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department_id=course.department.id,
            department_name=course.department.name,
            is_recommended=course.is_recommended
        )
        courses_list.append(course_data)
    
    return EntryRequirementsResponse(
        count=len(courses_list),
        courses=courses_list
    )


@router.get("/departments", response_model=DepartmentListResponse)
def get_departments(db: Session = Depends(get_db)):
    """학과 리스트 및 졸업 학점 확인"""
    
    departments = db.query(Department).options(
        joinedload(Department.college)
    ).all()
    
    departments_list = []
    for dept in departments:
        dept_data = DepartmentDetail(
            id=dept.id,
            code=dept.code,
            name=dept.name,
            college_name=dept.college.name if dept.college else "",
            min_credits=dept.min_credits,
            homepage_url=dept.homepage_url
        )
        departments_list.append(dept_data)
    
    return DepartmentListResponse(
        count=len(departments_list),
        departments=departments_list
    )


@router.get("/departments/{department_id}/courses", response_model=CourseListResponse)
def get_department_courses(
    department_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """특정 학과 관장 과목 조회"""
    
    # Verify department exists
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="학과를 찾을 수 없습니다.")
    
    # Query courses for this department
    query = db.query(Course).options(
        joinedload(Course.department)
    ).filter(Course.department_id == department_id)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    courses = query.offset(offset).limit(per_page).all()
    
    # Format response
    courses_list = []
    for course in courses:
        course_data = CourseInList(
            course_id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department=DepartmentBase(
                id=course.department.id,
                name=course.department.name
            ),
            flags=CourseFlags(
                is_entry_requirement=course.is_entry_requirement,
                is_recommended=course.is_recommended,
                is_retake_only=course.is_retake_only
            ),
            description=course.description
        )
        courses_list.append(course_data)
    
    return CourseListResponse(
        count=total_count,
        page=page,
        per_page=per_page,
        courses=courses_list
    )


@router.get("/departments/{department_id}/curriculum", response_model=DepartmentCurriculum)
def get_department_curriculum(department_id: int, db: Session = Depends(get_db)):
    """특정 학과의 교육과정 정보 조회"""
    
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="학과를 찾을 수 없습니다.")
    
    # This is a simplified version - in a real application, you would have
    # separate tables for tracks and requirements
    return DepartmentCurriculum(
        department_name=department.name,
        graduation_min_credits=department.min_credits,
        tracks=["기본 트랙"],  # Placeholder - should come from database
        entry_requirements_description="전공기초 과목 이수 및 평점 요건 충족"
    )
