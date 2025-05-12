from a2a_protocol.models import AgentCard, AgentCapability
from config import AGENT_ID, AGENT_NAME, AGENT_DESCRIPTION, A2A_PROTOCOL_VERSION, SERVER_HOST, SERVER_PORT


def create_agent_card() -> AgentCard:
    """고객 지원 에이전트의 Agent Card 생성"""

    capabilities = [
        AgentCapability(
            name="answer_general_questions",
            description="일반적인 고객 질문에 답변"
        ),
        AgentCapability(
            name="answer_product_questions",
            description="제품 관련 질문에 답변"
        ),
        AgentCapability(
            name="track_shipping",
            description="배송 추적 정보 제공",
            parameters={
                "order_id": "주문 번호"
            }
        ),
        AgentCapability(
            name="billing_inquiry",
            description="결제 및 청구 관련 문의 처리",
            parameters={
                "invoice_id": "청구서 번호"
            }
        )
    ]

    base_url = f"http://{SERVER_HOST}:{SERVER_PORT}"

    agent_card = AgentCard(
        id=AGENT_ID,
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version=A2A_PROTOCOL_VERSION,
        capabilities=capabilities,
        base_url=base_url,
        auth_required=False
    )

    return agent_card
