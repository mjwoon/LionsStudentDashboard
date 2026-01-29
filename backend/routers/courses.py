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
        query = query.filter(Course.department_id == department_id)
    
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
        joinedload(DepartmentEntryRequirement.requirement_courses)
    )
    
    if department_id:
        query = query.filter(DepartmentEntryRequirement.department_id == department_id)
    if admission_year:
        query = query.filter(DepartmentEntryRequirement.admission_year == admission_year)
    
    requirements = query.all()
    
    # 요건에 포함된 모든 과목 수집
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
            course_id=course.id,
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


@router.get("/courses/curriculum", response_model=dict)
def get_full_curriculum(
    department_id: Optional[int] = Query(300, description="학과 ID (기본값: 300 컴퓨터학부)"),
    db: Session = Depends(get_db)
):
    """전체 교육과정 조회 (학년/학기별 구조화) - JSON 파일 기반"""
    
    import json
    import os
    
    # 학과별 JSON 파일 매핑
    dept_json_map = {
        300: "sw.json",
        303: "dataIntelli.json",
        304: "designConverge.json",
        200: "arch.json",
        204: "elec.json",
        207: "ime.json"
    }
    
    if department_id not in dept_json_map:
        return {"curriculum": {}, "total_courses": 0}
    
    # JSON 파일 읽기
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", dept_json_map[department_id])
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"curriculum": {}, "total_courses": 0}
    
    # 권장 과목 데이터 로드
    recommended_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "recommended.json")
    recommended_courses = set()
    try:
        with open(recommended_path, "r", encoding="utf-8") as f:
            recommended_data = json.load(f)
            
            # 해당 학과의 권장 과목 찾기
            dept = db.query(Department).filter(Department.id == department_id).first()
            if dept:
                dept_name = dept.name
                for college in recommended_data["colleges"]:
                    for major in college["majors"]:
                        if major["name"] in dept_name or dept_name in major["name"]:
                            recommended_courses = set(major["recommended_courses"])
                            break
    except FileNotFoundError:
        pass  # 권장 과목 파일이 없으면 무시
    
    # 진입요건 과목 조회
    from models.models import DepartmentEntryRequirement, RequirementCourse
    
    entry_requirement_courses = set()
    requirements = db.query(DepartmentEntryRequirement).filter(
        DepartmentEntryRequirement.department_id == department_id
    ).all()
    
    for req in requirements:
        req_courses = db.query(RequirementCourse).filter(
            RequirementCourse.requirement_id == req.id
        ).all()
        for rc in req_courses:
            entry_requirement_courses.add(rc.course_code)
    
    # 학년/학기별로 그룹화
    curriculum = {}
    total_courses = 0
    
    for course_info in data["curriculum"]:
        year = course_info.get("course_year", 0)
        semester = course_info.get("semester", 0)
        
        year_key = f"{year}학년" if year > 0 else "기타"
        sem_key = f"{semester}학기" if semester > 0 else "학기미정"
        
        if year_key not in curriculum:
            curriculum[year_key] = {}
        if sem_key not in curriculum[year_key]:
            curriculum[year_key][sem_key] = []
        
        # DB에서 course_id 조회 (없으면 0)
        db_course = db.query(Course).filter(Course.course_code == course_info["course_code"]).first()
        course_id = db_course.id if db_course else 0
        
        # 권장 과목 체크
        is_recommended = course_info["course_name"] in recommended_courses
        
        # 진입요건 과목 체크
        is_entry_requirement = course_info["course_code"] in entry_requirement_courses
        
        curriculum[year_key][sem_key].append({
            "course_id": course_id,
            "course_code": course_info["course_code"],
            "course_name": course_info["course_name"],
            "credits": course_info["credits"],
            "course_type": course_info["course_type"],
            "is_entry_requirement": is_entry_requirement,
            "is_recommended": is_recommended,
            "department_name": data.get("department", "")
        })
        total_courses += 1
    
    return {
        "curriculum": curriculum,
        "total_courses": total_courses
    }
