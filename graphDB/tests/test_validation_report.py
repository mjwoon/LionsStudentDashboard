"""format_validation_report 순수 포매터 단위 테스트 (DB 불필요)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from course_graph_analysis import format_validation_report  # noqa: E402


def _sample_report(isolated_n=2, requires_total=3):
    quality = {"total": 0}
    if requires_total:
        quality = {
            "total": requires_total,
            "exact_match": {"count": 1, "rate": 33.3},
            "high_confidence": {"count": 1, "rate": 33.3},
            "medium_confidence": {"count": 1, "rate": 33.3},
            "low_confidence": {"count": 0, "rate": 0.0},
            "avg_confidence": 0.8,
        }
    return {
        "summary": {
            "node": {"num_courses": 100},
            "similar_to": {"num_edges": 250, "avg_similarity": 0.62,
                           "min_similarity": 0.5, "max_similarity": 0.9},
            "identical_id": {"num_edges": 4},
            "requires": {"num_edges": requires_total, "avg_confidence": 0.8,
                         "exact_matches": 1, "semantic_matches": 2},
            "unmapped_prerequisites": {"courses_count": 7, "sample": []},
        },
        "threshold_sensitivity": [
            {"threshold": 0.5, "num_edges": 250, "coverage_rate": 100.0},
            {"threshold": 0.7, "num_edges": 80, "coverage_rate": 32.0},
        ],
        "requires_quality": quality,
        "unmapped_sample": [{"course_name": "알고리즘", "unmapped_text": "수학필수"}],
        "isolated": [
            {"name": f"과목{i}", "code": f"C{i}", "department": "컴퓨터", "category": "전공"}
            for i in range(isolated_n)
        ],
    }


class FormatValidationReportTest(unittest.TestCase):
    def test_contains_core_sections(self):
        out = format_validation_report(_sample_report())
        for token in ("[1] 그래프 구축 요약", "교과목(노드) 수:         100",
                      "SIMILAR_TO 엣지 수:     250", "[2] 유사도 임계값별",
                      "[3] 선수강 매핑 품질", "[4] 매핑 실패", "[5] 고립 노드"):
            self.assertIn(token, out)

    def test_unmapped_sample_rendered(self):
        out = format_validation_report(_sample_report())
        self.assertIn("[알고리즘] → 수학필수", out)

    def test_empty_requires_quality(self):
        out = format_validation_report(_sample_report(requires_total=0))
        self.assertIn("REQUIRES 엣지가 없습니다.", out)

    def test_isolated_overflow_summarized(self):
        out = format_validation_report(_sample_report(isolated_n=8))
        self.assertIn("총 8개", out)
        self.assertIn("... 외 3개", out)  # 8 - 5

    def test_returns_str_not_none(self):
        self.assertIsInstance(format_validation_report(_sample_report()), str)


if __name__ == "__main__":
    unittest.main()
