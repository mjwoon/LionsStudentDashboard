"""
AI 총평 생성 서비스
OpenAI API를 활용하여 평가 결과에 대한 자연어 총평을 생성합니다.
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# OpenAI 설정
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


EVALUATION_PROMPT_TEMPLATE = """당신은 대학교 학사 상담 전문가입니다.
아래 학생의 전공진입 적합도 평가 결과를 분석하여 3~5문장의 총평을 작성해주세요.
학생에게 직접 말하는 톤(~입니다, ~하세요)으로 작성하고, 구체적인 과목명을 언급해주세요.

[평가 결과]
- 목표 학과: {department_name}
- 종합 점수: {overall_score}점 (등급: {grade})
- 진입요건 충족: {entry_requirement_score}%
- 권장과목 이수율: 동일 {recommended_exact_rate}% / 유사 {recommended_similar_rate}%
- 교육과정 이수율: 동일 {curriculum_exact_rate}% / 유사 {curriculum_similar_rate}%

[진입요건 상세]
{entry_details}

[미이수 권장과목]
{unmet_recommended}

[미이수 교육과정 과목]
{unmet_curriculum}

총평에는 다음을 포함해주세요:
1. 전반적인 적합도 평가 (한 줄)
2. 강점 (잘 준비된 부분)
3. 보완이 필요한 부분과 구체적 과목 추천
4. 전공진입을 위한 간단한 조언"""


class AIService:
    """AI 총평 생성 서비스 (OpenAI API)"""
    
    def __init__(self):
        self._client = None
    
    def _get_client(self):
        """OpenAI 클라이언트 지연 초기화"""
        if self._client is None:
            try:
                from openai import OpenAI
                api_key = OPENAI_API_KEY
                if not api_key:
                    logger.warning("OPENAI_API_KEY가 설정되지 않았습니다.")
                    return None
                self._client = OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai 패키지가 설치되지 않았습니다.")
                return None
            except Exception as e:
                logger.warning(f"OpenAI 클라이언트 초기화 실패: {e}")
                return None
        return self._client
    
    def generate_evaluation_summary(self, evaluation_result: Dict) -> Optional[str]:
        """
        평가 결과를 기반으로 AI 총평 생성
        
        Args:
            evaluation_result: 평가 결과 dict
            
        Returns:
            AI 생성 총평 문자열, 실패 시 None
        """
        client = self._get_client()
        if client is None:
            return None
        
        try:
            prompt = self._build_prompt(evaluation_result)
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 대학교 학사 상담 전문가입니다. 학생에게 도움이 되는 간결하고 구체적인 조언을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"AI 총평 생성 완료 (학과: {evaluation_result.get('department_name', 'N/A')})")
            return summary
            
        except Exception as e:
            logger.warning(f"AI 총평 생성 실패: {e}")
            return None
    
    def _build_prompt(self, result: Dict) -> str:
        """평가 결과에서 프롬프트 생성"""
        analysis = result.get("analysis_json", {})
        
        # 진입요건 상세
        entry_req = analysis.get("entry_requirement", {})
        entry_details_list = []
        for detail in entry_req.get("details", []):
            status = "✅ 이수" if detail.get("is_completed") else "❌ 미이수"
            entry_details_list.append(f"  - {detail.get('course_name', '?')} ({detail.get('course_code', '?')}): {status}")
        entry_details = "\n".join(entry_details_list) if entry_details_list else "  (진입요건 없음)"
        
        # 미이수 권장과목
        recommended = analysis.get("recommended_courses", {})
        unmet_rec = []
        for detail in recommended.get("details", []):
            if not detail.get("is_similar_match"):
                unmet_rec.append(f"  - {detail.get('course_name', '?')}")
        unmet_recommended = "\n".join(unmet_rec) if unmet_rec else "  (모두 이수 완료)"
        
        # 미이수 교육과정 과목
        curriculum = analysis.get("curriculum_completion", {})
        unmet_cur = []
        for detail in curriculum.get("details", []):
            if not detail.get("is_similar_match"):
                unmet_cur.append(f"  - {detail.get('course_name', '?')} ({detail.get('course_code', '?')})")
        unmet_curriculum = "\n".join(unmet_cur) if unmet_cur else "  (모두 이수 완료)"
        
        return EVALUATION_PROMPT_TEMPLATE.format(
            department_name=result.get("department_name", "알 수 없음"),
            overall_score=result.get("overall_score", 0),
            grade=result.get("grade", "N/A"),
            entry_requirement_score=result.get("entry_requirement_score", 0),
            recommended_exact_rate=result.get("recommended_exact_rate", 0),
            recommended_similar_rate=result.get("recommended_similar_rate", 0),
            curriculum_exact_rate=result.get("curriculum_exact_rate", 0),
            curriculum_similar_rate=result.get("curriculum_similar_rate", 0),
            entry_details=entry_details,
            unmet_recommended=unmet_recommended,
            unmet_curriculum=unmet_curriculum
        )
