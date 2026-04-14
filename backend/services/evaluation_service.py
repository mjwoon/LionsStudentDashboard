"""
전공진입 적합도 평가 서비스

3-메트릭 기반 평가 시스템:
- 진입요건 충족 (진입요건 있으면 %, 없으면 100%)
- 권장과목 이수 (동일과목 비율, 유사과목 인정 비율)
- 교육과정 이수 (1학년 과목 동일 비율, 유사과목 인정 비율)
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from models.models import (
    Student, Department, Course, StudentCourse,
    DepartmentEntryRequirement, RequirementCourse,
    StudentRequirementStatus, GradeLevelEnum,
    Curriculum, CourseRecommendation
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
        self._similarity_cache = {}       # Neo4j 유사도 캐시 {(code1, code2): float}
        self._similarity_threshold = 0.7  # 유사과목 인정 최소 유사도
        self._graph_available = None      # Neo4j 연결 상태 캐시 (None=미확인)
    
    def _load_all_curriculum_data(self) -> Dict[str, List[Dict]]:
        """모든 학과 교육과정 DB 로드 (유사과목 판정용)"""
        if self._curriculum_data_cache:
            return self._curriculum_data_cache
        
        curriculums = self.db.query(Curriculum).all()
        for cur in curriculums:
            dept = self.db.query(Department).filter(Department.id == cur.department_id).first()
            if dept:
                if dept.name not in self._curriculum_data_cache:
                    self._curriculum_data_cache[dept.name] = []
                self._curriculum_data_cache[dept.name].append({
                    "course_code": cur.course_code,
                    "course_name": cur.course_name,
                    "course_year": cur.course_year
                })
        
        return self._curriculum_data_cache
    
    def _get_all_course_codes_by_name(self) -> Dict[str, Set[str]]:
        """모든 교육과정에서 과목명 -> 학수코드 매핑 생성"""
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
        """학과의 필수/권장 과목 정보 DB에서 조회"""
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            return {"necessary_courses": [], "recommended_courses": []}
        
        # 필수 과목 조회 (RequirementCourse 활용)
        # 만약 RequirementCourse 테이블이 비어있다면, Curriculum에서 전공필수(필요시)만 가져오거나 
        # 임시로 빈 리스트 처리
        req_courses = self.db.query(RequirementCourse).join(DepartmentEntryRequirement).filter(
            DepartmentEntryRequirement.department_id == department_id
        ).all()
        
        necessary_courses = []
        for r in req_courses:
            course = self.db.query(Course).filter(Course.course_code == r.course_code).first()
            if course:
                necessary_courses.append({
                    "course_code": course.course_code,
                    "course_name": course.course_name
                })
        
        # 만약 RequirementCourse를 사용하지 않는 경우에는 빈 배열 반환 (요건 충족 검사에서 100% 처리)
        
        # 권장 과목 조회
        recs = self.db.query(CourseRecommendation).filter(CourseRecommendation.department_id == department_id).all()
        recommended_courses = [r.course_name for r in recs]
        
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
                Course.course_department == dept_name,
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
        student = self.db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise ValueError(f"학생 ID {student_id}를 찾을 수 없습니다.")
        
        # 학과 정보 조회
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ValueError(f"학과 ID {department_id}를 찾을 수 없습니다.")
        
        # 학생의 수강 이력 조회
        enrollments = self.db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.grade.isnot(None),
            StudentCourse.grade != ""
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
        dept_courses_data = self._get_department_courses(department.id)
        necessary_courses = dept_courses_data.get("necessary_courses", [])
        recommended_course_names = dept_courses_data.get("recommended_courses", [])
        first_year_courses = self._get_department_first_year_curriculum(department.id)
        course_name_to_codes = self._get_all_course_codes_by_name()
        
        from services.evaluation_presenter import EvaluationResponseBuilder
        analysis_json = EvaluationResponseBuilder.build_analysis_json(
            student=student,
            department=department,
            enrollments=enrollments,
            student_completed_courses=student_completed_courses,
            entry_requirement_score=entry_requirement_score,
            recommended_exact_rate=recommended_exact_rate,
            recommended_similar_rate=recommended_similar_rate,
            curriculum_exact_rate=curriculum_exact_rate,
            curriculum_similar_rate=curriculum_similar_rate,
            necessary_courses=necessary_courses,
            recommended_course_names=recommended_course_names,
            first_year_courses=first_year_courses,
            course_name_to_codes=course_name_to_codes,
            is_graph_available=self._is_graph_available(),
            find_best_similar_course_func=self._find_best_similar_course
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
            'ai_summary': None,
            'evaluated_at': datetime.utcnow()
        }
        
        # AI 총평은 AI Worker (Celery)가 별도로 처리
        
        # DB에 저장
        if save_to_db:
            self._save_evaluation_result(student_id, department_id, admission_year, result)
        
        return result
    
    def _get_student_completed_courses(self, enrollments: List[StudentCourse]) -> Dict:
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
                course = self.db.query(Course).filter(Course.course_code == enrollment.course_code).first()
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
        department_id: str
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
        department_id: str
    ) -> Tuple[float, float]:
        """
        권장과목 이수 점수 계산
        
        Returns:
            (동일과목 비율, 유사과목 인정 비율) 튜플
            - 동일과목: 정확히 같은 학수코드+과목명
            - 유사과목: Neo4j 유사도 >= threshold이면 인정 (폴백: 과목명 일치)
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
        # 유사과목 카운트 (Neo4j 유사도 또는 과목명 일치)
        similar_match_count = 0
        
        for rec_name in recommended_course_names:
            # 동일과목 체크: 과목명이 동일한 과목을 이수 + 학수코드도 일치
            if rec_name in completed_names:
                expected_codes = course_name_to_codes.get(rec_name, set())
                if expected_codes & completed_codes:
                    exact_match_count += 1
            
            # 유사과목 체크: Neo4j 유사도 기반 또는 과목명 폴백
            target_codes = course_name_to_codes.get(rec_name, set())
            is_similar, _, _ = self._find_best_similar_course(
                target_codes, rec_name, student_completed_courses
            )
            if is_similar:
                similar_match_count += 1
        
        total = len(recommended_course_names)
        exact_rate = (exact_match_count / total) * 100
        similar_rate = (similar_match_count / total) * 100
        
        return round(exact_rate, 2), round(similar_rate, 2)
    
    def _calculate_curriculum_completion_score(
        self,
        student_completed_courses: Dict,
        department_id: str
    ) -> Tuple[float, float]:
        """
        교육과정 이수 점수 (1학년 과목)
        
        Returns:
            (동일과목 비율, 유사과목 인정 비율) 튜플
            - 동일과목: 정확히 같은 설강학과+학수코드
            - 유사과목: Neo4j 유사도 >= threshold이면 인정 (폴백: 과목명 일치)
        """
        # 해당 학과의 1학년 교육과정 과목
        first_year_courses = self._get_department_first_year_curriculum(department_id)
        
        if not first_year_courses:
            return 100.0, 100.0  # 1학년 과목이 없으면 100%
        
        completed_codes = student_completed_courses["codes"]
        
        # 동일과목 카운트 (학수코드 일치)
        exact_match_count = 0
        # 유사과목 카운트 (Neo4j 유사도 또는 과목명 일치)
        similar_match_count = 0
        
        for course in first_year_courses:
            course_code = course.get("course_code", "")
            course_name = course.get("course_name", "")
            
            # 동일과목: 학수코드가 일치
            if course_code in completed_codes:
                exact_match_count += 1
            
            # 유사과목: Neo4j 유사도 기반 또는 과목명 폴백
            target_codes = {course_code} if course_code else set()
            is_similar, _, _ = self._find_best_similar_course(
                target_codes, course_name, student_completed_courses
            )
            if is_similar:
                similar_match_count += 1
        
        total = len(first_year_courses)
        exact_rate = (exact_match_count / total) * 100
        similar_rate = (similar_match_count / total) * 100
        
        return round(exact_rate, 2), round(similar_rate, 2)
    
    # ==================== Neo4j 유사도 통합 ====================
    
    def _is_graph_available(self) -> bool:
        """
        Neo4j 연결 가능 여부 확인 (인스턴스 내 1회 캐싱)
        """
        if self._graph_available is None:
            try:
                from services.graph_service import CourseGraphService
                self._graph_available = CourseGraphService.check_connection()
            except Exception:
                self._graph_available = False
            if not self._graph_available:
                logger.info("Neo4j 미연결 - 과목명 기반 폴백 모드로 동작")
        return self._graph_available
    
    def _get_similarity_from_graph(
        self,
        source_course_code: str,
        target_course_code: str
    ) -> float:
        """
        Neo4j에서 두 과목 간 유사도 조회 (캐싱 적용)
        
        Returns:
            유사도 (0.0 ~ 1.0), 관계 없거나 연결 실패 시 0.0
        """
        if not self._is_graph_available():
            return 0.0
        
        # 캐시 확인 (순서 무관하게 동일 키)
        cache_key = tuple(sorted([source_course_code, target_course_code]))
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # Neo4j 조회
        try:
            from services.graph_service import CourseGraphService
            similarity = CourseGraphService.get_similarity_between(
                source_course_code, target_course_code
            )
        except Exception as e:
            logger.warning(f"Neo4j 유사도 조회 실패 ({source_course_code} <-> {target_course_code}): {e}")
            similarity = 0.0
        
        self._similarity_cache[cache_key] = similarity
        return similarity
    
    def _find_best_similar_course(
        self,
        target_course_codes: Set[str],
        target_course_name: str,
        student_completed_courses: Dict
    ) -> Tuple[bool, float, Optional[Dict]]:
        """
        학생이 이수한 과목 중 타겟 과목과 가장 유사한 과목 찾기
        
        로직:
        1. 동일 학수코드 → 유사도 1.0
        2. Neo4j SIMILAR_TO 관계 조회 → threshold 이상이면 인정
        3. 폴백: 과목명 일치 → 유사도 1.0으로 인정
        
        Args:
            target_course_codes: 타겟 과목 학수코드 set (과목명으로 여러 코드 가능)
            target_course_name: 타겟 과목명
            student_completed_courses: 학생 이수 과목 정보
            
        Returns:
            (인정여부, 최고유사도, 매칭된 과목 dict or None)
        """
        completed_codes = student_completed_courses["codes"]
        completed_names = student_completed_courses["names"]
        completed_details = student_completed_courses["details"]
        
        # 1. 동일 학수코드 체크
        for target_code in target_course_codes:
            if target_code in completed_codes:
                for detail in completed_details:
                    if detail["course_code"] == target_code:
                        return (True, 1.0, detail)
        
        # 2. Neo4j 유사도 기반 매칭
        if self._is_graph_available():
            best_similarity = 0.0
            best_match = None
            
            for detail in completed_details:
                for target_code in target_course_codes:
                    sim = self._get_similarity_from_graph(
                        detail["course_code"],
                        target_code
                    )
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match = detail
            
            if best_similarity >= self._similarity_threshold:
                return (True, best_similarity, best_match)
            
            # Neo4j에서 유사 관계를 못 찾았더라도 과목명 폴백은 하지 않음
            # (Neo4j가 연결되어 있으면 그래프 결과를 신뢰)
            if best_similarity > 0:
                return (False, best_similarity, None)
        
        # 3. 폴백: 과목명 일치 (Neo4j 미연결 시)
        if target_course_name in completed_names:
            for detail in completed_details:
                if detail["course_name"] == target_course_name:
                    return (True, 1.0, detail)
        
        return (False, 0.0, None)
    
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
        설강학과의 과목만 포함 (중복 제거)
        
        Args:
            student_id: 학생 ID
            department_id: 학과 ID
            
        Returns:
            학년별 체계도 과목 딕셔너리 {1: [...], 2: [...], 3: [...], 4: [...]}
        """
        # 학과명 조회
        department = self.db.query(Department).filter(Department.id == department_id).first()
        if not department:
            return {}
        
        # 해당 학과의 교육과정 JSON에서 과목 코드 목록 가져오기
        curriculum_data = self._load_all_curriculum_data()
        dept_curriculum = curriculum_data.get(department.name, [])
        curriculum_course_codes = set(
            c.get("course_code", "") for c in dept_curriculum if c.get("course_code")
        )
        
        # 해당 학과 소속 과목만 조회 (설강학과 기준)
        dept_courses = self.db.query(Course).filter(
            Course.course_department == department.name,
            Course.course_year.in_([1, 2, 3, 4])
        ).order_by(Course.course_year, Course.semester, Course.course_code).all()
        
        # 교육과정 JSON에 있는 교양필수/전공기초 과목 중 다른 학과 소속인 것도 포함
        # (단, 설강학과 소속이 아닌 과목만 추가)
        existing_codes = set(c.course_code for c in dept_courses)
        extra_codes = curriculum_course_codes - existing_codes
        
        if extra_codes:
            # 교육과정에 명시된 과목 중 다른 학과 소속인 과목 조회
            # course_code 기준으로 중복 없이 하나만 가져오기
            extra_courses_raw = self.db.query(Course).filter(
                Course.course_code.in_(extra_codes),
                Course.course_year.in_([1, 2, 3, 4])
            ).order_by(Course.course_year, Course.semester, Course.course_code).all()
            
            # course_code 기준 중복 제거 (첫 번째만 사용)
            seen_codes = set()
            for c in extra_courses_raw:
                if c.course_code not in seen_codes:
                    dept_courses.append(c)
                    seen_codes.add(c.course_code)
        
        if not dept_courses:
            return {}
        
        # 학생의 수강 이력 조회
        enrollments = self.db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id
        ).all()
        
        # 수강 이력을 course_code로 매핑
        enrollment_map = {e.course_code: e for e in enrollments}
        
        # 해당 학과의 필수/권장 과목 리스트 가져오기
        department_courses_data = self._get_department_courses(department_id)
        necessary_course_codes = set(
            c.get("course_code", "") for c in department_courses_data.get('necessary_courses', [])
        )
        recommended_course_names = set(department_courses_data.get('recommended_courses', []))
        
        # 학년별 체계도 과목 리스트 생성 (course_code 기준 중복 제거)
        curriculum_by_year = {1: [], 2: [], 3: [], 4: []}
        seen_course_codes = set()
        
        # 정렬: 학년 → 학기 → 코드 순
        dept_courses.sort(key=lambda c: (c.course_year or 0, c.semester or 0, c.course_code or ""))
        
        for course in dept_courses:
            if course.course_code in seen_course_codes:
                continue
            seen_course_codes.add(course.course_code)
            
            enrollment = enrollment_map.get(course.course_code)
            enrolled_dept_name = None
            
            if enrollment:
                # 타학과 이수인 경우 학과명 기록
                # course_department는 학과명(string)이므로 department.name과 비교
                if course.course_department and course.course_department != department.name:
                    enrolled_dept_name = course.course_department
            
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
                "requirement_type": requirement_type,
                "semester": course.semester,
                "year": course.course_year,
                "enrolled": enrollment is not None,
                "grade": enrollment.grade if enrollment else None,
                "enrollment_year": enrollment.year if enrollment else None,
                "enrollment_semester": enrollment.semester if enrollment else None,
                "enrolled_department_name": enrolled_dept_name,
            }
            curriculum_by_year[course.course_year].append(course_detail)
        
        return {year: courses for year, courses in curriculum_by_year.items() if courses}
    

    
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
        student_ids: List[str],
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
