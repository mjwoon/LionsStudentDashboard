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
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

from lions_core.models import (
    Student, Department, Course, StudentCourse,
    DepartmentEntryRequirement, RequirementCourse,
    StudentRequirementStatus, GradeLevelEnum,
    Curriculum, CourseRecommendation
)
from lions_core.repositories import (
    EvaluationCacheRepository,
    StudentRepository,
    DepartmentRepository,
)
from lions_core.evaluation_presenter import EvaluationResponseBuilder
from lions_core import scoring
from lions_core.constants import (
    classify_grade,
    FIRST_YEAR,
    FAILING_GRADE,
    EVALUATION_WEIGHTS,
    SIMILARITY_THRESHOLD,
)


class EvaluationService:
    """3개 메트릭 기반 평가 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        # 반복되는 엔티티 단건 조회는 기존 리포지토리로 일원화(자기 리포지토리 무시 해소).
        self._students = StudentRepository(db)
        self._departments = DepartmentRepository(db)
        self._curriculum_data_cache = {}  # 학과별 교육과정 데이터 캐시
        self._similarity_cache = {}       # Neo4j 유사도 캐시 {(code1, code2): float}
        self._similarity_threshold = SIMILARITY_THRESHOLD  # 유사과목 인정 최소 유사도(SSOT)
        # 주의: _graph_available은 제거됨.
        #   연결 상태는 graph_service.is_graph_available()의
        #   30초 TTL 모듈 레벨 캐시를 사용합니다.
    
    def _load_all_curriculum_data(self) -> Dict[str, List[Dict]]:
        """모든 학과 교육과정 DB 로드 (유사과목 판정용)"""
        if self._curriculum_data_cache:
            return self._curriculum_data_cache
        
        curriculums = self.db.query(Curriculum).all()
        for cur in curriculums:
            dept = self._departments.get(cur.department_id)
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
    
    def _get_department_courses(self, department_id: int, admission_year: Optional[int] = None) -> Dict:
        """학과의 필수/권장 과목 정보 DB에서 조회.

        admission_year가 주어지면 해당 입학년도의 진입요건만 조회한다(연도별 룰셋 분리).
        None이면 학과의 모든 연도 요건을 합산한다(레거시 호환 경로).
        """
        department = self._departments.get(department_id)
        if not department:
            return {"necessary_courses": [], "recommended_courses": []}

        # 필수 과목 조회 (RequirementCourse 활용). admission_year가 있으면 입학년도로 필터.
        req_query = self.db.query(RequirementCourse).join(DepartmentEntryRequirement).filter(
            DepartmentEntryRequirement.department_id == department_id
        )
        if admission_year is not None:
            req_query = req_query.filter(
                DepartmentEntryRequirement.admission_year == admission_year
            )
        req_courses = req_query.all()
        
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
        department = self._departments.get(department_id)
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
        student = self._students.get(student_id)
        if not student:
            raise ValueError(f"학생 ID {student_id}를 찾을 수 없습니다.")
        
        # 학과 정보 조회
        department = self._departments.get(department_id)
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
        
        # 1. 진입요건 충족 점수 (학생 입학년도 기준)
        entry_requirement_score = self._calculate_entry_requirement_score(
            student_completed_courses, department_id, admission_year
        )
        
        # 2. 권장과목 이수 점수 (동일과목 비율, 유사과목 인정 비율)
        recommended_exact_rate, recommended_similar_rate = self._calculate_recommended_courses_score(
            student_completed_courses, department_id
        )
        
        # 3. 교육과정 이수 점수 (1학년 과목 동일 비율, 유사과목 인정 비율)
        curriculum_exact_rate, curriculum_similar_rate = self._calculate_curriculum_completion_score(
            student_completed_courses, department_id
        )
        
        # 4. 종합 점수 계산 (가중치 SSOT: constants.EVALUATION_WEIGHTS)
        overall_score = (
            entry_requirement_score * EVALUATION_WEIGHTS["entry_requirement"] +
            recommended_similar_rate * EVALUATION_WEIGHTS["recommended_courses"] +
            curriculum_similar_rate * EVALUATION_WEIGHTS["curriculum_completion"]
        )
        
        # 5. 상세 분석 JSON 생성
        dept_courses_data = self._get_department_courses(department.id, admission_year)
        necessary_courses = dept_courses_data.get("necessary_courses", [])
        recommended_course_names = dept_courses_data.get("recommended_courses", [])
        first_year_courses = self._get_department_first_year_curriculum(department.id)
        course_name_to_codes = self._get_all_course_codes_by_name()
        
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
        grade = classify_grade(overall_score)
        
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
            'evaluated_at': datetime.now(timezone.utc)
        }
        
        # AI 총평은 AI Worker (Celery)가 별도로 처리
        
        # DB에 저장
        if save_to_db:
            self._save_evaluation_result(student_id, department_id, admission_year, result)
        
        return result
    
    def _get_student_completed_courses(self, enrollments: List[StudentCourse]) -> Dict:
        """
        학생이 이수한 과목 정보 수집

        N+1 쿼리 방지: 유효 수강 이력의 과목코드를 한 번에 IN 절로 조회합니다.

        Returns:
            {
                "codes": {학수코드 set},
                "names": {과목명 set},
                "details": [{course_code, course_name, grade, credits}, ...]
            }
        """
        completed_codes = set()
        completed_names = set()
        completed_details = []

        # F학점/미수강 제외: 유효한 수강 이력만 필터링
        valid_enrollments = [
            e for e in enrollments
            if e.grade and e.grade != FAILING_GRADE
        ]
        if not valid_enrollments:
            return {"codes": completed_codes, "names": completed_names, "details": completed_details}

        # 과목 정보 일괄 조회 (IN 절, 쿼리 1회)
        enrollment_codes = [e.course_code for e in valid_enrollments]
        courses = self.db.query(Course).filter(
            Course.course_code.in_(enrollment_codes)
        ).all()
        course_map = {c.course_code: c for c in courses}

        # grade 역참조 맵
        grade_map = {e.course_code: e.grade for e in valid_enrollments}

        for code, course in course_map.items():
            completed_codes.add(course.course_code)
            completed_names.add(course.course_name)
            completed_details.append({
                "course_code": course.course_code,
                "course_name": course.course_name,
                "grade": grade_map.get(code, ""),
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
        department_id: str,
        admission_year: Optional[int] = None
    ) -> float:
        """
        진입요건 충족 점수 (admission_year가 있으면 해당 입학년도 요건만 기준)

        - 진입요건이 있으면: 이수한 필수과목 비율 (%)
        - 진입요건이 없으면: 100%
        """
        dept_courses = self._get_department_courses(department_id, admission_year)
        necessary_courses = dept_courses.get("necessary_courses", [])
        return scoring.entry_requirement_score(necessary_courses, student_completed_courses)
    
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

        # 권장과목이 없으면 비싼 과목-코드 매핑 조회를 건너뛴다(동작·성능 보존).
        if not recommended_course_names:
            return 100.0, 100.0

        course_name_to_codes = self._get_all_course_codes_by_name()
        return scoring.recommended_courses_score(
            recommended_course_names,
            student_completed_courses,
            course_name_to_codes,
            self._find_best_similar_course,
        )
    
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
        first_year_courses = self._get_department_first_year_curriculum(department_id)
        return scoring.curriculum_completion_score(
            first_year_courses,
            student_completed_courses,
            self._find_best_similar_course,
        )
    
    # ==================== Neo4j 유사도 통합 ====================

    def _is_graph_available(self) -> bool:
        """
        Neo4j 연결 가능 여부 확인

        graph_service 모듈의 30초 TTL 캐시(is_graph_available)를 사용합니다.
        인스턴스 레벨 캐싱 제거 → 요청 간 공유, Neo4j 복구 시 TTL 내 자동 정상화.
        """
        from lions_core.graph_connection import is_graph_available
        available = is_graph_available()
        if not available:
            logger.debug("Neo4j 미연결 - 과목명 기반 폴백 모듈로 동작")
        return available
    
    def _get_similarity_from_graph(
        self,
        source_course_code: str,
        target_course_code: str
    ) -> float:
        """
        Neo4j에서 두 과목 간 유사도 조회

        CourseGraphService.get_similarity_between의 lru_cache가
        프로세스 레벨에서 캐싱을 담당하므로,
        여기에서는 간단한 에러 핸델링만 수행합니다.

        Returns:
            유사도 (0.0 ~ 1.0), 관계 없거나 연결 실패 시 0.0
        """
        if not self._is_graph_available():
            return 0.0
        try:
            from lions_core.course_graph_service import CourseGraphService
            return CourseGraphService.get_similarity_between(
                source_course_code, target_course_code
            )
        except Exception as e:
            logger.warning(
                f"Neo4j 유사도 조회 실패 "
                f"({source_course_code} <-> {target_course_code}): {e}"
            )
            return 0.0
    
    def _find_best_similar_course(
        self,
        target_course_codes: Set[str],
        target_course_name: str,
        student_completed_courses: Dict
    ) -> Tuple[bool, float, Optional[Dict]]:
        """
        학생이 이수한 과목 중 타겟 과목과 가장 유사한 과목 찾기

        판정 우선순위:
        1. 동일 학수코드  → 유사도 1.0 (항상 최우선)
        2. 과목명 직접 일치 → 유사도 1.0 (Neo4j 연결 여부와 무관)
        3. Neo4j SIMILAR_TO 관계 조회 → threshold(0.7) 이상이면 인정

        [버그 수정 이력]
        이전 로직은 과목명 일치(3단계)를 Neo4j 미연결 시에만 실행하여
        Neo4j가 연결되어 있을 때 유사도 < threshold 이면 같은 과목명이라도 미인정되는
        일관성 문제가 있었습니다. 과목명 일치를 2단계로 올려 항상 실행합니다.

        Args:
            target_course_codes: 타겟 과목 학수코드 set (과목명으로 여러 코드 가능)
            target_course_name: 타겟 과목명
            student_completed_courses: 학생 이수 과목 정보

        Returns:
            (인정여부, 최고유사도, 매칭된 과목 dict or None)
        """
        # 순수 판정 로직은 scoring 모듈에 위임한다. 그래프 가용성/유사도 조회는
        # 콜러블로 주입되어 지연 평가·대체(fake)가 가능하다(의존성 역전).
        return scoring.find_best_similar_course(
            target_course_codes,
            target_course_name,
            student_completed_courses,
            is_graph_available=self._is_graph_available,
            get_similarity=self._get_similarity_from_graph,
            threshold=self._similarity_threshold,
        )
    
    def _save_evaluation_result(
        self,
        student_id: int,
        department_id: int,
        admission_year: int,
        result: Dict
    ):
        """평가 결과를 StudentRequirementStatus 테이블에 저장 (쓰기 매핑은 리포지토리가 담당)."""
        EvaluationCacheRepository(self.db).save_result(student_id, department_id, result)
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
        department = self._departments.get(department_id)
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
        
        # 해당 학과의 필수/권장 과목 리스트 가져오기 (학생 입학년도 요건과 일치시킴)
        admission_year = self.get_admission_year_from_student_id(str(student_id))
        department_courses_data = self._get_department_courses(department_id, admission_year)
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
        admission_year: Optional[int] = None
    ) -> List[Dict]:
        """여러 학생을 한 번에 평가 (admission_year 미지정 시 학번에서 학생별로 도출)"""
        results = []

        for student_id in student_ids:
            try:
                effective_admission_year = (
                    admission_year
                    if admission_year is not None
                    else self.get_admission_year_from_student_id(str(student_id))
                )
                result = self.evaluate_student(
                    student_id, department_id, effective_admission_year, save_to_db=True
                )
                results.append(result)
            except Exception as e:
                print(f"학생 {student_id} 평가 실패: {e}")
                continue
        
        return results
