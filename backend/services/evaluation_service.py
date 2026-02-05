"""
전공진입 적합도 평가 서비스

3-메트릭 기반 평가 시스템:
- 진입요건 충족 (진입요건 있으면 %, 없으면 100%)
- 권장과목 이수 (동일과목 비율, 유사과목 인정 비율)
- 교육과정 이수 (1학년 과목 동일 비율, 유사과목 인정 비율)
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Tuple, Set
from datetime import datetime
import json
import os
import glob

from models.models import (
    Student, Department, Course, CourseEnrollment,
    DepartmentEntryRequirement, RequirementCourse,
    StudentRequirementStatus, GradeLevelEnum
)
from constants import (
    GRADE_TO_NUMERIC,
    GRADE_THRESHOLDS,
    MAX_GPA,
    FIRST_YEAR,
    FAILING_GRADE,
    MIN_SATISFACTION_SCORE
)


class EvaluationService:
    """3개 메트릭 기반 평가 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self._necessary_data = None
        self._recommended_data = None
        self._curriculum_data_cache = {}  # 학과별 교육과정 데이터 캐시
    
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
    
    def _load_all_curriculum_data(self) -> Dict[str, List[Dict]]:
        """
        모든 학과 교육과정 JSON 파일 로드 (유사과목 판정용)
        
        Returns:
            {학과명: [과목정보 리스트]} 형태의 딕셔너리
        """
        if self._curriculum_data_cache:
            return self._curriculum_data_cache
        
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        curriculum_files = ['sw.json', 'elec.json', 'arch.json', 'ime.json', 
                           'dataIntelli.json', 'designConverge.json']
        
        for filename in curriculum_files:
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    dept_name = data.get('department', '')
                    curriculum = data.get('curriculum', [])
                    if dept_name:
                        self._curriculum_data_cache[dept_name] = curriculum
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        
        return self._curriculum_data_cache
    
    def _get_all_course_codes_by_name(self) -> Dict[str, Set[str]]:
        """
        모든 교육과정에서 과목명 -> 학수코드 매핑 생성
        (동일 과목명이 여러 학과에서 다른 코드로 존재할 수 있음)
        
        Returns:
            {과목명: {학수코드1, 학수코드2, ...}} 형태의 딕셔너리
        """
        curriculum_data = self._load_all_curriculum_data()
        course_name_to_codes: Dict[str, Set[str]] = {}
        
        for dept_name, courses in curriculum_data.items():
            for course in courses:
                course_name = course.get('course_name', '')
                course_code = course.get('course_code', '')
                if course_name and course_code:
                    if course_name not in course_name_to_codes:
                        course_name_to_codes[course_name] = set()
                    course_name_to_codes[course_name].add(course_code)
        
        # DB의 과목도 추가
        db_courses = self.db.query(Course).all()
        for course in db_courses:
            if course.course_name not in course_name_to_codes:
                course_name_to_codes[course.course_name] = set()
            course_name_to_codes[course.course_name].add(course.course_code)
        
        return course_name_to_codes
    
    def _get_department_courses(self, department_id: int) -> Dict:
        """학과의 필수/권장 과목 정보 조회"""
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            return {"necessary_courses": [], "recommended_courses": []}
        
        dept_name = department.name
        
        # 필수 과목 조회 (진입요건)
        necessary_data = self._load_necessary_courses()
        necessary_courses = []
        for college in necessary_data.get("colleges", []):
            for major in college.get("majors", []):
                if major.get("name") == dept_name:
                    # 전체 과목 정보 추출 (course_code와 course_name 포함)
                    necessary_courses = [
                        {
                            "course_code": course["course_code"],
                            "course_name": course.get("course_name", "")
                        }
                        for course in major.get("necessary_courses", [])
                    ]
                    break
        
        # 권장 과목 조회 (과목명 리스트)
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
    
    def _get_department_first_year_curriculum(self, department_id: int) -> List[Dict]:
        """
        해당 학과의 1학년 교육과정 과목 목록 조회
        
        Returns:
            [{"course_code": "XXX", "course_name": "YYY"}, ...] 형태의 리스트
        """
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            return []
        
        dept_name = department.name
        curriculum_data = self._load_all_curriculum_data()
        
        # 해당 학과의 교육과정에서 1학년 과목 추출
        dept_curriculum = curriculum_data.get(dept_name, [])
        first_year_courses = [
            {
                "course_code": course.get("course_code", ""),
                "course_name": course.get("course_name", "")
            }
            for course in dept_curriculum
            if course.get("course_year") == 1
        ]
        
        # 교육과정 JSON에 없으면 DB에서 조회
        if not first_year_courses:
            db_courses = self.db.query(Course).filter(
                Course.department_id == department_id,
                Course.course_year == FIRST_YEAR
            ).all()
            first_year_courses = [
                {
                    "course_code": c.course_code,
                    "course_name": c.course_name
                }
                for c in db_courses
            ]
        
        return first_year_courses
    
    def evaluate_student(
        self,
        student_id: int,
        department_id: int,
        admission_year: int = 2026,
        save_to_db: bool = True
    ) -> Dict:
        """
        학생의 학과 적합도를 3개 메트릭으로 평가
        
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
        
        # 학생이 이수한 과목 정보 수집 (과목코드, 과목명)
        student_completed_courses = self._get_student_completed_courses(enrollments)
        
        # 1. 진입요건 충족 점수
        entry_requirement_score = self._calculate_entry_requirement_score(
            student_completed_courses, department_id
        )
        
        # 2. 권장과목 이수 점수 (동일과목 비율, 유사과목 인정 비율)
        recommended_exact_rate, recommended_similar_rate = self._calculate_recommended_courses_score(
            student_completed_courses, department_id
        )
        
        # 3. 교육과정 이수 점수 (1학년 과목 동일 비율, 유사과목 인정 비율)
        curriculum_exact_rate, curriculum_similar_rate = self._calculate_curriculum_completion_score(
            student_completed_courses, department_id
        )
        
        # 4. 종합 점수 계산 (진입요건 40% + 권장과목유사 30% + 교육과정유사 30%)
        overall_score = (
            entry_requirement_score * 0.4 +
            recommended_similar_rate * 0.3 +
            curriculum_similar_rate * 0.3
        )
        
        # 5. 상세 분석 JSON 생성
        analysis_json = self._build_analysis_json(
            student, department, enrollments, student_completed_courses,
            entry_requirement_score,
            recommended_exact_rate, recommended_similar_rate,
            curriculum_exact_rate, curriculum_similar_rate
        )
        
        # 6. 등급 판정
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
            # 진입요건 충족
            'entry_requirement_score': round(entry_requirement_score, 2),
            # 권장과목 이수
            'recommended_exact_rate': round(recommended_exact_rate, 2),
            'recommended_similar_rate': round(recommended_similar_rate, 2),
            # 교육과정 이수
            'curriculum_exact_rate': round(curriculum_exact_rate, 2),
            'curriculum_similar_rate': round(curriculum_similar_rate, 2),
            # 종합
            'overall_score': round(overall_score, 2),
            'grade': grade,
            'analysis_json': analysis_json,
            'evaluated_at': datetime.utcnow()
        }
        
        # DB에 저장
        if save_to_db:
            self._save_evaluation_result(student_id, department_id, admission_year, result)
        
        return result
    
    def _get_student_completed_courses(self, enrollments: List[CourseEnrollment]) -> Dict:
        """
        학생이 이수한 과목 정보 수집
        
        Returns:
            {
                "codes": {학수코드 set},
                "names": {과목명 set},
                "details": [{course_code, course_name, grade}, ...]
            }
        """
        completed_codes = set()
        completed_names = set()
        completed_details = []
        
        for enrollment in enrollments:
            if enrollment.grade and enrollment.grade != FAILING_GRADE:
                course = self.db.query(Course).filter(Course.id == enrollment.course_id).first()
                if course:
                    completed_codes.add(course.course_code)
                    completed_names.add(course.course_name)
                    completed_details.append({
                        "course_code": course.course_code,
                        "course_name": course.course_name,
                        "grade": enrollment.grade,
                        "credits": course.credits
                    })
        
        return {
            "codes": completed_codes,
            "names": completed_names,
            "details": completed_details
        }
    
    def _calculate_entry_requirement_score(
        self,
        student_completed_courses: Dict,
        department_id: int
    ) -> float:
        """
        진입요건 충족 점수
        
        - 진입요건이 있으면: 이수한 필수과목 비율 (%)
        - 진입요건이 없으면: 100%
        """
        dept_courses = self._get_department_courses(department_id)
        necessary_courses = dept_courses.get("necessary_courses", [])
        
        # 진입요건이 없으면 100%
        if not necessary_courses:
            return 100.0
        
        completed_codes = student_completed_courses["codes"]
        completed_names = student_completed_courses["names"]
        
        # 이수한 필수과목 수 계산
        completed_count = 0
        for necessary in necessary_courses:
            course_code = necessary.get("course_code", "")
            course_name = necessary.get("course_name", "")
            
            # 학수코드 또는 과목명이 일치하면 이수로 인정
            if course_code in completed_codes or course_name in completed_names:
                completed_count += 1
        
        # 비율 계산
        score = (completed_count / len(necessary_courses)) * 100
        return round(min(100.0, score), 2)
    
    def _calculate_recommended_courses_score(
        self,
        student_completed_courses: Dict,
        department_id: int
    ) -> Tuple[float, float]:
        """
        권장과목 이수 점수 계산
        
        Returns:
            (동일과목 비율, 유사과목 인정 비율) 튜플
            - 동일과목: 정확히 같은 학수코드+과목명
            - 유사과목: 과목명이 같으면 다른 학과 과목도 인정
        """
        dept_courses = self._get_department_courses(department_id)
        recommended_course_names = dept_courses.get("recommended_courses", [])  # 과목명 리스트
        
        if not recommended_course_names:
            return 100.0, 100.0  # 권장과목이 없으면 100%
        
        completed_codes = student_completed_courses["codes"]
        completed_names = student_completed_courses["names"]
        
        # 교과목 DB에서 권장과목명에 해당하는 학수코드 찾기
        course_name_to_codes = self._get_all_course_codes_by_name()
        
        # 동일과목 카운트 (해당 학과의 설강 과목만)
        exact_match_count = 0
        # 유사과목 카운트 (과목명이 같으면 다른 학과도 인정)
        similar_match_count = 0
        
        for rec_name in recommended_course_names:
            # 유사과목 체크: 과목명이 동일한 과목을 이수했는지
            if rec_name in completed_names:
                similar_match_count += 1
                
                # 동일과목 체크: 해당 과목명에 대응하는 학수코드를 이수했는지
                expected_codes = course_name_to_codes.get(rec_name, set())
                if expected_codes & completed_codes:  # 교집합이 있으면
                    exact_match_count += 1
        
        total = len(recommended_course_names)
        exact_rate = (exact_match_count / total) * 100
        similar_rate = (similar_match_count / total) * 100
        
        return round(exact_rate, 2), round(similar_rate, 2)
    
    def _calculate_curriculum_completion_score(
        self,
        student_completed_courses: Dict,
        department_id: int
    ) -> Tuple[float, float]:
        """
        교육과정 이수 점수 (1학년 과목)
        
        Returns:
            (동일과목 비율, 유사과목 인정 비율) 튜플
            - 동일과목: 정확히 같은 설강학과+학수코드
            - 유사과목: 과목명이 같으면 다른 학과 과목도 인정
        """
        # 해당 학과의 1학년 교육과정 과목
        first_year_courses = self._get_department_first_year_curriculum(department_id)
        
        if not first_year_courses:
            return 100.0, 100.0  # 1학년 과목이 없으면 100%
        
        completed_codes = student_completed_courses["codes"]
        completed_names = student_completed_courses["names"]
        
        # 동일과목 카운트 (학수코드 일치)
        exact_match_count = 0
        # 유사과목 카운트 (과목명 일치)
        similar_match_count = 0
        
        for course in first_year_courses:
            course_code = course.get("course_code", "")
            course_name = course.get("course_name", "")
            
            # 동일과목: 학수코드가 일치
            if course_code in completed_codes:
                exact_match_count += 1
            
            # 유사과목: 과목명이 일치
            if course_name in completed_names:
                similar_match_count += 1
        
        total = len(first_year_courses)
        exact_rate = (exact_match_count / total) * 100
        similar_rate = (similar_match_count / total) * 100
        
        return round(exact_rate, 2), round(similar_rate, 2)
    
    def _find_similar_courses(
        self,
        target_course_name: str,
        student_completed_courses: Dict
    ) -> bool:
        """
        학생이 이수한 과목 중 타겟 과목과 유사한 과목이 있는지 확인
        (과목명 기준 유사도 판단)
        """
        return target_course_name in student_completed_courses["names"]
    
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
        
        # 점수 업데이트 (새로운 3-메트릭 체계)
        # 기존 필드에 매핑 (curriculum_completion_score -> curriculum_similar_rate로 사용)
        status.curriculum_completion_score = result.get('curriculum_similar_rate', 0)
        status.related_courses_score = result.get('recommended_similar_rate', 0)
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
        # 해당 학과의 전체 과목 조회 (1~4학년)
        # 1. 해당 학과 소속 과목 (전공기초 포함) OR
        # 2. 교양필수 과목 (다른 학과 소속이어도 포함)
        dept_courses = self.db.query(Course).filter(
            Course.course_year.in_([1, 2, 3, 4]),
            or_(
                Course.department_id == department_id,
                Course.course_type == '교양필수'
            )
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
        # necessary_courses는 이제 [{course_code, course_name}, ...] 형태
        necessary_course_codes = set(
            c.get("course_code", "") for c in department_courses_data.get('necessary_courses', [])
        )
        # recommended_courses는 과목명 리스트
        recommended_course_names = set(department_courses_data.get('recommended_courses', []))
        
        # 학년별 체계도 과목 리스트 생성
        curriculum_by_year = {1: [], 2: [], 3: [], 4: []}
        for course in dept_courses:
            enrollment = enrollment_map.get(course.id)
            
            # 해당 학과 기준으로 요건 분류 결정
            requirement_type = None
            if course.course_code in necessary_course_codes:
                requirement_type = "전공진입"
            elif course.course_name in recommended_course_names:
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
        student_completed_courses: Dict,
        entry_requirement_score: float,
        recommended_exact_rate: float,
        recommended_similar_rate: float,
        curriculum_exact_rate: float,
        curriculum_similar_rate: float
    ) -> Dict:
        """
        상세 분석 JSON 생성 (3-메트릭 체계)
        
        Returns:
            분석 데이터 딕셔너리
        """
        # 학과 관련 과목 정보 조회
        dept_courses_data = self._get_department_courses(department.id)
        necessary_courses = dept_courses_data.get("necessary_courses", [])
        recommended_course_names = dept_courses_data.get("recommended_courses", [])
        
        # 1학년 교육과정 과목
        first_year_courses = self._get_department_first_year_curriculum(department.id)
        
        completed_codes = student_completed_courses["codes"]
        completed_names = student_completed_courses["names"]
        completed_details = student_completed_courses["details"]
        
        # 1. 진입요건 상세
        entry_requirement_details = []
        for necessary in necessary_courses:
            course_code = necessary.get("course_code", "")
            course_name = necessary.get("course_name", "")
            is_completed = course_code in completed_codes or course_name in completed_names
            
            # 어떤 과목으로 이수했는지 찾기
            matched_course = None
            for detail in completed_details:
                if detail["course_code"] == course_code or detail["course_name"] == course_name:
                    matched_course = detail
                    break
            
            entry_requirement_details.append({
                "course_code": course_code,
                "course_name": course_name,
                "is_completed": is_completed,
                "matched_course": matched_course
            })
        
        # 2. 권장과목 상세
        recommended_details = []
        course_name_to_codes = self._get_all_course_codes_by_name()
        
        for rec_name in recommended_course_names:
            is_exact_match = False
            is_similar_match = rec_name in completed_names
            matched_course = None
            
            if is_similar_match:
                # 정확히 어떤 과목으로 이수했는지 찾기
                for detail in completed_details:
                    if detail["course_name"] == rec_name:
                        matched_course = detail
                        # 해당 과목명의 원래 학수코드와 일치하면 exact match
                        expected_codes = course_name_to_codes.get(rec_name, set())
                        if detail["course_code"] in expected_codes:
                            is_exact_match = True
                        break
            
            recommended_details.append({
                "course_name": rec_name,
                "is_exact_match": is_exact_match,
                "is_similar_match": is_similar_match,
                "matched_course": matched_course
            })
        
        # 3. 교육과정(1학년) 상세
        curriculum_details = []
        for course in first_year_courses:
            course_code = course.get("course_code", "")
            course_name = course.get("course_name", "")
            
            is_exact_match = course_code in completed_codes
            is_similar_match = course_name in completed_names
            matched_course = None
            
            if is_exact_match or is_similar_match:
                for detail in completed_details:
                    if detail["course_code"] == course_code or detail["course_name"] == course_name:
                        matched_course = detail
                        break
            
            curriculum_details.append({
                "course_code": course_code,
                "course_name": course_name,
                "is_exact_match": is_exact_match,
                "is_similar_match": is_similar_match,
                "matched_course": matched_course
            })
        
        # 종합 점수 계산
        overall_score = (
            entry_requirement_score * 0.4 +
            recommended_similar_rate * 0.3 +
            curriculum_similar_rate * 0.3
        )
        
        return {
            "entry_requirement": {
                "score": entry_requirement_score,
                "total_courses": len(necessary_courses),
                "completed_courses": sum(1 for d in entry_requirement_details if d["is_completed"]),
                "has_requirement": len(necessary_courses) > 0,
                "details": entry_requirement_details,
                "status": "충족" if entry_requirement_score >= 100 else "미충족"
            },
            "recommended_courses": {
                "exact_rate": recommended_exact_rate,
                "similar_rate": recommended_similar_rate,
                "total_courses": len(recommended_course_names),
                "exact_completed": sum(1 for d in recommended_details if d["is_exact_match"]),
                "similar_completed": sum(1 for d in recommended_details if d["is_similar_match"]),
                "details": recommended_details,
                "status": "완료" if recommended_similar_rate >= 100 else "진행중"
            },
            "curriculum_completion": {
                "exact_rate": curriculum_exact_rate,
                "similar_rate": curriculum_similar_rate,
                "total_courses": len(first_year_courses),
                "exact_completed": sum(1 for d in curriculum_details if d["is_exact_match"]),
                "similar_completed": sum(1 for d in curriculum_details if d["is_similar_match"]),
                "details": curriculum_details,
                "status": "완료" if curriculum_similar_rate >= 100 else "진행중"
            },
            "overall": {
                "score": overall_score,
                "weights": {
                    "entry_requirement": 0.4,
                    "recommended_courses": 0.3,
                    "curriculum_completion": 0.3
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
