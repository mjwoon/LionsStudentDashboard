from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct
from typing import Optional
from database import get_db
from models.database import (
    MajorSurvey, Student, Department, SurveyRound, 
    Course, CourseEnrollment
)
from models.schemas import (
    SurveySummaryResponse, SurveyOverview, MajorPreference, SurveyStatus,
    SurveyCreate, SurveyCreateResponse, SurveySubmitData,
    SurveyRoundResponse, SurveyRoundMeta, RoundInfo, SurveySubmissionItem,
    SurveyChoiceBase
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
    
    # Calculate entry requirement completion rate
    # This is a simplified calculation
    total_enrollments = db.query(CourseEnrollment).join(Course).filter(
        Course.is_entry_requirement == True
    ).count()
    
    entry_completion_rate = 0.0
    if total_students > 0:
        avg_completions = total_enrollments / total_students
        # Assuming 3 entry requirements needed on average
        entry_completion_rate = min((avg_completions / 3) * 100, 100)
    
    # Get major preferences with counts and average decision scale
    preferences = db.query(
        Department.name,
        func.count(MajorSurvey.id).label('count'),
        func.avg(MajorSurvey.decision_scale).label('avg_scale')
    ).join(
        MajorSurvey, Department.id == MajorSurvey.first_choice_dept_id
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
            MajorSurvey.round_id == current_round.id
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
        MajorSurvey.student_id == student.id,
        MajorSurvey.round_id == survey_round.id
    ).first()
    
    if existing_survey:
        raise HTTPException(
            status_code=400, 
            detail="이미 해당 회차의 설문을 제출하셨습니다."
        )
    
    # Create new survey
    new_survey = MajorSurvey(
        student_id=student.id,
        round_id=survey_round.id,
        first_choice_dept_id=survey_data.first_choice_dept_id,
        second_choice_dept_id=survey_data.second_choice_dept_id,
        decision_scale=survey_data.decision_scale,
        submitted_at=datetime.utcnow()
    )
    
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)
    
    return SurveyCreateResponse(
        success=True,
        message="설문이 성공적으로 제출되었습니다.",
        data=SurveySubmitData(
            survey_id=new_survey.id,
            submitted_at=new_survey.submitted_at.strftime("%Y-%m-%dT%H:%M:%SZ")
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
    ).filter(MajorSurvey.round_id == round_id)
    
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
            submitted_at=survey.submitted_at.strftime("%Y-%m-%dT%H:%M:%SZ")
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
