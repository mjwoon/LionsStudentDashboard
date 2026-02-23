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


EVALUATION_PROMPT_TEMPLATE = """# Role
당신은 자유전공학부생의 전공 진입을 돕는 'AI 지도교수'입니다.
제공된 데이터를 바탕으로 학과별 전공 이수 체계와 학생의 학습 상태를 종합 분석하여, 전공 진입 적합성을 최종 진단합니다.

# Input Data
[목표 학과]: {department_name}
[진입요건 충족]: {entry_requirement_score}%
[권장과목 이수율]: 동일 {recommended_exact_rate}% / 유사 {recommended_similar_rate}%
[교육과정 이수율]: 동일 {curriculum_exact_rate}% / 유사 {curriculum_similar_rate}%

[진입요건 상세]
{entry_details}

[미이수 권장과목]
{unmet_recommended}

[미이수 교육과정 과목]
{unmet_curriculum}

# 통합 진단 논리
- [위계 리스크]: 선행 학기의 필수/기초 과목 누락 여부 (누락 시 상태값 하향)
- [잠재력/적성]: 희망 전공 관련 핵심 과목의 수강 여부 및 이수율 (높을 시 상태값 상향)

상태값 결정 가이드:
- 우수: 이수 계통을 완벽히 준수하고 주요 과목 이수율이 매우 높은 경우
- 양호: 일부 누락이 있으나 이수율이 우수하여 극복 가능한 경우
- 주의: 이수율은 좋으나 필수 과목 누락이 심각하거나, 계통은 맞으나 이수율이 저조한 경우
- 위험: 필수 과목 누락이 심각하고 전반적 이수율도 저조한 경우

# Output Format
반드시 아래 양식으로 **단 한 줄**만 출력하십시오.
[상태값] : [이수 계통의 안정성과 전공 적합성을 종합한 최종 상담 의견]

예시:
우수 : 이수 계통이 완벽하며 권장과목 이수율이 매우 높아 진입에 적합합니다.

# 출력 길이 제한
- 오직 1줄(1 sentence)로 제한하여 작성하십시오.
- 친절한 어조를 유지하되, 공손한 인사말을 반복하지 않습니다.
- 완결성과 실용성을 길이 제한 내에서 최우선으로 유지합니다."""


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
                    {"role": "system", "content": "당신은 자유전공학부생의 전공 진입을 돕는 AI 지도교수입니다. 지침에 따라 단 한 줄의 진단 결과만 출력하십시오."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=150
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
            entry_requirement_score=result.get("entry_requirement_score", 0),
            recommended_exact_rate=result.get("recommended_exact_rate", 0),
            recommended_similar_rate=result.get("recommended_similar_rate", 0),
            curriculum_exact_rate=result.get("curriculum_exact_rate", 0),
            curriculum_similar_rate=result.get("curriculum_similar_rate", 0),
            entry_details=entry_details,
            unmet_recommended=unmet_recommended,
            unmet_curriculum=unmet_curriculum
        )
