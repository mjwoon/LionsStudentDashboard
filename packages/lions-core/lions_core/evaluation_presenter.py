from typing import List, Dict, Callable
from lions_core.models import Student, Department, StudentCourse
from lions_core.constants import EVALUATION_WEIGHTS

class EvaluationResponseBuilder:
    """Evaluation Service에서 계산된 Raw 데이터를 받아 API 응답 형태(JSON)로 포맷팅하는 역할을 담당합니다."""

    @staticmethod
    def build_analysis_json(
        student: Student,
        department: Department,
        enrollments: List[StudentCourse],
        student_completed_courses: Dict,
        entry_breakdown: Dict,
        recommended_exact_rate: float,
        recommended_similar_rate: float,
        curriculum_exact_rate: float,
        curriculum_similar_rate: float,
        necessary_courses: List[Dict],
        recommended_course_names: List[str],
        first_year_courses: List[Dict],
        course_name_to_codes: Dict[str, set],
        is_graph_available: bool,
        find_best_similar_course_func: Callable
    ) -> Dict:
        """상세 분석 JSON 생성 (3-메트릭 체계)"""

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

        for rec_name in recommended_course_names:
            is_exact_match = False
            is_similar_match = False
            similarity = 0.0
            matched_course = None
            matched_by = None  # 'exact', 'graph_similar', 'name_similar'

            # 동일과목 체크
            if rec_name in completed_names:
                expected_codes = course_name_to_codes.get(rec_name, set())
                if expected_codes & completed_codes:
                    is_exact_match = True
                    for detail in completed_details:
                        if detail["course_name"] == rec_name:
                            matched_course = detail
                            break

            # 유사과목 체크 (Neo4j 또는 폴백)
            target_codes = course_name_to_codes.get(rec_name, set())
            is_similar, sim_score, sim_match = find_best_similar_course_func(
                target_codes, rec_name, student_completed_courses
            )
            if is_similar:
                is_similar_match = True
                similarity = sim_score
                if not matched_course:
                    matched_course = sim_match
                # 매칭 방식 판별
                if is_exact_match:
                    matched_by = 'exact'
                elif sim_score < 1.0 and is_graph_available:
                    matched_by = 'graph_similar'
                else:
                    matched_by = 'name_similar'

            recommended_details.append({
                "course_name": rec_name,
                "is_exact_match": is_exact_match,
                "is_similar_match": is_similar_match,
                "similarity": round(similarity, 4),
                "matched_by": matched_by,
                "matched_course": matched_course
            })

        # 3. 교육과정(1학년) 상세
        curriculum_details = []
        for course in first_year_courses:
            course_code = course.get("course_code", "")
            course_name = course.get("course_name", "")

            is_exact_match = course_code in completed_codes

            # 유사과목 체크 (Neo4j 또는 폴백)
            target_codes = {course_code} if course_code else set()
            is_similar, sim_score, sim_match = find_best_similar_course_func(
                target_codes, course_name, student_completed_courses
            )
            is_similar_match = is_similar
            similarity = sim_score
            matched_course = sim_match

            # 매칭 방식 판별
            matched_by = None
            if is_exact_match:
                matched_by = 'exact'
                # exact인 경우 matched_course 설정
                if not matched_course:
                    for detail in completed_details:
                        if detail["course_code"] == course_code:
                            matched_course = detail
                            break
            elif is_similar_match:
                if similarity < 1.0 and is_graph_available:
                    matched_by = 'graph_similar'
                else:
                    matched_by = 'name_similar'

            curriculum_details.append({
                "course_code": course_code,
                "course_name": course_name,
                "is_exact_match": is_exact_match,
                "is_similar_match": is_similar_match,
                "similarity": round(similarity, 4),
                "matched_by": matched_by,
                "matched_course": matched_course
            })

        # 종합 점수 계산 (가중치 SSOT: constants.EVALUATION_WEIGHTS)
        overall_score = (
            entry_breakdown["score"] * EVALUATION_WEIGHTS["entry_requirement"] +
            recommended_similar_rate * EVALUATION_WEIGHTS["recommended_courses"] +
            curriculum_similar_rate * EVALUATION_WEIGHTS["curriculum_completion"]
        )

        return {
            # 진입요건: 규칙 분해(최고 그룹 기준)로 점수·표시 일치. total/completed는
            # 그 그룹의 required/qualifying이라 화면의 "X/Y 과목"이 score와 어긋나지 않는다.
            "entry_requirement": {
                "score": entry_breakdown["score"],
                "total_courses": entry_breakdown["required"],
                "completed_courses": entry_breakdown["qualifying"],
                "has_requirement": entry_breakdown["has_requirement"],
                "details": entry_requirement_details,
                "status": "충족" if entry_breakdown["satisfied"] else "미충족"
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
                "weights": dict(EVALUATION_WEIGHTS)
            }
        }
