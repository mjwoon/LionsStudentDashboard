"""
전공진입 적합도 평가 서비스

5개 메트릭 기반 평가 시스템:
1. GPA 점수 (25%)
2. 필수과목 학점 점수 (30%)
3. 권장과목 이수 여부 점수 (15%)
4. 권장과목 학점 점수 (15%)
5. 교육과정 완성도 점수 (15%)
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os
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


class EvaluationService:
    """5개 메트릭 기반 평가 서비스"""
    
    # 가중치 설정 (합계 100%)
    WEIGHT_REQUIRED_COURSES = 0.40  # 필수과목 학점 40% (핵심)
    WEIGHT_GPA = 0.20  # GPA 20%
    WEIGHT_RECOMMENDED_COMPLETION = 0.15  # 권장과목 이수 여부 15%
    WEIGHT_RECOMMENDED_GRADE = 0.15  # 권장과목 학점 15%
    WEIGHT_CURRICULUM_COMPLETION = 0.10  # 교육과정 완성도 10%
    
    # 성적 등급 -> 숫자 매핑
    GRADE_TO_NUMERIC = {
        'A+': 4.5, 'A0': 4.0,
        'B+': 3.3, 'B0': 3.0,
        'C+': 2.3, 'C0': 2.0,
        'D+': 1.3, 'D0': 1.0,
        'F': 0.0,
    }
    
    # 학년별 등급 -> 최소 점수 매핑
    GRADE_LEVEL_MINIMUM = {
        GradeLevelEnum.A: 4.0,  # A 이상: 4.0 이상
        GradeLevelEnum.B: 3.0,  # B 이상: 3.0 이상
        GradeLevelEnum.C: 2.0,  # C 이상: 2.0 이상
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._load_recommended_courses()
    
    def _load_recommended_courses(self):
        """권장과목 데이터 로드"""
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "recommended.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 학과명 -> 권장과목 리스트 매핑
        self.recommended_courses_map = {}
        for college in data.get("colleges", []):
            for major in college.get("majors", []):
                major_name = major["name"]
                self.recommended_courses_map[major_name] = major.get("recommended_courses", [])
    
    def evaluate_student(
        self,
        student_id: int,
        department_id: int,
        admission_year: int = 2026,
        save_to_db: bool = True
    ) -> Dict:
        """
        학생의 학과 적합도를 5개 메트릭으로 평가
        
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
        
        # 진입요건 조회
        entry_requirements = self.db.query(DepartmentEntryRequirement).filter(
            DepartmentEntryRequirement.department_id == department_id,
            DepartmentEntryRequirement.admission_year == admission_year
        ).all()
        
        # 1. GPA 점수 계산 (25%)
        gpa_score = self._calculate_gpa_score(student)
        
        # 2. 필수과목 학점 점수 (30%)
        required_score = self._calculate_required_courses_score(
            enrollments, entry_requirements
        )
        
        # 3. 권장과목 이수 여부 점수 (15%)
        recommended_completion_score = self._calculate_recommended_completion_score(
            enrollments, department.name
        )
        
        # 4. 권장과목 학점 점수 (15%)
        recommended_grade_score = self._calculate_recommended_grade_score(
            enrollments, department.name
        )
        
        # 5. 교육과정 완성도 점수 (15%)
        curriculum_completion_score = self._calculate_curriculum_completion_score(
            enrollments, department_id
        )
        
        # 6. 종합 점수 계산
        overall_score = (
            required_score * self.WEIGHT_REQUIRED_COURSES +
            gpa_score * self.WEIGHT_GPA +
            recommended_completion_score * self.WEIGHT_RECOMMENDED_COMPLETION +
            recommended_grade_score * self.WEIGHT_RECOMMENDED_GRADE +
            curriculum_completion_score * self.WEIGHT_CURRICULUM_COMPLETION
        )
        
        # 7. 상세 분석 JSON 생성
        analysis_json = self._build_analysis_json(
            student, department, enrollments, entry_requirements,
            gpa_score, required_score, recommended_completion_score,
            recommended_grade_score, curriculum_completion_score
        )
        
        # 등급 판정
        if overall_score >= 90:
            grade = 'A'
        elif overall_score >= 80:
            grade = 'B'
        elif overall_score >= 70:
            grade = 'C'
        elif overall_score >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        result = {
            'student_id': student_id,
            'department_id': department_id,
            'department_name': department.name,
            'gpa_score': round(gpa_score, 2),
            'required_courses_score': round(required_score, 2),
            'recommended_completion_score': round(recommended_completion_score, 2),
            'recommended_grade_score': round(recommended_grade_score, 2),
            'curriculum_completion_score': round(curriculum_completion_score, 2),
            'overall_score': round(overall_score, 2),
            'grade': grade,
            'analysis_json': analysis_json,
            'evaluated_at': datetime.utcnow()
        }
        
        # DB에 저장
        if save_to_db:
            self._save_evaluation_result(student_id, department_id, admission_year, result)
        
        return result
    
    def _calculate_gpa_score(self, student: Student) -> float:
        """
        GPA 점수 계산 (25%)
        
        GPA를 100점 만점으로 환산
        - 4.5 = 100점
        - 0.0 = 0점
        """
        if not student.current_gpa or student.current_gpa == 0:
            return 0.0
        
        # GPA를 100점 만점으로 환산 (4.5 만점 기준)
        score = (float(student.current_gpa) / 4.5) * 100
        return min(100.0, max(0.0, score))
    
    def _calculate_required_courses_score(
        self,
        enrollments: List[CourseEnrollment],
        entry_requirements: List[DepartmentEntryRequirement]
    ) -> float:
        """
        필수과목 학점 점수 계산 (30%)
        
        진입요건을 충족한 비율로 점수 계산
        OR 조건도 처리
        """
        if not entry_requirements:
            return 100.0  # 진입요건 없으면 만점
        
        # 이수한 과목 정보 구축
        enrolled_courses_map = self._build_enrolled_courses_map(enrollments)
        
        satisfied_count = 0
        total_count = len(entry_requirements)
        
        for requirement in entry_requirements:
            # 요건 과목 조회
            req_courses = self.db.query(RequirementCourse).filter(
                RequirementCourse.requirement_id == requirement.id
            ).all()
            
            if not req_courses:
                continue
            
            # OR 조건 처리
            if requirement.logic_operator == "OR":
                is_satisfied = self._check_or_condition(
                    requirement, req_courses, enrolled_courses_map
                )
            else:  # AND 조건 (기본)
                is_satisfied = self._check_and_condition(
                    requirement, req_courses, enrolled_courses_map
                )
            
            if is_satisfied:
                satisfied_count += 1
        
        # 충족률을 점수로 환산
        if total_count == 0:
            return 100.0
        
        score = (satisfied_count / total_count) * 100
        return round(score, 2)
    
    def _check_or_condition(
        self,
        requirement: DepartmentEntryRequirement,
        req_courses: List[RequirementCourse],
        enrolled_courses_map: Dict
    ) -> bool:
        """
        OR 조건 체크
        
        예: "B 이상 2과목 OR A 이상 1과목"
        - 요건 과목 중 B 이상으로 2과목 이상 이수했거나
        - 요건 과목 중 A 이상으로 1과목 이상 이수했으면 충족
        """
        course_codes = [rc.course_code for rc in req_courses]
        
        # B 이상 조건 확인
        b_or_higher = []
        a_or_higher = []
        
        for course_code in course_codes:
            if course_code in enrolled_courses_map:
                course_info = enrolled_courses_map[course_code]
                numeric_grade = course_info.get('numeric_grade', 0)
                
                if numeric_grade >= self.GRADE_LEVEL_MINIMUM.get(GradeLevelEnum.B, 3.0):
                    b_or_higher.append(course_code)
                
                if numeric_grade >= self.GRADE_LEVEL_MINIMUM.get(GradeLevelEnum.A, 4.0):
                    a_or_higher.append(course_code)
        
        # OR 조건: B 이상 required_count개 이상 OR A 이상 1개 이상
        required_count = requirement.required_count or 2
        
        condition1 = len(b_or_higher) >= required_count  # B 이상 N과목
        condition2 = len(a_or_higher) >= 1  # A 이상 1과목
        
        return condition1 or condition2
    
    def _check_and_condition(
        self,
        requirement: DepartmentEntryRequirement,
        req_courses: List[RequirementCourse],
        enrolled_courses_map: Dict
    ) -> bool:
        """
        AND 조건 체크 (기본)
        
        요건 과목 중 required_count개 이상을 target_grade_level 이상으로 이수
        """
        course_codes = [rc.course_code for rc in req_courses]
        satisfied_courses = []
        
        min_grade = self.GRADE_LEVEL_MINIMUM.get(
            requirement.target_grade_level,
            3.0  # 기본값 B 이상
        )
        
        for course_code in course_codes:
            if course_code in enrolled_courses_map:
                course_info = enrolled_courses_map[course_code]
                numeric_grade = course_info.get('numeric_grade', 0)
                
                if numeric_grade >= min_grade:
                    satisfied_courses.append(course_code)
        
        required_count = requirement.required_count or 1
        return len(satisfied_courses) >= required_count
    
    def _calculate_recommended_completion_score(
        self,
        enrollments: List[CourseEnrollment],
        department_name: str
    ) -> float:
        """
        권장과목 이수 여부 점수 (15%)
        
        권장과목 중 몇 개를 이수했는지 비율로 계산
        """
        recommended_courses = self.recommended_courses_map.get(department_name, [])
        
        if not recommended_courses:
            return 100.0  # 권장과목 없으면 만점
        
        # 이수한 과목명 목록
        enrolled_course_names = set()
        for enrollment in enrollments:
            course = self.db.query(Course).filter(
                Course.id == enrollment.course_id
            ).first()
            if course:
                enrolled_course_names.add(course.course_name)
        
        # 권장과목 이수 개수 계산
        completed_count = sum(
            1 for rec_course in recommended_courses
            if rec_course in enrolled_course_names
        )
        
        # 비율을 점수로 환산
        score = (completed_count / len(recommended_courses)) * 100
        return round(score, 2)
    
    def _calculate_recommended_grade_score(
        self,
        enrollments: List[CourseEnrollment],
        department_name: str
    ) -> float:
        """
        권장과목 학점 점수 (15%)
        
        권장과목의 평균 성적을 100점 만점으로 환산
        """
        recommended_courses = self.recommended_courses_map.get(department_name, [])
        
        if not recommended_courses:
            return 100.0  # 권장과목 없으면 만점
        
        # 권장과목 중 이수한 과목의 성적 수집
        grades = []
        for enrollment in enrollments:
            course = self.db.query(Course).filter(
                Course.id == enrollment.course_id
            ).first()
            if course and course.course_name in recommended_courses:
                if enrollment.numeric_grade is not None:
                    grades.append(float(enrollment.numeric_grade))
        
        if not grades:
            return 0.0  # 권장과목 미이수
        
        # 평균 성적을 100점 만점으로 환산
        avg_grade = sum(grades) / len(grades)
        score = (avg_grade / 4.5) * 100
        return round(score, 2)
    
    def _calculate_curriculum_completion_score(
        self,
        enrollments: List[CourseEnrollment],
        department_id: int
    ) -> float:
        """
        교육과정 완성도 점수 (10%)
        
        해당 학과의 1학년 과목 중 이수한 비율
        """
        # 해당 학과의 1학년 과목 조회
        dept_courses = self.db.query(Course).filter(
            Course.department_id == department_id,
            Course.course_year == 1
        ).all()
        
        # 1학년 과목이 없으면 0점 반환
        if not dept_courses:
            return 0.0
        
        dept_course_ids = {c.id for c in dept_courses}
        
        # 이수한 전공과목 개수 (F학점 제외)
        completed_count = sum(
            1 for enrollment in enrollments
            if enrollment.course_id in dept_course_ids and
            enrollment.grade and enrollment.grade != 'F'
        )
        
        # 비율을 점수로 환산
        score = (completed_count / len(dept_courses)) * 100
        return round(min(100.0, score), 2)
    
    def _build_enrolled_courses_map(
        self,
        enrollments: List[CourseEnrollment]
    ) -> Dict:
        """이수한 과목 정보를 course_code로 매핑"""
        enrolled_map = {}
        
        for enrollment in enrollments:
            course = self.db.query(Course).filter(
                Course.id == enrollment.course_id
            ).first()
            
            if course:
                enrolled_map[course.course_code] = {
                    'course_name': course.course_name,
                    'grade': enrollment.grade,
                    'numeric_grade': float(enrollment.numeric_grade) if enrollment.numeric_grade else 0,
                    'credits': course.credits
                }
        
        return enrolled_map
    
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
        status.gpa_score = result['gpa_score']
        status.required_courses_score = result['required_courses_score']
        status.recommended_completion_score = result['recommended_completion_score']
        status.recommended_grade_score = result['recommended_grade_score']
        status.curriculum_completion_score = result['curriculum_completion_score']
        status.overall_score = result['overall_score']
        status.analysis_json = result.get('analysis_json')
        status.calculated_at = result['evaluated_at']
        
        # 충족 여부 판정 (required_courses_score가 100점이고 overall이 70점 이상)
        status.is_satisfied = (
            result['required_courses_score'] >= 100.0 and
            result['overall_score'] >= 70.0
        )
        
        self.db.commit()
    
    def _build_analysis_json(
        self,
        student: Student,
        department: Department,
        enrollments: List[CourseEnrollment],
        entry_requirements: List[DepartmentEntryRequirement],
        gpa_score: float,
        required_score: float,
        recommended_completion_score: float,
        recommended_grade_score: float,
        curriculum_completion_score: float
    ) -> Dict:
        """
        상세 분석 JSON 생성
        
        Returns:
            분석 데이터 딕셔너리
        """
        enrolled_courses_map = self._build_enrolled_courses_map(enrollments)
        
        # 진입요건 상세 분석
        entry_requirements_details = []
        completed_requirements = []
        
        for requirement in entry_requirements:
            req_courses = self.db.query(RequirementCourse).filter(
                RequirementCourse.requirement_id == requirement.id
            ).all()
            
            if not req_courses:
                continue
            
            # 요건 충족 여부 확인
            if requirement.logic_operator == "OR":
                is_satisfied = self._check_or_condition(
                    requirement, req_courses, enrolled_courses_map
                )
            else:
                is_satisfied = self._check_and_condition(
                    requirement, req_courses, enrolled_courses_map
                )
            
            if is_satisfied:
                completed_requirements.append(requirement.requirement_text)
            
            # 각 과목별 상세 정보
            course_details = []
            for req_course in req_courses:
                course_info = enrolled_courses_map.get(req_course.course_code, {})
                course = self.db.query(Course).filter(
                    Course.course_code == req_course.course_code
                ).first()
                
                course_details.append({
                    "course_code": req_course.course_code,
                    "course_name": course.course_name if course else "Unknown",
                    "grade": course_info.get('grade', 'Not Taken'),
                    "numeric_grade": course_info.get('numeric_grade', 0),
                    "satisfied": course_info.get('numeric_grade', 0) >= self.GRADE_LEVEL_MINIMUM.get(
                        requirement.target_grade_level, 3.0
                    ) if course_info else False
                })
            
            entry_requirements_details.append({
                "requirement_text": requirement.requirement_text,
                "target_grade_level": requirement.target_grade_level.value,
                "required_count": requirement.required_count,
                "logic_operator": requirement.logic_operator,
                "is_satisfied": is_satisfied,
                "courses": course_details
            })
        
        # 권장과목 분석
        recommended_courses = self.recommended_courses_map.get(department.name, [])
        enrolled_course_names = set()
        for enrollment in enrollments:
            course = self.db.query(Course).filter(
                Course.id == enrollment.course_id
            ).first()
            if course:
                enrolled_course_names.add(course.course_name)
        
        completed_recommended = [
            course for course in recommended_courses
            if course in enrolled_course_names
        ]
        
        # 교육과정 완성도 상세 정보 계산 (1학년만)
        dept_courses = self.db.query(Course).filter(
            Course.department_id == department.id,
            Course.course_year == 1,
            or_(
                Course.course_type.like('%전공%'),
                Course.course_type == '전공기초',
                Course.course_type == '전공핵심',
                Course.course_type == '교양필수'
            )
        ).all()
        
        dept_course_ids = {c.id for c in dept_courses}
        completed_curriculum_count = sum(
            1 for enrollment in enrollments
            if enrollment.course_id in dept_course_ids and
            enrollment.grade and enrollment.grade != 'F'
        )
        
        return {
            "entry_requirements": {
                "status": "satisfied" if required_score >= 100 else "not_satisfied",
                "completed_requirements": completed_requirements,
                "details": entry_requirements_details
            },
            "gpa": {
                "current_gpa": float(student.current_gpa) if student.current_gpa else 0.0,
                "max_gpa": 4.5,
                "score": gpa_score
            },
            "recommended_courses": {
                "total": len(recommended_courses),
                "completed": len(completed_recommended),
                "completion_rate": len(completed_recommended) / len(recommended_courses) if recommended_courses else 0,
                "completed_list": completed_recommended,
                "score": recommended_completion_score
            },
            "recommended_grades": {
                "score": recommended_grade_score
            },
            "curriculum_completion": {
                "score": curriculum_completion_score,
                "completed_count": completed_curriculum_count,
                "total_count": len(dept_courses),
                "completion_rate": completed_curriculum_count / len(dept_courses) if dept_courses else 0,
                "status": "완료" if curriculum_completion_score >= 100 else "진행중"
            },
            "overall": {
                "score": (
                    required_score * self.WEIGHT_REQUIRED_COURSES +
                    gpa_score * self.WEIGHT_GPA +
                    recommended_completion_score * self.WEIGHT_RECOMMENDED_COMPLETION +
                    recommended_grade_score * self.WEIGHT_RECOMMENDED_GRADE +
                    curriculum_completion_score * self.WEIGHT_CURRICULUM_COMPLETION
                ),
                "weights": {
                    "required_courses": self.WEIGHT_REQUIRED_COURSES,
                    "gpa": self.WEIGHT_GPA,
                    "recommended_completion": self.WEIGHT_RECOMMENDED_COMPLETION,
                    "recommended_grade": self.WEIGHT_RECOMMENDED_GRADE,
                    "curriculum_completion": self.WEIGHT_CURRICULUM_COMPLETION
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
