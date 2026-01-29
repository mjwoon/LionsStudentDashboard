from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from models.models import Student, Department, College, MajorSurvey, CourseEnrollment, Course
from database import get_db
from sqlalchemy import func, desc, case

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    대시보드 통계 데이터 반환
    
    Returns:
        - colleges: 단과대학 목록
        - departments: 학과 목록 (단과대학 정보 포함)
        - current_data: 현재 희망학과별 학생 수 및 비율
        - trend_data: 시계열 추세 데이터 (회차별)
        - student_stats: 전체 학생 통계
        - grade_distribution: 성적 분포 데이터
    """
    
    # 1. 단과대학 목록 조회
    colleges = db.query(College).all()
    colleges_data = [
        {
            "id": college.id,
            "name": college.name,
            "code": college.code
        }
        for college in colleges
    ]
    
    # 2. 학과 목록 조회 (단과대학 정보 포함)
    departments = db.query(Department).all()
    departments_data = [
        {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "college": str(dept.college_id),  # DashboardView에서 string으로 비교함
            "college_name": dept.college.name if dept.college else None
        }
        for dept in departments
    ]
    
    # 3. 현재 데이터: 가장 최근 설문 기준 희망학과별 학생 수
    # 각 학생의 가장 최근 설문의 1지망 학과를 집계
    subquery = (
        db.query(
            MajorSurvey.student_id,
            func.max(MajorSurvey.round_id).label("max_round")
        )
        .group_by(MajorSurvey.student_id)
        .subquery()
    )
    
    latest_surveys = (
        db.query(MajorSurvey)
        .join(
            subquery,
            (MajorSurvey.student_id == subquery.c.student_id) &
            (MajorSurvey.round_id == subquery.c.max_round)
        )
        .all()
    )
    
    # 1지망 학과별 학생 수 집계
    dept_student_count = {}
    for survey in latest_surveys:
        if survey.first_choice_dept_id:
            dept_id = survey.first_choice_dept_id
            dept_student_count[dept_id] = dept_student_count.get(dept_id, 0) + 1
    
    # 총 학생 수 (설문 제출한 학생)
    total_students = len(latest_surveys)
    
    # 학과별 데이터 생성
    current_data = []
    for dept in departments:
        count = dept_student_count.get(dept.id, 0)
        percent = round((count / total_students * 100), 1) if total_students > 0 else 0
        current_data.append({
            "id": dept.id,
            "name": dept.name,
            "students": count,
            "percent": percent
        })
    
    # 학생 수 기준 내림차순 정렬
    current_data.sort(key=lambda x: x["students"], reverse=True)
    
    # 4. 추세 데이터: 회차별 희망학과 변화
    # 모든 설문 회차 조회
    all_rounds = db.query(MajorSurvey.round_id).distinct().order_by(MajorSurvey.round_id).all()
    round_ids = [r[0] for r in all_rounds]
    
    trend_data = []
    for round_id in round_ids:
        # 해당 회차의 설문 조회
        round_surveys = db.query(MajorSurvey).filter(
            MajorSurvey.round_id == round_id
        ).all()
        
        # 학과별 학생 수 집계
        round_dept_count = {}
        for survey in round_surveys:
            if survey.first_choice_dept_id:
                dept_id = survey.first_choice_dept_id
                # 학과명 찾기
                dept = db.query(Department).filter(Department.id == dept_id).first()
                if dept:
                    dept_name = dept.name
                    round_dept_count[dept_name] = round_dept_count.get(dept_name, 0) + 1
        
        trend_data.append({
            "period": f"{round_id}차",
            "data": round_dept_count
        })
    
    # 5. 전체 학생 통계
    total_students_count = db.query(func.count(Student.id)).scalar()
    
    # GPA 통계
    gpa_stats = db.query(
        func.avg(Student.current_gpa).label("avg_gpa"),
        func.max(Student.current_gpa).label("max_gpa"),
        func.min(Student.current_gpa).label("min_gpa")
    ).filter(Student.current_gpa > 0).first()
    
    # 학점 통계
    credits_stats = db.query(
        func.avg(Student.total_credits).label("avg_credits"),
        func.max(Student.total_credits).label("max_credits"),
        func.min(Student.total_credits).label("min_credits")
    ).filter(Student.total_credits > 0).first()
    
    # 계열별 학생 수
    track_distribution = db.query(
        Student.track,
        func.count(Student.id).label("count")
    ).group_by(Student.track).all()
    
    student_stats = {
        "total_students": total_students_count,
        "avg_gpa": round(float(gpa_stats.avg_gpa), 2) if gpa_stats.avg_gpa else 0,
        "max_gpa": round(float(gpa_stats.max_gpa), 2) if gpa_stats.max_gpa else 0,
        "min_gpa": round(float(gpa_stats.min_gpa), 2) if gpa_stats.min_gpa else 0,
        "avg_credits": round(float(credits_stats.avg_credits), 1) if credits_stats.avg_credits else 0,
        "max_credits": int(credits_stats.max_credits) if credits_stats.max_credits else 0,
        "min_credits": int(credits_stats.min_credits) if credits_stats.min_credits else 0,
        "track_distribution": [
            {"track": track, "count": count}
            for track, count in track_distribution
        ]
    }
    
    # 6. 성적 분포 데이터
    # 전체 학생의 GPA 구간별 분포
    gpa_ranges = [
        ("4.0 이상", 4.0, 4.5),
        ("3.5~3.99", 3.5, 3.99),
        ("3.0~3.49", 3.0, 3.49),
        ("2.5~2.99", 2.5, 2.99),
        ("2.0~2.49", 2.0, 2.49),
        ("2.0 미만", 0.0, 1.99)
    ]
    
    grade_distribution = []
    for range_name, min_gpa, max_gpa in gpa_ranges:
        count = db.query(func.count(Student.id)).filter(
            Student.current_gpa >= min_gpa,
            Student.current_gpa <= max_gpa
        ).scalar()
        
        grade_distribution.append({
            "range": range_name,
            "count": count,
            "percent": round((count / total_students_count * 100), 1) if total_students_count > 0 else 0
        })
    
    # 학과별 평균 GPA (상위 10개 학과)
    dept_gpa_stats = []
    for dept in departments:
        # 해당 학과를 희망하는 학생들의 평균 GPA
        dept_student_ids = [s.student_id for s in latest_surveys if s.first_choice_dept_id == dept.id]
        
        if dept_student_ids:
            avg_gpa = db.query(func.avg(Student.current_gpa)).filter(
                Student.id.in_(dept_student_ids),
                Student.current_gpa > 0
            ).scalar()
            
            if avg_gpa:
                dept_gpa_stats.append({
                    "department": dept.name,
                    "avg_gpa": round(float(avg_gpa), 2),
                    "student_count": len(dept_student_ids)
                })
    
    # 평균 GPA 기준 내림차순 정렬 후 상위 10개
    dept_gpa_stats.sort(key=lambda x: x["avg_gpa"], reverse=True)
    
    return {
        "colleges": colleges_data,
        "departments": departments_data,
        "current_data": current_data,
        "trend_data": trend_data,
        "student_stats": student_stats,
        "grade_distribution": grade_distribution,
        "department_gpa_stats": dept_gpa_stats[:10]
    }

