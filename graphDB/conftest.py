"""pytest 부트스트랩: graphDB 디렉터리를 sys.path 최상단에 둬서
`experiment.*`, `similarity_engine`, `text_features` 를 절대 임포트할 수 있게 한다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
