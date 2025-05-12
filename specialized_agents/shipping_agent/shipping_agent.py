import asyncio
import logging

from a2a_protocol.client import A2AClient
from a2a_protocol.models import Task, Message, TaskStatus, MessageType, AgentCard
from a2a_protocol.server import A2AServer


class ShippingAgent:
    """배송 정보를 제공하는 A2A 호환 에이전트"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Agent Card 생성
        self.agent_card = self._create_agent_card()

        # A2A 서버 및 클라이언트 초기화
        self.server = A2AServer(self.agent_card)
        self.client = A2AClient(self.agent_card.id)

        # 배송 정책 데이터 (간단한 예시용)
        self.shipping_policies = {
            "standard": {
                "name": "표준 배송",
                "price": "3,000원",
                "time": "2-3일 소요",
                "description": "일반 택배 서비스를 통해 배송됩니다."
            },
            "express": {
                "name": "빠른 배송",
                "price": "6,000원",
                "time": "다음날 배송",
                "description": "주문 당일 오후 3시 이전 결제 완료 시 다음날 도착을 보장합니다."
            },
            "same_day": {
                "name": "당일 배송",
                "price": "10,000원",
                "time": "당일 도착",
                "description": "서울 및 수도권 지역에 한해 오전 11시 이전 주문 시 당일 저녁 도착을 보장합니다."
            }
        }
        
        # 배송 상태 추적 데이터 (간단한 예시용)
        self.tracking_data = {
            "TRK123456789": {
                "order_id": "ORD-20250511-001",
                "product": "스마트폰 Pro",
                "status": "배송 완료",
                "history": [
                    {"time": "2025-05-09 14:23", "status": "주문 접수"},
                    {"time": "2025-05-10 09:15", "status": "상품 준비 중"},
                    {"time": "2025-05-10 18:30", "status": "배송 시작"},
                    {"time": "2025-05-11 13:45", "status": "배송 완료"}
                ],
                "estimated_delivery": "2025-05-11",
                "carrier": "A2A 물류",
                "recipient": "홍길동"
            },
            "TRK987654321": {
                "order_id": "ORD-20250511-002",
                "product": "노트북 Air",
                "status": "배송 중",
                "history": [
                    {"time": "2025-05-10 11:42", "status": "주문 접수"},
                    {"time": "2025-05-11 10:30", "status": "상품 준비 중"},
                    {"time": "2025-05-12 09:15", "status": "배송 시작"}
                ],
                "estimated_delivery": "2025-05-13",
                "carrier": "A2A 물류",
                "recipient": "김철수"
            },
            "TRK567890123": {
                "order_id": "ORD-20250512-001",
                "product": "스마트워치 4",
                "status": "상품 준비 중",
                "history": [
                    {"time": "2025-05-12 09:07", "status": "주문 접수"},
                    {"time": "2025-05-12 10:23", "status": "상품 준비 중"}
                ],
                "estimated_delivery": "2025-05-14",
                "carrier": "A2A 물류",
                "recipient": "이영희"
            }
        }

        # 서버 핸들러 확장
        self._extend_server_handlers()

    def _create_agent_card(self) -> AgentCard:
        """에이전트 카드 생성"""
        return AgentCard(
            id="shipping-agent",
            name="배송 정보 에이전트",
            description="배송 상태 추적, 배송 정책 안내, 예상 배송 일정을 제공하는 에이전트",
            version="1.0.0",
            base_url="http://localhost:8002/agent",
            capabilities=[
                {
                    "name": "track_shipping",
                    "description": "배송 추적 번호를 사용하여 배송 상태를 확인합니다",
                    "parameters": {
                        "tracking_number": {
                            "type": "string",
                            "description": "배송 추적 번호"
                        }
                    }
                },
                {
                    "name": "get_shipping_policy",
                    "description": "배송 정책에 대한 정보를 제공합니다",
                    "parameters": {
                        "policy_type": {
                            "type": "string",
                            "description": "특정 배송 정책 유형 (기본값: 모든 정책)",
                            "required": False
                        }
                    }
                }
            ]
        )

    def _extend_server_handlers(self):
        """서버 핸들러 확장 메서드"""

        # 원래 핸들러 참조 저장
        original_handle_new_task = self.server.handle_new_task

        # 새 작업 핸들러 오버라이드
        async def extended_handle_new_task(task: Task):
            self.logger.info(f"새 배송 정보 요청 수신: {task.id} - {task.title}")

            # 원래 핸들러 호출
            await original_handle_new_task(task)

            # 작업 자동 처리 시작
            asyncio.create_task(self.process_task(task))

        # 핸들러 교체
        self.server.handle_new_task = extended_handle_new_task

    async def startup(self):
        """에이전트 시작"""
        self.logger.info("배송 정보 에이전트 준비 완료")

    async def process_task(self, task: Task):
        """작업 처리 로직"""
        self.logger.info(f"배송 정보 요청 처리 시작: {task.id}")

        # 초기 상태 업데이트
        task.status = TaskStatus.IN_PROGRESS

        # 내용이 없는 경우 인사말 메시지 추가
        if not task.messages:
            greeting_message = Message(
                id=f"msg_greeting_{task.id}",
                type=MessageType.TEXT,
                content="안녕하세요! 배송 정보 에이전트입니다. 배송 조회나 배송 정책에 대해 문의하시겠어요?"
            )
            task.messages.append(greeting_message)
            
            # 서버 작업 상태 명시적 업데이트
            self.logger.info(f"인사말 메시지 추가: {greeting_message.id}, 메시지 수: {len(task.messages)}")
            self.server.tasks[task.id] = task
            return

        # 마지막 메시지 가져오기
        latest_message = task.messages[-1]

        # 메시지가 클라이언트로부터 온 것인지 확인
        if latest_message.id.startswith("msg_"):
            query = latest_message.content.lower()
            
            # 배송 추적 처리
            if ("배송" in query and ("조회" in query or "확인" in query or "상태" in query)) or "추적" in query:
                # 추적 번호를 찾기 위한 간단한 처리
                tracking_number = None
                for potential_tracking in ["TRK123456789", "TRK987654321", "TRK567890123"]:
                    if potential_tracking.lower() in query:
                        tracking_number = potential_tracking
                        break
                
                if tracking_number and tracking_number in self.tracking_data:
                    # 추적 데이터 제공
                    tracking_info = self.tracking_data[tracking_number]
                    response = f"📦 배송 추적 정보 ({tracking_number})\n\n"
                    response += f"주문 번호: {tracking_info['order_id']}\n"
                    response += f"상품: {tracking_info['product']}\n"
                    response += f"상태: {tracking_info['status']}\n"
                    response += f"예상 배송일: {tracking_info['estimated_delivery']}\n"
                    response += f"배송사: {tracking_info['carrier']}\n"
                    response += f"수령인: {tracking_info['recipient']}\n\n"
                    
                    response += "배송 이력:\n"
                    for entry in tracking_info['history']:
                        response += f"• {entry['time']} - {entry['status']}\n"
                else:
                    # 추적 번호가 없거나 유효하지 않은 경우
                    sample_numbers = ", ".join(self.tracking_data.keys())
                    response = "배송 추적을 위해서는 유효한 추적 번호가 필요합니다. "
                    response += f"테스트를 위해 다음의 샘플 번호를 사용해보세요: {sample_numbers}"
            
            # 배송 정책 처리
            elif "정책" in query or "비용" in query or "요금" in query or "기간" in query:
                policy_type = None
                if "표준" in query or "일반" in query:
                    policy_type = "standard"
                elif "빠른" in query or "익일" in query or "익스프레스" in query:
                    policy_type = "express"
                elif "당일" in query:
                    policy_type = "same_day"
                
                if policy_type and policy_type in self.shipping_policies:
                    # 특정 정책 정보 제공
                    policy = self.shipping_policies[policy_type]
                    response = f"📦 {policy['name']} 정책\n\n"
                    response += f"비용: {policy['price']}\n"
                    response += f"소요 시간: {policy['time']}\n"
                    response += f"상세 정보: {policy['description']}"
                else:
                    # 모든 정책 정보 제공
                    response = "📦 배송 정책 안내\n\n"
                    for policy_id, policy in self.shipping_policies.items():
                        response += f"[{policy['name']}]\n"
                        response += f"비용: {policy['price']}\n"
                        response += f"소요 시간: {policy['time']}\n"
                        response += f"상세 정보: {policy['description']}\n\n"
            
            # 기타 일반 문의
            else:
                response = "배송에 관련된 다음 서비스를 제공해 드릴 수 있습니다:\n\n"
                response += "1. 배송 추적: 배송 상태를 확인하려면 추적 번호를 알려주세요.\n"
                response += "2. 배송 정책: 표준 배송, 빠른 배송, 당일 배송 등의 정책 정보를 안내해 드립니다.\n"
                response += "3. 배송 문제 해결: 배송 지연, 분실 등의 문제 발생 시 해결 방법을 안내해 드립니다.\n\n"
                response += "어떤 도움이 필요하신가요?"
            
            # 응답 메시지 추가
            response_message = Message(
                id=f"msg_response_{task.id}_{len(task.messages)}",
                type=MessageType.TEXT,
                content=response
            )
            task.messages.append(response_message)
            
            # 작업 상태 업데이트
            if len(task.messages) >= 4:  # 간단한 예시를 위해 몇 번의 메시지 교환 후 완료로 설정
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.WAITING_FOR_INPUT
                
            # 서버 작업 상태 명시적 업데이트
            self.logger.info(f"응답 메시지 추가: {response_message.id}, 메시지 수: {len(task.messages)}")
            self.server.tasks[task.id] = task
