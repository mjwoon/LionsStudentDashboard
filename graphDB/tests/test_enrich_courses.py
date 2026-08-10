"""enrich_courses 조인 로직 단위 테스트."""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enrich_courses import enrich  # noqa: E402


class EnrichTest(unittest.TestCase):
    def _group3(self):
        return pd.DataFrame({
            "교과목이름": ["자료구조", "알고리즘", "알고리즘", "미분적분학"],
            "학수번호": ["CSE201", "CSE301", "MAT301", "MAT101"],
            "학점": [3, 3, 3, 2],
            "설강학과": ["컴퓨터", "컴퓨터", "수학", "수학"],
        })

    def test_pair_match(self):
        agg = pd.DataFrame({"교과목 이름": ["자료구조"], "설강학과": ["컴퓨터"]})
        out, stats = enrich(agg, self._group3())
        self.assertEqual(out["학수번호"].iloc[0], "CSE201")
        self.assertEqual(out["학점"].iloc[0], 3)
        self.assertEqual(stats["matched_pair"], 1)

    def test_ambiguous_name_requires_dept(self):
        # '알고리즘'은 group3에 학과가 둘 → 이름 단독 매칭 불가, 학과로 구분
        agg = pd.DataFrame({"교과목 이름": ["알고리즘"], "설강학과": ["수학"]})
        out, _ = enrich(agg, self._group3())
        self.assertEqual(out["학수번호"].iloc[0], "MAT301")

    def test_unique_name_fallback(self):
        # '미분적분학'은 유일 → 학과가 달라도 이름 단독 보조 매칭
        agg = pd.DataFrame({"교과목 이름": ["미분적분학"], "설강학과": ["교양학부"]})
        out, stats = enrich(agg, self._group3())
        self.assertEqual(out["학수번호"].iloc[0], "MAT101")
        self.assertEqual(stats["matched_name"], 1)

    def test_unmatched_is_blank(self):
        agg = pd.DataFrame({"교과목 이름": ["없는과목"], "설강학과": ["컴퓨터"]})
        out, stats = enrich(agg, self._group3())
        self.assertEqual(out["학수번호"].iloc[0], "")
        self.assertEqual(out["학점"].iloc[0], "")
        self.assertEqual(stats["unmatched"], 1)

    def test_spaced_name_normalized(self):
        # aggregated 이름에 공백이 있어도 정규화되어 매칭
        agg = pd.DataFrame({"교과목 이름": ["자료 구조"], "설강학과": ["컴퓨터"]})
        out, _ = enrich(agg, self._group3())
        self.assertEqual(out["학수번호"].iloc[0], "CSE201")


if __name__ == "__main__":
    unittest.main()
