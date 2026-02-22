from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from database import get_db
from models.models import Course, Department, College
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
        dept = db.query(Department).filter(Department.id == department_id).first()
        if dept:
            query = query.filter(Course.course_department == dept.name)
        else:
            return CourseListResponse(count=0, page=page, per_page=per_page, courses=[])
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    courses = query.offset(offset).limit(per_page).all()
    
    # Format response
    courses_list = []
    for course in courses:
        course_data = CourseInList(
            course_id=course.course_id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department=DepartmentBase(
                id=course.department.id,
                name=course.department.name
            ),
            flags=CourseFlags(
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
def get_entry_requirements(
    department_id: Optional[int] = None,
    admission_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """전공 진입 요건 조회 (새로운 구조)"""
    from models.models import DepartmentEntryRequirement, RequirementCourse
    
    # 진입요건 조회
    query = db.query(DepartmentEntryRequirement).options(
        joinedload(DepartmentEntryRequirement.requirement_courses).joinedload(RequirementCourse.course)
    )
    
    if department_id:
        query = query.filter(DepartmentEntryRequirement.department_id == department_id)
    if admission_year:
        query = query.filter(DepartmentEntryRequirement.admission_year == admission_year)
    
    requirements = query.all()
    
    # 요건에 포함된 모든 과목 수집 (course_code FK를 통해)
    all_course_codes = set()
    for req in requirements:
        for req_course in req.requirement_courses:
            all_course_codes.add(req_course.course_code)
    
    # 과목 정보 조회
    courses = db.query(Course).options(
        joinedload(Course.department)
    ).filter(Course.course_code.in_(all_course_codes)).all()
    
    courses_list = []
    for course in courses:
        course_data = EntryRequirementCourse(
            course_id=course.course_id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department_id=course.department.id,
            department_name=course.department.name,
            is_recommended=False  # 이제 별도 테이블에서 관리
        )
        courses_list.append(course_data)
    
    return EntryRequirementsResponse(
        count=len(courses_list),
        courses=courses_list
    )


@router.get("/departments", response_model=DepartmentListResponse)
def get_departments(db: Session = Depends(get_db)):
    """학과 리스트 및 졸업 학점 확인"""
    from models.models import DepartmentEntryRequirement
    
    departments = db.query(Department).options(
        joinedload(Department.college)
    ).all()
    
    # Check which departments have entry requirements configured
    eval_dept_ids = {
        r[0] for r in db.query(DepartmentEntryRequirement.department_id).distinct().all()
    }
    
    departments_list = []
    for dept in departments:
        dept_data = DepartmentDetail(
            id=dept.id,
            code=dept.code,
            name=dept.name,
            college_name=dept.college.name if dept.college else "",
            min_credits=dept.min_credits,
            is_evaluation_available=(dept.id in eval_dept_ids)
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
    ).filter(Course.course_department == department.name)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    courses = query.offset(offset).limit(per_page).all()
    
    # Format response
    courses_list = []
    for course in courses:
        course_data = CourseInList(
            course_id=course.course_id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            course_type=course.course_type,
            department=DepartmentBase(
                id=course.department.id,
                name=course.department.name
            ),
            flags=CourseFlags(
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
    
    return DepartmentCurriculum(
        department_name=department.name,
        graduation_min_credits=department.min_credits,
        tracks=["기본 트랙"],  # Placeholder - should come from database
        entry_requirements_description="전공기초 과목 이수 및 평점 요건 충족"
    )


@router.get("/courses/curriculum", response_model=dict)
def get_full_curriculum(
    department_id: Optional[int] = Query(None, description="학과 ID"),
    db: Session = Depends(get_db)
):
    """전체 교육과정 조회 (학년/학기별 구조화) - DB 기반 처리"""
    
    from models.models import Curriculum, CourseRecommendation, DepartmentEntryRequirement, RequirementCourse
    
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        return {"curriculum": {}, "total_courses": 0}
        
    dept_name = dept.name
    
    # 해당 학과의 모든 교육과정(Curriculum) 조회
    curriculums = db.query(Curriculum).filter(Curriculum.department_id == department_id).all()
    
    # 해당 학과의 권장 과목명 조회
    recommended_courses = set()
    recs = db.query(CourseRecommendation).filter(CourseRecommendation.department_id == department_id).all()
    for r in recs:
        recommended_courses.add(r.course_name)
        
    # 해당 학과의 진입요건 과목 Code 조회
    entry_requirement_codes = set()
    requirements = db.query(DepartmentEntryRequirement).filter(
        DepartmentEntryRequirement.department_id == department_id
    ).all()
    
    for req in requirements:
        req_courses = db.query(RequirementCourse).filter(
            RequirementCourse.requirement_id == req.id
        ).all()
        for rc in req_courses:
            entry_requirement_codes.add(rc.course_code)
            
    # 관련 Course 정보 일괄 조회를 위해 course_code 수집
    course_codes = [c.course_code for c in curriculums]
    courses_db = db.query(Course).filter(Course.course_code.in_(course_codes)).all()
    course_map = {c.course_code: c for c in courses_db}
    
    curriculum_grouped = {}
    total_courses = 0
    
    for cur in curriculums:
        course_db = course_map.get(cur.course_code)
        
        # 만약 Course 테이블에 없는 과목이라면 기본값 세팅
        credits = course_db.credits if course_db else 3
        course_type = course_db.course_type if course_db else "전공선택"
        course_id = course_db.course_id if course_db else 0
        semester = course_db.semester if course_db and course_db.semester else 0
        
        # 학년(Curriculum.course_year 기준) 및 학기
        year = cur.course_year
        year_key = f"{year}학년" if year > 0 else "기타"
        sem_key = f"{semester}학기" if semester > 0 else "학기미정"
        
        if year_key not in curriculum_grouped:
            curriculum_grouped[year_key] = {}
        if sem_key not in curriculum_grouped[year_key]:
            curriculum_grouped[year_key][sem_key] = []
            
        is_recommended = cur.course_name in recommended_courses
        is_entry_requirement = cur.course_code in entry_requirement_codes
        
        curriculum_grouped[year_key][sem_key].append({
            "course_id": course_id,
            "course_code": cur.course_code,
            "course_name": cur.course_name,
            "credits": credits,
            "course_type": course_type,
            "is_entry_requirement": is_entry_requirement,
            "is_recommended": is_recommended,
            "department_name": dept_name
        })
        total_courses += 1
        
    return {
        "curriculum": curriculum_grouped,
        "total_courses": total_courses
    }
