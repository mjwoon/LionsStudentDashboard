from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct
from typing import Optional, List
from database import get_db
from models.models import (
    MajorSurvey, Student, Department, SurveyRound, 
    Course, StudentCourse, College
)
from models.schemas import (
    SurveySummaryResponse, SurveyOverview, MajorPreference, SurveyStatus,
    SurveyCreate, SurveyCreateResponse, SurveySubmitData,
    SurveyRoundResponse, SurveyRoundMeta, RoundInfo, SurveySubmissionItem,
    SurveyChoiceBase, DashboardStatsResponse, DepartmentWithStats, 
    TrendDataPoint, CollegeBase
)
from datetime import datetime
import math

router = APIRouter(prefix="/api", tags=["surveys"])


@router.get("/surveys/summary", response_model=SurveySummaryResponse)
def get_survey_summary(db: Session = Depends(get_db)):
    """회차별 전공 희망 통계 조회"""
    
    # Get total students
    total_students = db.query(Student).count()
    
    # Get total departments (excluding 자율전공학부)
    total_departments = db.query(Department).filter(
        Department.code != "LIONSE"
    ).count()
    
    # Calculate entry requirement completion rate (simplified)
    entry_completion_rate = 0.0
    
    # Get major preferences with counts and average decision scale
    preferences = db.query(
        Department.name,
        func.count(MajorSurvey.id).label('count'),
        func.avg(MajorSurvey.decision_scale).label('avg_scale')
    ).join(
        MajorSurvey, Department.id == MajorSurvey.first_choice_id
    ).group_by(
        Department.name
    ).order_by(
        func.count(MajorSurvey.id).desc()
    ).limit(10).all()
    
    major_preferences = [
        MajorPreference(
            dept_name=pref[0],
            count=pref[1],
            avg_decision_scale=round(float(pref[2] or 0), 1)
        )
        for pref in preferences
    ]
    
    # Get current survey round info
    current_round = db.query(SurveyRound).order_by(
        SurveyRound.round_number.desc()
    ).first()
    
    current_round_number = current_round.round_number if current_round else 0
    
    # Calculate participation rate for current round
    if current_round:
        participants = db.query(MajorSurvey).filter(
            MajorSurvey.survey_round_id == current_round.id
        ).count()
        participation_rate = (participants / total_students * 100) if total_students > 0 else 0
    else:
        participation_rate = 0.0
    
    return SurveySummaryResponse(
        overview=SurveyOverview(
            total_students=total_students,
            total_departments=total_departments,
            entry_requirement_completion_rate=round(entry_completion_rate, 1)
        ),
        major_preferences=major_preferences,
        survey_status=SurveyStatus(
            current_round=current_round_number,
            participation_rate=round(participation_rate, 1)
        )
    )


@router.post("/surveys", response_model=SurveyCreateResponse, status_code=201)
def create_survey(survey_data: SurveyCreate, db: Session = Depends(get_db)):
    """학생의 전공 희망 설문 제출"""
    
    # Verify student exists
    student = db.query(Student).filter(
        Student.student_id == survey_data.student_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    
    # Verify survey round exists
    survey_round = db.query(SurveyRound).filter(
        SurveyRound.round_number == survey_data.survey_round
    ).first()
    if not survey_round:
        raise HTTPException(status_code=404, detail="설문 회차를 찾을 수 없습니다.")
    
    # Check if survey is still open
    if survey_round.status != "OPEN":
        raise HTTPException(status_code=400, detail="해당 설문은 이미 마감되었습니다.")
    
    # Verify first choice department exists
    first_dept = db.query(Department).filter(
        Department.id == survey_data.first_choice_dept_id
    ).first()
    if not first_dept:
        raise HTTPException(status_code=404, detail="1지망 학과를 찾을 수 없습니다.")
    
    # Verify second choice department if provided
    if survey_data.second_choice_dept_id:
        second_dept = db.query(Department).filter(
            Department.id == survey_data.second_choice_dept_id
        ).first()
        if not second_dept:
            raise HTTPException(status_code=404, detail="2지망 학과를 찾을 수 없습니다.")
    
    # Check if student already submitted for this round
    existing_survey = db.query(MajorSurvey).filter(
        MajorSurvey.student_id == student.student_id,
        MajorSurvey.survey_round_id == survey_round.id
    ).first()
    
    if existing_survey:
        raise HTTPException(
            status_code=400, 
            detail="이미 해당 회차의 설문을 제출하셨습니다."
        )
    
    # Create new survey
    new_survey = MajorSurvey(
        student_id=student.student_id,
        survey_round_id=survey_round.id,
        first_choice_id=survey_data.first_choice_dept_id,
        second_choice_id=survey_data.second_choice_dept_id or survey_data.first_choice_dept_id,
        decision_scale=survey_data.decision_scale,
        survey_date=datetime.utcnow()
    )
    
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)
    
    return SurveyCreateResponse(
        success=True,
        message="설문이 성공적으로 제출되었습니다.",
        data=SurveySubmitData(
            survey_id=new_survey.id,
            submitted_at=new_survey.survey_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    )


@router.get("/major-surveys/rounds/{round_id}", response_model=SurveyRoundResponse)
def get_round_surveys(
    round_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """특정 회차(1차, 2차 등) 조사 결과 조회"""
    
    # Verify round exists
    survey_round = db.query(SurveyRound).filter(
        SurveyRound.id == round_id
    ).first()
    if not survey_round:
        raise HTTPException(status_code=404, detail="설문 회차를 찾을 수 없습니다.")
    
    # Base query for submissions
    query = db.query(MajorSurvey).options(
        joinedload(MajorSurvey.student).joinedload(Student.department),
        joinedload(MajorSurvey.first_choice),
        joinedload(MajorSurvey.second_choice)
    ).filter(MajorSurvey.survey_round_id == round_id)
    
    # Get total count
    total_count = query.count()
    
    # Calculate total pages
    total_pages = math.ceil(total_count / limit)
    
    # Apply pagination
    offset = (page - 1) * limit
    submissions = query.offset(offset).limit(limit).all()
    
    # Format submissions
    submissions_list = []
    for survey in submissions:
        submission = SurveySubmissionItem(
            survey_id=survey.id,
            student_id=survey.student.student_id,
            name=survey.student.name,
            department_name=survey.student.department.name,
            first_choice=SurveyChoiceBase(
                id=survey.first_choice.id,
                name=survey.first_choice.name
            ),
            second_choice=SurveyChoiceBase(
                id=survey.second_choice.id,
                name=survey.second_choice.name
            ) if survey.second_choice else None,
            decision_scale=survey.decision_scale,
            submitted_at=survey.survey_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        submissions_list.append(submission)
    
    return SurveyRoundResponse(
        meta=SurveyRoundMeta(
            total_count=total_count,
            current_page=page,
            total_pages=total_pages,
            per_page=limit
        ),
        round_info=RoundInfo(
            round_id=survey_round.id,
            title=survey_round.title,
            status=survey_round.status
        ),
        submissions=submissions_list
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """대시보드 통계 데이터 조회"""
    
    # Department code to frontend id mapping
    dept_code_map = {
        'CS': 'cs', 'EE': 'ee', 'ME': 'mechanical', 'CHEM_ENG': 'chemical',
        'CIVIL': 'civil', 'ARCH': 'architecture', 'IE': 'industrial', 'MATER': 'materials',
        'MATH': 'math', 'PHYS': 'physics', 'CHEM': 'chem', 'BIO': 'bio',
        'EARTH': 'earth', 'ASTRO': 'astronomy',
        'BIZ': 'business', 'ACCT': 'accounting', 'FIN': 'finance', 'MKT': 'marketing',
        'KOR': 'korean', 'ENG': 'english', 'HIST': 'history', 'PHIL': 'philosophy', 'CHI': 'chinese',
        'ECON': 'economics', 'POL': 'political', 'SOC': 'sociology', 'PSY': 'psychology',
        'MEDIA': 'media', 'LAW': 'law'
    }
    
    # Department colors
    dept_colors = {
        'cs': '#3b82f6', 'ee': '#10b981', 'mechanical': '#f59e0b', 'chemical': '#ef4444',
        'civil': '#8b5cf6', 'architecture': '#ec4899', 'industrial': '#14b8a6', 'materials': '#f97316',
        'math': '#06b6d4', 'physics': '#6366f1', 'chem': '#a855f7', 'bio': '#ec4899',
        'earth': '#84cc16', 'astronomy': '#0ea5e9',
        'business': '#f59e0b', 'accounting': '#eab308', 'finance': '#22c55e', 'marketing': '#06b6d4',
        'korean': '#8b5cf6', 'english': '#6366f1', 'history': '#a855f7', 'philosophy': '#ec4899', 'chinese': '#f43f5e',
        'economics': '#10b981', 'political': '#3b82f6', 'sociology': '#f59e0b', 'psychology': '#ef4444',
        'media': '#8b5cf6', 'law': '#14b8a6'
    }
    
    # College name to id mapping
    college_map = {
        '공과대학': 'engineering',
        '자연과학대학': 'science',
        '경영대학': 'business',
        '인문대학': 'humanities',
        '사회과학대학': 'social'
    }
    
    # Get colleges
    colleges_db = db.query(College).filter(College.id != 1).all()
    colleges = [CollegeBase(id=college.id, name=college.name) for college in colleges_db]
    
    # Get latest round
    latest_round = db.query(SurveyRound).order_by(SurveyRound.round_number.desc()).first()
    
    if not latest_round:
        return DashboardStatsResponse(
            colleges=colleges,
            departments=[],
            current_data=[],
            trend_data=[]
        )
    
    # Get current data (latest round statistics)
    current_stats = db.query(
        Department.code,
        Department.name,
        College.id.label('college_id'),
        func.count(MajorSurvey.id).label('count')
    ).join(
        MajorSurvey, Department.id == MajorSurvey.first_choice_id
    ).join(
        College, Department.college_id == College.id
    ).filter(
        MajorSurvey.survey_round_id == latest_round.id,
        Department.code != 'LIONSE'
    ).group_by(
        Department.id, Department.code, Department.name, College.id
    ).order_by(
        func.count(MajorSurvey.id).desc()
    ).all()
    
    total_students = sum(stat.count for stat in current_stats)
    
    departments_list = []
    current_data_list = []
    
    for stat in current_stats:
        dept_id = dept_code_map.get(stat.code, stat.code.lower())
        college_id = str(stat.college_id)
        color = dept_colors.get(dept_id, '#6b7280')
        percent = (stat.count / total_students * 100) if total_students > 0 else 0
        
        dept_data = DepartmentWithStats(
            id=dept_id,
            name=stat.name,
            college=college_id,
            color=color,
            students=stat.count,
            percent=round(percent, 1)
        )
        departments_list.append(dept_data)
        current_data_list.append(dept_data)
    
    # Get trend data (all rounds)
    rounds = db.query(SurveyRound).order_by(SurveyRound.round_number).all()
    trend_data_list = []
    
    for idx, round_obj in enumerate(rounds, 1):
        round_stats = db.query(
            Department.code,
            func.count(MajorSurvey.id).label('count')
        ).join(
            MajorSurvey, Department.id == MajorSurvey.first_choice_id
        ).filter(
            MajorSurvey.survey_round_id == round_obj.id,
            Department.code != 'LIONSE'
        ).group_by(
            Department.code
        ).all()
        
        data_dict = {}
        for stat in round_stats:
            dept_id = dept_code_map.get(stat.code, stat.code.lower())
            data_dict[dept_id] = stat.count
        
        trend_data_list.append(TrendDataPoint(
            period=f"{idx}차",
            data=data_dict
        ))
    
    return DashboardStatsResponse(
        colleges=colleges,
        departments=departments_list,
        current_data=current_data_list,
        trend_data=trend_data_list
    )
