"""
전공진입 적합도 평가 알고리즘

학생별로 각 학과에 대한 진입 적합도를 계산하는 서비스
요구사항_정리_0122.md 기반으로 구현
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from models.database import (
    Student,
    Course,
    CourseEnrollment,
    Department,
    DepartmentEntryRequirement,
    RequirementCourse,
    StudentRequirementStatus,
    GradeLevelEnum,
)


class MajorSuitabilityEvaluator:
    """전공 적합도 평가 클래스"""
    
    # 가중치 설정
    WEIGHT_REQUIRED_COURSES = 0.70  # 필수 과목 70%
    WEIGHT_RECOMMENDED_COURSES = 0.20  # 권장 과목 20%
    WEIGHT_RELATED_CREDITS = 0.10  # 관련 학점 10%
    
    # 성적 등급 -> 점수 매핑
    GRADE_POINTS = {
        'A+': 4.5, 'A0': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B0': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C0': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D0': 1.0, 'D-': 0.7,
        'F': 0.0, 'P': 3.0, 'NP': 0.0
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_student_for_department(
        self, 
        student_id: int, 
        department_id: int,
        admission_year: int = 2025
    ) -> Dict:
        """
        특정 학생의 특정 학과에 대한 적합도 평가
        
        Args:
            student_id: 학생 ID
            department_id: 평가할 학과 ID
            admission_year: 입학년도 (진입요건 기준)
            
        Returns:
            평가 결과 딕셔너리
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"학생 ID {student_id}를 찾을 수 없습니다.")
        
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ValueError(f"학과 ID {department_id}를 찾을 수 없습니다.")
        
        # 학생의 수강 내역 조회
        enrollments = self.db.query(CourseEnrollment).filter(
            CourseEnrollment.student_id == student_id
        ).all()
        
        # 해당 학과의 진입요건 조회
        entry_requirements = self.db.query(DepartmentEntryRequirement).filter(
            and_(
                DepartmentEntryRequirement.department_id == department_id,
                DepartmentEntryRequirement.admission_year == admission_year
            )
        ).all()
        
        # 1. 필수 과목 평가
        required_result = self._evaluate_required_courses(
            enrollments, entry_requirements, department_id
        )
        
        # 2. 권장 과목 평가
        recommended_result = self._evaluate_recommended_courses(
            enrollments, department_id
        )
        
        # 3. 관련 학점 평가
        related_credits_result = self._evaluate_related_credits(
            enrollments, department_id
        )
        
        # 4. 종합 적합도 계산
        overall_score = (
            required_result['score'] * self.WEIGHT_REQUIRED_COURSES +
            recommended_result['score'] * self.WEIGHT_RECOMMENDED_COURSES +
            related_credits_result['score'] * self.WEIGHT_RELATED_CREDITS
        )
        
        # 5. 평가 등급 결정
        grade = self._calculate_grade(overall_score)
        
        # 6. 종합 메시지 생성
        summary_message = self._generate_summary_message(
            required_result, recommended_result, related_credits_result, grade
        )
        
        return {
            'student_id': student_id,
            'department_id': department_id,
            'department_name': department.name,
            'admission_year': admission_year,
            'required_courses': required_result,
            'recommended_courses': recommended_result,
            'related_credits': related_credits_result,
            'overall_score': round(overall_score, 2),
            'grade': grade,
            'summary_message': summary_message,
            'evaluated_at': datetime.utcnow().isoformat()
        }
    
    def _evaluate_required_courses(
        self,
        enrollments: List[CourseEnrollment],
        entry_requirements: List[DepartmentEntryRequirement],
        department_id: int
    ) -> Dict:
        """
        필수 과목 이수 평가
        
        Returns:
            {
                'score': float,  # 0-100점
                'total_requirements': int,  # 전체 요건 수
                'satisfied_requirements': int,  # 충족한 요건 수
                'details': List[Dict],  # 각 요건별 상세 정보
                'pass': bool  # 전체 통과 여부
            }
        """
        if not entry_requirements:
            return {
                'score': 100.0,
                'total_requirements': 0,
                'satisfied_requirements': 0,
                'details': [],
                'pass': True,
                'message': '진입요건이 설정되지 않은 학과입니다.'
            }
        
        # 학생이 이수한 과목 코드와 성적 매핑
        enrolled_courses = {}
        for enrollment in enrollments:
            course = self.db.query(Course).filter(Course.id == enrollment.course_id).first()
            if course:
                enrolled_courses[course.course_code] = {
                    'grade': enrollment.grade,
                    'numeric_grade': enrollment.numeric_grade,
                    'course_name': course.course_name,
                    'credits': course.credits
                }
        
        details = []
        satisfied_count = 0
        total_count = len(entry_requirements)
        
        for requirement in entry_requirements:
            # 해당 요건의 과목 목록 조회
            req_courses = self.db.query(RequirementCourse).filter(
                RequirementCourse.requirement_id == requirement.id
            ).all()
            
            requirement_course_codes = [rc.course_code for rc in req_courses]
            
            # 학생이 이수한 과목 중 요건을 충족하는 과목 찾기
            satisfied_courses = []
            for course_code in requirement_course_codes:
                if course_code in enrolled_courses:
                    course_info = enrolled_courses[course_code]
                    # 성적 조건 확인
                    if self._check_grade_requirement(
                        course_info.get('numeric_grade'),
                        requirement.target_grade_level
                    ):
                        satisfied_courses.append({
                            'course_code': course_code,
                            'course_name': course_info['course_name'],
                            'grade': course_info['grade'],
                            'credits': course_info['credits']
                        })
            
            # 요건 충족 여부 판단
            is_satisfied = len(satisfied_courses) >= requirement.required_count
            if is_satisfied:
                satisfied_count += 1
            
            details.append({
                'requirement_id': requirement.id,
                'requirement_group': requirement.requirement_group,
                'requirement_text': requirement.requirement_text,
                'target_grade': requirement.target_grade_level.value if requirement.target_grade_level else None,
                'required_count': requirement.required_count,
                'total_courses': len(requirement_course_codes),
                'satisfied_count': len(satisfied_courses),
                'satisfied_courses': satisfied_courses,
                'is_satisfied': is_satisfied,
                'is_alert_required': requirement.is_alert_required
            })
        
        # 점수 계산: (충족한 요건 수 / 전체 요건 수) * 100
        score = (satisfied_count / total_count * 100) if total_count > 0 else 100.0
        pass_status = satisfied_count == total_count
        
        return {
            'score': round(score, 2),
            'total_requirements': total_count,
            'satisfied_requirements': satisfied_count,
            'details': details,
            'pass': pass_status,
            'message': f'{total_count}개 요건 중 {satisfied_count}개 충족'
        }
    
    def _evaluate_recommended_courses(
        self,
        enrollments: List[CourseEnrollment],
        department_id: int
    ) -> Dict:
        """
        권장 과목 이수 평가
        
        해당 학과의 전공기초, 전공핵심 과목 이수 현황 평가
        """
        # 해당 학과의 전공기초, 전공핵심 과목 조회
        recommended_courses = self.db.query(Course).filter(
            and_(
                Course.department_id == department_id,
                Course.course_type.in_(['전공기초', '전공핵심'])
            )
        ).all()
        
        if not recommended_courses:
            return {
                'score': 100.0,
                'total_courses': 0,
                'completed_courses': 0,
                'completion_rate': 100.0,
                'details': [],
                'message': '권장 과목 정보가 없습니다.'
            }
        
        # 학생이 이수한 과목 ID 세트
        enrolled_course_ids = {e.course_id for e in enrollments}
        
        # 이수한 권장 과목
        completed = []
        total_credits = 0
        completed_credits = 0
        
        for course in recommended_courses:
            total_credits += course.credits
            if course.id in enrolled_course_ids:
                enrollment = next(e for e in enrollments if e.course_id == course.id)
                completed.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'course_type': course.course_type,
                    'credits': course.credits,
                    'grade': enrollment.grade
                })
                completed_credits += course.credits
        
        completion_rate = (completed_credits / total_credits * 100) if total_credits > 0 else 0
        
        # 점수는 이수율에 비례
        score = completion_rate
        
        return {
            'score': round(score, 2),
            'total_courses': len(recommended_courses),
            'completed_courses': len(completed),
            'total_credits': total_credits,
            'completed_credits': completed_credits,
            'completion_rate': round(completion_rate, 2),
            'details': completed,
            'message': f'{len(recommended_courses)}개 권장 과목 중 {len(completed)}개 이수 ({completion_rate:.1f}%)'
        }
    
    def _evaluate_related_credits(
        self,
        enrollments: List[CourseEnrollment],
        department_id: int
    ) -> Dict:
        """
        관련 학점 평가
        
        해당 학과의 모든 전공 과목에 대한 이수 학점 평가
        """
        # 해당 학과의 모든 전공 과목
        all_major_courses = self.db.query(Course).filter(
            and_(
                Course.department_id == department_id,
                Course.course_type.like('%전공%')
            )
        ).all()
        
        if not all_major_courses:
            return {
                'score': 50.0,
                'total_available_credits': 0,
                'earned_credits': 0,
                'message': '전공 과목 정보가 없습니다.'
            }
        
        # 학생이 이수한 해당 학과 전공 과목 학점
        enrolled_course_ids = {e.course_id for e in enrollments}
        earned_credits = sum(
            course.credits for course in all_major_courses 
            if course.id in enrolled_course_ids
        )
        
        # 전체 이용 가능한 학점 (1-2학년 과목 기준)
        available_credits = sum(
            course.credits for course in all_major_courses
            if course.course_year and course.course_year <= 2
        )
        
        # 목표: 1-2학년 전공 과목의 50% 이상 이수 시 만점
        target_credits = available_credits * 0.5
        
        if target_credits > 0:
            score = min((earned_credits / target_credits) * 100, 100.0)
        else:
            score = 50.0
        
        return {
            'score': round(score, 2),
            'total_available_credits': available_credits,
            'earned_credits': earned_credits,
            'target_credits': round(target_credits, 2),
            'message': f'{available_credits}학점 중 {earned_credits}학점 이수'
        }
    
    def _check_grade_requirement(
        self,
        numeric_grade: Optional[float],
        target_grade_level: Optional[GradeLevelEnum]
    ) -> bool:
        """
        성적이 요구 등급을 충족하는지 확인
        
        Args:
            numeric_grade: 숫자 성적 (예: 4.5, 3.0)
            target_grade_level: 목표 등급 (A, B, C)
            
        Returns:
            충족 여부
        """
        if not target_grade_level:
            return True  # 성적 조건 없음
        
        if numeric_grade is None:
            return False
        
        # 등급 기준점
        grade_thresholds = {
            GradeLevelEnum.A: 4.0,  # A 이상
            GradeLevelEnum.B: 3.0,  # B 이상
            GradeLevelEnum.C: 2.0,  # C 이상
        }
        
        threshold = grade_thresholds.get(target_grade_level, 0.0)
        return numeric_grade >= threshold
    
    def _calculate_grade(self, score: float) -> str:
        """
        종합 점수를 등급으로 변환
        
        Args:
            score: 종합 점수 (0-100)
            
        Returns:
            등급 문자열
        """
        if score >= 90:
            return 'S'  # Excellent
        elif score >= 80:
            return 'A'  # Very Good
        elif score >= 70:
            return 'B'  # Good
        elif score >= 60:
            return 'C'  # Fair
        elif score >= 50:
            return 'D'  # Poor
        else:
            return 'F'  # Very Poor
    
    def _generate_summary_message(
        self,
        required_result: Dict,
        recommended_result: Dict,
        related_credits_result: Dict,
        grade: str
    ) -> str:
        """
        종합 평가 메시지 생성
        """
        messages = []
        
        # 등급별 기본 메시지
        grade_messages = {
            'S': '우수: 전공진입 준비가 매우 잘 되어있습니다!',
            'A': '양호: 전공진입 요건을 잘 충족하고 있습니다.',
            'B': '보통: 전공진입이 가능하나 추가 과목 이수를 권장합니다.',
            'C': '주의: 전공진입 요건 충족을 위해 노력이 필요합니다.',
            'D': '경고: 전공진입 필수 과목 이수율을 높여야 합니다.',
            'F': '위험: 전공진입을 위해 많은 과목 이수가 필요합니다.'
        }
        
        messages.append(grade_messages.get(grade, '평가 완료'))
        
        # 필수 과목 관련
        if not required_result['pass']:
            unsatisfied = required_result['total_requirements'] - required_result['satisfied_requirements']
            messages.append(f"진입요건 {unsatisfied}개가 미충족 상태입니다.")
            
            # Alert가 필요한 요건이 있는지 확인
            alert_requirements = [
                d for d in required_result['details'] 
                if not d['is_satisfied'] and d['is_alert_required']
            ]
            if alert_requirements:
                messages.append("⚠️ 필수 확인 사항이 있습니다. 상세 내용을 확인하세요.")
        
        # 권장 과목 관련
        if recommended_result['completion_rate'] < 30:
            messages.append(f"권장 과목 이수율이 {recommended_result['completion_rate']:.0f}%로 낮습니다. 전공기초/핵심 과목을 더 수강하세요.")
        
        return ' '.join(messages)
    
    def batch_evaluate_all_students(self, department_id: int, admission_year: int = 2025) -> List[Dict]:
        """
        특정 학과에 대해 모든 학생 평가 (배치 처리)
        
        Args:
            department_id: 평가할 학과 ID
            admission_year: 입학년도
            
        Returns:
            모든 학생의 평가 결과 리스트
        """
        students = self.db.query(Student).all()
        results = []
        
        for student in students:
            try:
                result = self.evaluate_student_for_department(
                    student.id, department_id, admission_year
                )
                results.append(result)
            except Exception as e:
                print(f"학생 {student.student_id} 평가 중 오류: {e}")
                continue
        
        return results
    
    def save_evaluation_results(self, evaluation_results: List[Dict]) -> int:
        """
        평가 결과를 데이터베이스에 저장
        
        Args:
            evaluation_results: evaluate_student_for_department 결과 리스트
            
        Returns:
            저장된 레코드 수
        """
        saved_count = 0
        
        for result in evaluation_results:
            # 기존 레코드 확인
            existing = self.db.query(StudentRequirementStatus).filter(
                and_(
                    StudentRequirementStatus.student_id == result['student_id'],
                    StudentRequirementStatus.department_id == result['department_id']
                )
            ).first()
            
            # 저장할 데이터 구성 (기존 스키마에 맞춤)
            status_data = {
                'student_id': result['student_id'],
                'department_id': result['department_id'],
                'is_satisfied': result['required_courses']['pass'],
                'analysis_json': result,  # 전체 결과를 JSON으로 저장
                'ai_summary': result['summary_message'],
                'calculated_at': datetime.utcnow()
            }
            
            if existing:
                # 업데이트
                for key, value in status_data.items():
                    setattr(existing, key, value)
            else:
                # 신규 생성
                new_status = StudentRequirementStatus(**status_data)
                self.db.add(new_status)
            
            saved_count += 1
        
        self.db.commit()
        return saved_count


# Admin service를 위한 래퍼 클래스
class EvaluationService:
    """평가 서비스 - admin_service.py에서 사용하기 위한 정적 메서드 제공"""
    
    @staticmethod
    def evaluate_major_suitability(db: Session, student_id: int, department_id: int, admission_year: int):
        """학생의 특정 학과에 대한 전공 적합도 평가"""
        evaluator = MajorSuitabilityEvaluator(db)
        result = evaluator.evaluate_student_for_department(student_id, department_id, admission_year)
        
        # 딕셔너리를 객체처럼 접근할 수 있도록 SimpleNamespace로 변환
        from types import SimpleNamespace
        return SimpleNamespace(**result)
