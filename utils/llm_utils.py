import traceback
from typing import Dict, Any, List, Optional
import openai
from config import LLM_API_KEY, LLM_MODEL

# OpenAI API 키 설정
openai.api_key = LLM_API_KEY


async def generate_response(query: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
    """LLM을 사용하여 고객 질문에 답변 생성"""

    messages = []

    # 시스템 프롬프트 추가
    messages.append({
        "role": "system",
        "content": "당신은 친절하고 도움이 되는 고객 지원 에이전트입니다. 질문에 정확하고 간결하게 답변해주세요."
    })

    # 컨텍스트 추가 (있는 경우)
    if context:
        for item in context:
            messages.append(item)

    # 사용자 쿼리 추가
    messages.append({
        "role": "user",
        "content": query
    })

    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content
    except Exception as e:
        traceback.print_exc()
        return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}"


async def categorize_query(query: str) -> str:
    """고객 쿼리를 카테고리로 분류"""

    messages = [
        {
            "role": "system",
            "content": "다음 카테고리 중 하나로 고객 질문을 분류하세요: general, product, shipping, billing, other"
        },
        {
            "role": "user",
            "content": f"다음 고객 질문을 카테고리로 분류해주세요: '{query}'"
        }
    ]

    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=20
        )

        category = response.choices[0].message.content.strip().lower()

        # 유효한 카테고리인지 확인
        valid_categories = ["general", "product", "shipping", "billing", "other"]
        if category not in valid_categories:
            return "general"

        return category
    except Exception as e:
        traceback.print_exc()
        return "general"  # 오류 발생 시 기본 카테고리 반환
