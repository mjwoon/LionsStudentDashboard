"""text_features 순수 함수 단위 테스트 (표준 unittest, 외부 의존 없음)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_features import (  # noqa: E402
    PREREQ_STOPWORDS,
    STOPWORDS,
    filter_stopwords,
    filter_stopwords_many,
    is_sequential_course,
)


class FilterStopwordsTest(unittest.TestCase):
    def test_removes_stopwords_and_single_chars(self):
        # '및','수' 등은 STOPWORDS, 1글자 토큰도 제거
        self.assertEqual(filter_stopwords("데이터베이스 및 알고리즘"), "데이터베이스 알고리즘")

    def test_keeps_meaningful_tokens(self):
        self.assertEqual(filter_stopwords("자료구조 알고리즘"), "자료구조 알고리즘")

    def test_empty_after_filter(self):
        self.assertEqual(filter_stopwords("및 수 이"), "")

    def test_many(self):
        self.assertEqual(
            filter_stopwords_many(["자료구조 및 알고리즘", "및 수"]),
            ["자료구조 알고리즘", ""],
        )

    def test_prereq_extends_base(self):
        # 선수강 전용 세트는 일반 불용어를 모두 포함하고 요건 관용어를 추가한다.
        self.assertTrue(STOPWORDS <= PREREQ_STOPWORDS)
        for w in ("선수강", "필수", "수강", "추천"):
            self.assertIn(w, PREREQ_STOPWORDS)
            self.assertNotIn(w, STOPWORDS)


class IsSequentialCourseTest(unittest.TestCase):
    def test_arabic_sequence(self):
        self.assertTrue(is_sequential_course("미분적분학1", "미분적분학2"))

    def test_roman_normalized(self):
        self.assertTrue(is_sequential_course("일반물리학Ⅰ", "일반물리학Ⅱ"))

    def test_same_number_not_sequential(self):
        self.assertFalse(is_sequential_course("미분적분학1", "미분적분학1"))

    def test_different_base_not_sequential(self):
        self.assertFalse(is_sequential_course("미분적분학1", "선형대수2"))

    def test_no_sequence_number(self):
        self.assertFalse(is_sequential_course("자료구조", "알고리즘"))

    def test_trailing_paren_after_number_not_detected(self):
        # 알려진 한계(원본 동작 보존): 시퀀스 번호 뒤에 괄호가 오면 인식하지 못한다.
        # 번호가 문자열의 맨 끝일 때만 연계과목으로 판별된다.
        self.assertFalse(is_sequential_course("회로이론1(설계)", "회로이론2(설계)"))


if __name__ == "__main__":
    unittest.main()
