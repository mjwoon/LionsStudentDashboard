"""
관리자용 서비스 로직
- 대량 데이터 업로드
- 진단 결과 캐싱
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import (
    Student, Course, Department, CourseEnrollment,
    StudentRequirementStatus, College, Advisor
)
from models.schemas import (
    CourseDataUpload, StudentDataUpload, EnrollmentDataUpload,
    DataUploadResponse, BulkEvaluationRequest, BulkEvaluationResponse,
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
    def upload_courses(db: Session, courses_data: List[CourseDataUpload]) -> DataUploadResponse:
        """과목 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        errors = []
        
        try:
            for course_data in courses_data:
                # 학과 코드로 학과 찾기
                department = db.query(Department).filter(
                    Department.code == course_data.department_code
                ).first()
                
                if not department:
                    errors.append(f"학과 코드 {course_data.department_code}를 찾을 수 없습니다.")
                    continue
                
                # 기존 과목 확인
                existing_course = db.query(Course).filter(
                    Course.course_code == course_data.course_code
                ).first()
                
                if existing_course:
                    # 업데이트
                    existing_course.course_name = course_data.course_name
                    existing_course.credits = course_data.credits
                    existing_course.course_type = course_data.course_type
                    existing_course.department_id = department.id
                    existing_course.course_year = course_data.course_year
                    existing_course.semester = course_data.semester
                    existing_course.is_retake_only = course_data.is_retake_only
                    existing_course.description = course_data.description
                    updated_count += 1
                else:
                    # 새로 생성
                    new_course = Course(
                        course_code=course_data.course_code,
                        course_name=course_data.course_name,
                        credits=course_data.credits,
                        course_type=course_data.course_type,
                        department_id=department.id,
                        course_year=course_data.course_year,
                        semester=course_data.semester,
                        is_retake_only=course_data.is_retake_only,
                        description=course_data.description
                    )
                    db.add(new_course)
                    uploaded_count += 1
            
            db.commit()
            
            return DataUploadResponse(
                success=True,
                message=f"과목 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                errors=errors if errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"과목 업로드 오류: {str(e)}")
            return DataUploadResponse(
                success=False,
                message=f"과목 데이터 업로드 실패: {str(e)}",
                uploaded_count=0,
                updated_count=0,
                errors=[str(e)]
            )
    
    @staticmethod
    def upload_students(db: Session, students_data: List[StudentDataUpload]) -> DataUploadResponse:
        """학생 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        errors = []
        
        try:
            for student_data in students_data:
                # 학과 코드로 학과 찾기
                department = db.query(Department).filter(
                    Department.code == student_data.department_code
                ).first()
                
                if not department:
                    errors.append(f"학과 코드 {student_data.department_code}를 찾을 수 없습니다.")
                    continue
                
                # 기존 학생 확인
                existing_student = db.query(Student).filter(
                    Student.student_id == student_data.student_id
                ).first()
                
                if existing_student:
                    # 업데이트
                    existing_student.name = student_data.name
                    existing_student.email = student_data.email
                    existing_student.phone = student_data.phone
                    existing_student.department_id = department.id
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
                        department_id=department.id,
                        pride=student_data.pride,
                        class_number=student_data.class_number,
                        track=student_data.track
                    )
                    db.add(new_student)
                    uploaded_count += 1
            
            db.commit()
            
            return DataUploadResponse(
                success=True,
                message=f"학생 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                errors=errors if errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"학생 업로드 오류: {str(e)}")
            return DataUploadResponse(
                success=False,
                message=f"학생 데이터 업로드 실패: {str(e)}",
                uploaded_count=0,
                updated_count=0,
                errors=[str(e)]
            )
    
    @staticmethod
    def upload_enrollments(db: Session, enrollments_data: List[EnrollmentDataUpload]) -> DataUploadResponse:
        """수강 데이터 일괄 업로드/업데이트"""
        uploaded_count = 0
        updated_count = 0
        errors = []
        
        try:
            for enrollment_data in enrollments_data:
                # 학생 찾기
                student = db.query(Student).filter(
                    Student.student_id == enrollment_data.student_id
                ).first()
                
                if not student:
                    errors.append(f"학생 {enrollment_data.student_id}를 찾을 수 없습니다.")
                    continue
                
                # 과목 찾기
                course = db.query(Course).filter(
                    Course.course_code == enrollment_data.course_code
                ).first()
                
                if not course:
                    errors.append(f"과목 코드 {enrollment_data.course_code}를 찾을 수 없습니다.")
                    continue
                
                # 기존 수강 기록 확인
                existing_enrollment = db.query(CourseEnrollment).filter(
                    CourseEnrollment.student_id == student.id,
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.year == enrollment_data.year,
                    CourseEnrollment.semester == enrollment_data.semester
                ).first()
                
                if existing_enrollment:
                    # 업데이트
                    existing_enrollment.completion_type = enrollment_data.completion_type
                    existing_enrollment.is_retake = enrollment_data.is_retake
                    existing_enrollment.grade = enrollment_data.grade
                    existing_enrollment.numeric_grade = enrollment_data.numeric_grade
                    updated_count += 1
                else:
                    # 새로 생성
                    new_enrollment = CourseEnrollment(
                        student_id=student.id,
                        course_id=course.id,
                        year=enrollment_data.year,
                        semester=enrollment_data.semester,
                        completion_type=enrollment_data.completion_type,
                        is_retake=enrollment_data.is_retake,
                        grade=enrollment_data.grade,
                        numeric_grade=enrollment_data.numeric_grade
                    )
                    db.add(new_enrollment)
                    uploaded_count += 1
            
            db.commit()
            
            return DataUploadResponse(
                success=True,
                message=f"수강 데이터 업로드 완료",
                uploaded_count=uploaded_count,
                updated_count=updated_count,
                errors=errors if errors else None
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"수강 데이터 업로드 오류: {str(e)}")
            return DataUploadResponse(
                success=False,
                message=f"수강 데이터 업로드 실패: {str(e)}",
                uploaded_count=0,
                updated_count=0,
                errors=[str(e)]
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
                            StudentRequirementStatus.student_id == student.id,
                            StudentRequirementStatus.department_id == department.id
                        ).first()
                        
                        # force_recalculate가 True이거나 캐시가 없으면 계산
                        if request.force_recalculate or not existing_cache:
                            # 진단 수행
                            evaluation_result = EvaluationService.evaluate_major_suitability(
                                db=db,
                                student_id=student.id,
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
                                    student_id=student.id,
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
