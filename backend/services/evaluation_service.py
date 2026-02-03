"""
전공진입 적합도 평가 서비스

2-메트릭 기반 평가 시스템:
- 1학년 전공체계도 완성도 (70%)
- 유사과목 점수 (30%)
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict
from datetime import datetime
import json
import os

from models.models import (
    Student, Department, Course, CourseEnrollment,
    DepartmentEntryRequirement, RequirementCourse,
    StudentRequirementStatus, GradeLevelEnum
)
from constants import (
    GRADE_TO_NUMERIC,
    WEIGHT_CURRICULUM_COMPLETION,
    WEIGHT_RELATED_COURSES,
    GRADE_THRESHOLDS,
    MAX_GPA,
    FIRST_YEAR,
    FAILING_GRADE,
    MIN_SATISFACTION_SCORE
)


class EvaluationService:
    """2개 메트릭 기반 평가 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self._necessary_data = None
        self._recommended_data = None
    
    def _load_necessary_courses(self) -> Dict:
        """necessary.json 파일 로드"""
        if self._necessary_data is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            necessary_path = os.path.join(data_dir, 'necessary.json')
            try:
                with open(necessary_path, 'r', encoding='utf-8') as f:
                    self._necessary_data = json.load(f)
            except FileNotFoundError:
                self._necessary_data = {"colleges": []}
        return self._necessary_data
    
    def _load_recommended_courses(self) -> Dict:
        """recommended.json 파일 로드"""
        if self._recommended_data is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            recommended_path = os.path.join(data_dir, 'recommended.json')
            try:
                with open(recommended_path, 'r', encoding='utf-8') as f:
                    self._recommended_data = json.load(f)
            except FileNotFoundError:
                self._recommended_data = {"colleges": []}
        return self._recommended_data
    
    def _get_department_courses(self, department_id: int) -> Dict:
        """학과의 필수/권장 과목 정보 조회"""
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            return {"necessary_courses": [], "recommended_courses": []}
        
        dept_name = department.name
        
        # 필수 과목 조회
        necessary_data = self._load_necessary_courses()
        necessary_courses = []
        for college in necessary_data.get("colleges", []):
            for major in college.get("majors", []):
                if major.get("name") == dept_name:
                    # course_code 리스트 추출
                    necessary_courses = [
                        course["course_code"] 
                        for course in major.get("necessary_courses", [])
                    ]
                    break
        
        # 권장 과목 조회
        recommended_data = self._load_recommended_courses()
        recommended_courses = []
        for college in recommended_data.get("colleges", []):
            for major in college.get("majors", []):
                if major.get("name") == dept_name:
                    recommended_courses = major.get("recommended_courses", [])
                    break
        
        return {
            "necessary_courses": necessary_courses,
            "recommended_courses": recommended_courses
        }
    
    def evaluate_student(
        self,
        student_id: int,
        department_id: int,
        admission_year: int = 2026,
        save_to_db: bool = True
    ) -> Dict:
        """
        학생의 학과 적합도를 2개 메트릭으로 평가
        
        Args:
            student_id: 학생 ID
            department_id: 평가 대상 학과 ID
            admission_year: 입학연도 (진입요건 기준)
            save_to_db: StudentRequirementStatus에 저장 여부
            
        Returns:
            평가 결과 딕셔너리
        """
        # 학생 정보 조회
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"학생 ID {student_id}를 찾을 수 없습니다.")
        
        # 학과 정보 조회
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ValueError(f"학과 ID {department_id}를 찾을 수 없습니다.")
        
        # 학생의 수강 이력 조회
        enrollments = self.db.query(CourseEnrollment).filter(
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.grade.isnot(None),
            CourseEnrollment.grade != ""
        ).all()
        
        # 1. 1학년 전공체계도 완성도 점수 (70%)
        curriculum_completion_score = self._calculate_curriculum_completion_score(
            enrollments, department_id
        )
        
        # 2. 유사과목 점수 (30%)
        related_courses_score = self._calculate_related_courses_score(
            enrollments, department_id
        )
        
        # 3. 종합 점수 계산
        overall_score = (
            curriculum_completion_score * WEIGHT_CURRICULUM_COMPLETION +
            related_courses_score * WEIGHT_RELATED_COURSES
        )
        
        # 4. 상세 분석 JSON 생성
        analysis_json = self._build_analysis_json(
            student, department, enrollments,
            curriculum_completion_score, related_courses_score
        )
        
        # 5. 등급 판정
        if overall_score >= GRADE_THRESHOLDS['A']:
            grade = 'A'
        elif overall_score >= GRADE_THRESHOLDS['B']:
            grade = 'B'
        elif overall_score >= GRADE_THRESHOLDS['C']:
            grade = 'C'
        elif overall_score >= GRADE_THRESHOLDS['D']:
            grade = 'D'
        else:
            grade = 'F'
        
        result = {
            'student_id': student_id,
            'department_id': department_id,
            'department_name': department.name,
            'curriculum_completion_score': round(curriculum_completion_score, 2),
            'related_courses_score': round(related_courses_score, 2),
            'overall_score': round(overall_score, 2),
            'grade': grade,
            'analysis_json': analysis_json,
            'evaluated_at': datetime.utcnow()
        }
        
        # DB에 저장
        if save_to_db:
            self._save_evaluation_result(student_id, department_id, admission_year, result)
        
        return result
    
    def _calculate_curriculum_completion_score(
        self,
        enrollments: List[CourseEnrollment],
        department_id: int
    ) -> float:
        """
        1학년 전공체계도 완성도 점수 (70%)
        
        해당 학과의 1학년 과목 중 이수한 비율
        """
        # 해당 학과의 1학년 과목 조회
        dept_courses = self.db.query(Course).filter(
            Course.department_id == department_id,
            Course.course_year == FIRST_YEAR
        ).all()
        
        # 1학년 과목이 없으면 0점 반환
        if not dept_courses:
            return 0.0
        
        dept_course_ids = {c.id for c in dept_courses}
        
        # 이수한 전공과목 개수 (F학점 제외)
        completed_count = sum(
            1 for enrollment in enrollments
            if enrollment.course_id in dept_course_ids and
            enrollment.grade and enrollment.grade != FAILING_GRADE
        )
        
        # 비율을 점수로 환산
        score = (completed_count / len(dept_courses)) * 100
        return round(min(100.0, score), 2)
    
    def _calculate_related_courses_score(
        self,
        enrollments: List[CourseEnrollment],
        department_id: int
    ) -> float:
        """
        유사과목 점수 (30%)
        
        전공체계도에는 없으나 학생이 수강한 과목 중에서
        전공체계도의 과목과 유사한 과목을 찾아 점수 부여
        
        유사도 판단 기준:
        1. 동일 학과의 다른 학년 과목
        2. 과목명에 유사한 키워드가 포함된 경우
        3. 동일 분야의 기초/심화 과목
        """
        # 해당 학과의 1학년 과목 조회
        dept_first_year_courses = self.db.query(Course).filter(
            Course.department_id == department_id,
            Course.course_year == FIRST_YEAR
        ).all()
        
        if not dept_first_year_courses:
            return 0.0
        
        # 1학년 과목 ID 세트
        first_year_course_ids = {c.id for c in dept_first_year_courses}
        
        # 학생이 수강한 과목 중 1학년 과목이 아닌 것들
        other_enrollments = [
            e for e in enrollments
            if e.course_id not in first_year_course_ids and
            e.grade and e.grade != FAILING_GRADE
        ]
        
        if not other_enrollments:
            return 0.0
        
        # 유사과목 점수 계산
        related_count = 0
        
        for enrollment in other_enrollments:
            course = self.db.query(Course).filter(
                Course.id == enrollment.course_id
            ).first()
            
            if not course:
                continue
            
            # 유사도 체크
            if self._is_related_course(course, dept_first_year_courses, department_id):
                related_count += 1
        
        # 유사과목 수를 1학년 과목 수 대비 비율로 계산
        # 최대 100점까지 가능 (유사과목이 1학년 과목 수만큼 있으면 만점)
        max_related = len(dept_first_year_courses)
        score = (related_count / max_related) * 100
        
        return round(min(100.0, score), 2)
    
    def _is_related_course(
        self,
        course: Course,
        dept_first_year_courses: List[Course],
        department_id: int
    ) -> bool:
        """
        과목이 전공체계도 과목과 유사한지 판단
        
        유사도 판단 기준:
        1. 동일 학과의 2-4학년 과목
        2. 과목명에 1학년 과목과 유사한 키워드 포함
        """
        # 기준 1: 동일 학과의 상급 학년 과목
        if course.department_id == department_id and course.course_year and course.course_year > FIRST_YEAR:
            return True
        
        # 기준 2: 과목명 키워드 유사도
        course_name_lower = course.course_name.lower()
        
        # 1학년 과목들의 키워드 추출
        keywords = set()
        for first_year_course in dept_first_year_courses:
            # 과목명에서 주요 키워드 추출 (예: "미분적분학" -> "미분", "적분")
            name = first_year_course.course_name
            # 간단한 키워드 추출 (2글자 이상)
            if len(name) >= 2:
                keywords.add(name[:2])
                keywords.add(name[:3] if len(name) >= 3 else name)
                keywords.add(name)
        
        # 현재 과목명에 키워드가 포함되어 있는지 확인
        for keyword in keywords:
            if keyword.lower() in course_name_lower:
                return True
        
        return False
    
    
    def _save_evaluation_result(
        self,
        student_id: int,
        department_id: int,
        admission_year: int,
        result: Dict
    ):
        """평가 결과를 StudentRequirementStatus 테이블에 저장"""
        # 기존 레코드 찾기
        status = self.db.query(StudentRequirementStatus).filter(
            StudentRequirementStatus.student_id == student_id,
            StudentRequirementStatus.department_id == department_id
        ).first()
        
        if not status:
            # 새로 생성
            status = StudentRequirementStatus(
                student_id=student_id,
                department_id=department_id
            )
            self.db.add(status)
        
        # 점수 업데이트
        status.curriculum_completion_score = result['curriculum_completion_score']
        status.related_courses_score = result['related_courses_score']
        status.overall_score = result['overall_score']
        status.analysis_json = result.get('analysis_json')
        status.calculated_at = result['evaluated_at']
        
        # 충족 여부 판정 (overall_score가 MIN_SATISFACTION_SCORE 이상)
        status.is_satisfied = result['overall_score'] >= MIN_SATISFACTION_SCORE
        
        self.db.commit()
    
    def get_curriculum_details(self, student_id: int, department_id: int) -> Dict[int, List[Dict]]:
        """
        전체 학년 전공이수체계도 상세 정보 반환 (학년별로 그룹화)
        교양필수, 전공기초 과목도 포함
        
        Args:
            student_id: 학생 ID
            department_id: 학과 ID
            
        Returns:
            학년별 체계도 과목 딕셔너리 {1: [...], 2: [...], 3: [...], 4: [...]}
        """
        # 해당 학과의 전체 과목 + 교양필수/전공기초 과목 조회 (1~4학년)
        # course_type이 교양필수 또는 전공기초인 과목도 포함
        dept_courses = self.db.query(Course).filter(
            or_(
                Course.department_id == department_id,
                Course.course_type == '교양필수',
                Course.course_type == '전공기초'
            ),
            Course.course_year.in_([1, 2, 3, 4])
        ).order_by(Course.course_year, Course.semester, Course.course_code).all()
        
        if not dept_courses:
            return {}
        
        # 학생의 수강 이력 조회
        enrollments = self.db.query(CourseEnrollment).filter(
            CourseEnrollment.student_id == student_id
        ).all()
        
        # 수강 이력을 course_id로 매핑
        enrollment_map = {e.course_id: e for e in enrollments}
        
        # 해당 학과의 필수/권장 과목 리스트 가져오기
        department_courses_data = self._get_department_courses(department_id)
        necessary_course_codes = set(department_courses_data.get('necessary_courses', []))
        recommended_course_codes = set(department_courses_data.get('recommended_courses', []))
        
        # 학년별 체계도 과목 리스트 생성
        curriculum_by_year = {1: [], 2: [], 3: [], 4: []}
        for course in dept_courses:
            enrollment = enrollment_map.get(course.id)
            
            # 해당 학과 기준으로 요건 분류 결정
            requirement_type = None
            if course.course_code in necessary_course_codes:
                requirement_type = "전공진입"
            elif course.course_code in recommended_course_codes or course.course_name in recommended_course_codes:
                requirement_type = "권장과목"
            
            course_detail = {
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credits": course.credits,
                "course_type": course.course_type,
                "requirement_type": requirement_type,  # 해당 학과의 요건 분류
                "semester": course.semester,
                "year": course.course_year,
                "enrolled": enrollment is not None,
                "grade": enrollment.grade if enrollment else None,
                "enrollment_year": enrollment.year if enrollment else None,
                "enrollment_semester": enrollment.semester if enrollment else None
            }
            curriculum_by_year[course.course_year].append(course_detail)
        
        # 빈 학년은 제거
        return {year: courses for year, courses in curriculum_by_year.items() if courses}
    
    def _build_analysis_json(
        self,
        student: Student,
        department: Department,
        enrollments: List[CourseEnrollment],
        curriculum_completion_score: float,
        related_courses_score: float
    ) -> Dict:
        """
        상세 분석 JSON 생성
        
        Returns:
            분석 데이터 딕셔너리
        """
        # 1학년 전공체계도 과목 조회
        dept_first_year_courses = self.db.query(Course).filter(
            Course.department_id == department.id,
            Course.course_year == FIRST_YEAR
        ).all()
        
        dept_course_ids = {c.id for c in dept_first_year_courses}
        
        # 이수한 1학년 과목
        completed_first_year = []
        for enrollment in enrollments:
            if enrollment.course_id in dept_course_ids and enrollment.grade and enrollment.grade != FAILING_GRADE:
                course = self.db.query(Course).filter(Course.id == enrollment.course_id).first()
                if course:
                    completed_first_year.append({
                        "course_code": course.course_code,
                        "course_name": course.course_name,
                        "grade": enrollment.grade,
                        "credits": course.credits
                    })
        
        # 유사과목 찾기
        related_courses = []
        other_enrollments = [
            e for e in enrollments
            if e.course_id not in dept_course_ids and
            e.grade and e.grade != FAILING_GRADE
        ]
        
        for enrollment in other_enrollments:
            course = self.db.query(Course).filter(Course.id == enrollment.course_id).first()
            if course and self._is_related_course(course, dept_first_year_courses, department.id):
                related_courses.append({
                    "course_code": course.course_code,
                    "course_name": course.course_name,
                    "grade": enrollment.grade,
                    "credits": course.credits,
                    "course_year": course.course_year,
                    "department_match": course.department_id == department.id
                })
        
        return {
            "curriculum_completion": {
                "score": curriculum_completion_score,
                "total_courses": len(dept_first_year_courses),
                "completed_courses": len(completed_first_year),
                "completion_rate": len(completed_first_year) / len(dept_first_year_courses) if dept_first_year_courses else 0,
                "completed_list": completed_first_year,
                "status": "완료" if curriculum_completion_score >= 100 else "진행중"
            },
            "related_courses": {
                "score": related_courses_score,
                "total_related": len(related_courses),
                "related_list": related_courses
            },
            "overall": {
                "score": (
                    curriculum_completion_score * WEIGHT_CURRICULUM_COMPLETION +
                    related_courses_score * WEIGHT_RELATED_COURSES
                ),
                "weights": {
                    "curriculum_completion": WEIGHT_CURRICULUM_COMPLETION,
                    "related_courses": WEIGHT_RELATED_COURSES
                }
            }
        }
    
    @staticmethod
    def get_admission_year_from_student_id(student_id_str: str) -> int:
        """
        학번에서 입학년도 추출
        
        Args:
            student_id_str: 학번 문자열 (예: "20260001")
            
        Returns:
            입학년도 (예: 2026)
        """
        try:
            return int(student_id_str[:4])
        except (ValueError, IndexError):
            return 2026  # 기본값
    
    def batch_evaluate_students(
        self,
        student_ids: List[int],
        department_id: int,
        admission_year: int = 2026
    ) -> List[Dict]:
        """여러 학생을 한 번에 평가"""
        results = []
        
        for student_id in student_ids:
            try:
                result = self.evaluate_student(
                    student_id, department_id, admission_year, save_to_db=True
                )
                results.append(result)
            except Exception as e:
                print(f"학생 {student_id} 평가 실패: {e}")
                continue
        
        return results
