import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from a2a_protocol.models import Task, Message, TaskStatus, MessageType, AgentCard
from a2a_protocol.client import A2AClient
from a2a_protocol.server import A2AServer


class BillingAgent:
    """결제 및 청구 정보를 제공하는 A2A 호환 에이전트"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Agent Card 생성
        self.agent_card = self._create_agent_card()

        # A2A 서버 및 클라이언트 초기화
        self.server = A2AServer(self.agent_card)
        self.client = A2AClient(self.agent_card.id)

        # 결제 방법 데이터 (간단한 예시용)
        self.payment_methods = {
            "credit_card": {
                "name": "신용카드",
                "description": "국내외 모든 신용카드로 결제 가능합니다.",
                "discount": "0-5% (카드사별 상이)",
                "limit": "한도 없음"
            },
            "bank_transfer": {
                "name": "계좌이체",
                "description": "실시간 계좌이체로 즉시 결제됩니다.",
                "discount": "2%",
                "limit": "한도 없음"
            },
            "mobile_pay": {
                "name": "모바일 결제",
                "description": "카카오페이, 토스, 페이코 등의 간편결제를 지원합니다.",
                "discount": "1-3%",
                "limit": "일 100만원 한도"
            }
        }
        
        # 주문 및 결제 내역 (간단한 예시용)
        self.order_history = {
            "ORD-20250511-001": {
                "customer_id": "CUST001",
                "product": "스마트폰 Pro",
                "amount": 999000,
                "payment_method": "신용카드",
                "payment_status": "결제 완료",
                "payment_date": "2025-05-09 14:23",
                "invoice_number": "INV-20250509-001",
                "refund_status": None
            },
            "ORD-20250511-002": {
                "customer_id": "CUST002",
                "product": "노트북 Air",
                "amount": 1599000,
                "payment_method": "모바일 결제",
                "payment_status": "결제 완료",
                "payment_date": "2025-05-10 11:42",
                "invoice_number": "INV-20250510-001",
                "refund_status": None
            },
            "ORD-20250512-001": {
                "customer_id": "CUST003",
                "product": "스마트워치 4",
                "amount": 499000,
                "payment_method": "계좌이체",
                "payment_status": "결제 완료",
                "payment_date": "2025-05-12 09:07",
                "invoice_number": "INV-20250512-001",
                "refund_status": None
            },
            "ORD-20250501-001": {
                "customer_id": "CUST004",
                "product": "스마트폰 Pro",
                "amount": 999000,
                "payment_method": "신용카드",
                "payment_status": "환불 완료",
                "payment_date": "2025-05-01 10:15",
                "invoice_number": "INV-20250501-001",
                "refund_status": {
                    "status": "환불 완료",
                    "reason": "고객 변심",
                    "refund_date": "2025-05-03 15:30",
                    "refund_amount": 999000
                }
            }
        }

        # 서버 핸들러 확장
        self._extend_server_handlers()

    def _create_agent_card(self) -> AgentCard:
        """에이전트 카드 생성"""
        return AgentCard(
            id="billing-agent",
            name="결제 및 청구 에이전트",
            description="결제 처리, 청구서 조회, 환불 정책을 제공하는 에이전트",
            version="1.0.0",
            base_url="http://localhost:8003/agent",
            capabilities=[
                {
                    "name": "check_order",
                    "description": "주문 번호로 결제 정보를 조회합니다",
                    "parameters": {
                        "order_id": {
                            "type": "string",
                            "description": "조회할 주문 번호"
                        }
                    }
                },
                {
                    "name": "get_payment_methods",
                    "description": "사용 가능한 결제 수단 정보를 제공합니다",
                    "parameters": {}
                },
                {
                    "name": "refund_policy",
                    "description": "환불 정책에 대한 정보를 제공합니다",
                    "parameters": {}
                }
            ]
        )

    def _extend_server_handlers(self):
        """서버 핸들러 확장 메서드"""

        # 원래 핸들러 참조 저장
        original_handle_new_task = self.server.handle_new_task

        # 새 작업 핸들러 오버라이드
        async def extended_handle_new_task(task: Task):
            self.logger.info(f"새 결제/청구 정보 요청 수신: {task.id} - {task.title}")

            # 원래 핸들러 호출
            await original_handle_new_task(task)

            # 작업 자동 처리 시작
            asyncio.create_task(self.process_task(task))

        # 핸들러 교체
        self.server.handle_new_task = extended_handle_new_task

    async def startup(self):
        """에이전트 시작"""
        self.logger.info("결제 및 청구 에이전트 준비 완료")

    async def process_task(self, task: Task):
        """작업 처리 로직"""
        self.logger.info(f"결제/청구 정보 요청 처리 시작: {task.id}")

        # 초기 상태 업데이트
        task.status = TaskStatus.IN_PROGRESS

        # 내용이 없는 경우 인사말 메시지 추가
        if not task.messages:
            greeting_message = Message(
                id=f"msg_greeting_{task.id}",
                type=MessageType.TEXT,
                content="안녕하세요! 결제 및 청구 에이전트입니다. 결제 방법, 주문 내역 조회, 환불 정책 등에 대해 문의하실 수 있습니다."
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
            
            # 주문 내역 조회 처리
            if ("주문" in query and ("조회" in query or "확인" in query or "내역" in query)) or "결제 내역" in query:
                # 주문 번호를 찾기 위한 간단한 처리
                order_id = None
                for potential_order in self.order_history.keys():
                    if potential_order.lower() in query:
                        order_id = potential_order
                        break
                
                if order_id and order_id in self.order_history:
                    # 주문 내역 제공
                    order_info = self.order_history[order_id]
                    response = f"💰 주문 내역 ({order_id})\n\n"
                    response += f"상품: {order_info['product']}\n"
                    response += f"금액: {order_info['amount']:,}원\n"
                    response += f"결제 수단: {order_info['payment_method']}\n"
                    response += f"결제 상태: {order_info['payment_status']}\n"
                    response += f"결제일: {order_info['payment_date']}\n"
                    response += f"청구서 번호: {order_info['invoice_number']}\n"
                    
                    if order_info['refund_status']:
                        refund = order_info['refund_status']
                        response += f"\n환불 정보:\n"
                        response += f"상태: {refund['status']}\n"
                        response += f"사유: {refund['reason']}\n"
                        response += f"환불일: {refund['refund_date']}\n"
                        response += f"환불 금액: {refund['refund_amount']:,}원"
                else:
                    # 주문 번호가 없거나 유효하지 않은 경우
                    sample_orders = ", ".join(self.order_history.keys())
                    response = "주문 내역을 조회하기 위해서는 유효한 주문 번호가 필요합니다. "
                    response += f"테스트를 위해 다음의 샘플 주문 번호를 사용해보세요: {sample_orders}"
            
            # 결제 방법 처리
            elif "결제" in query and ("방법" in query or "수단" in query):
                payment_type = None
                if "카드" in query or "신용" in query:
                    payment_type = "credit_card"
                elif "계좌" in query or "이체" in query:
                    payment_type = "bank_transfer"
                elif "모바일" in query or "간편" in query:
                    payment_type = "mobile_pay"
                
                if payment_type and payment_type in self.payment_methods:
                    # 특정 결제 방법 정보 제공
                    payment = self.payment_methods[payment_type]
                    response = f"💳 {payment['name']} 결제 정보\n\n"
                    response += f"설명: {payment['description']}\n"
                    response += f"할인율: {payment['discount']}\n"
                    response += f"한도: {payment['limit']}"
                else:
                    # 모든 결제 방법 정보 제공
                    response = "💳 사용 가능한 결제 수단 안내\n\n"
                    for payment_id, payment in self.payment_methods.items():
                        response += f"[{payment['name']}]\n"
                        response += f"설명: {payment['description']}\n"
                        response += f"할인율: {payment['discount']}\n"
                        response += f"한도: {payment['limit']}\n\n"
            
            # 환불 정책 처리
            elif "환불" in query or "취소" in query or "반품" in query:
                response = "🔄 환불 정책 안내\n\n"
                response += "1. 단순 변심에 의한 환불\n"
                response += "   - 제품 수령 후 7일 이내에 환불 신청 가능\n"
                response += "   - 제품이 미개봉 상태여야 함\n"
                response += "   - 배송비는 고객 부담\n\n"
                response += "2. 제품 하자에 의한 환불\n"
                response += "   - 제품 수령 후 14일 이내에 환불 신청 가능\n"
                response += "   - 제품 결함 증빙 자료 제출 필요\n"
                response += "   - 배송비는 판매자 부담\n\n"
                response += "3. 환불 처리 기간\n"
                response += "   - 환불 승인 후 3-5 영업일 이내 처리\n"
                response += "   - 결제 수단에 따라 환불 기간이 다를 수 있음\n\n"
                response += "환불에 대한 자세한 문의는 고객센터(1234-5678)로 연락주세요."
            
            # 기타 일반 문의
            else:
                response = "결제 및 청구와 관련된 다음 서비스를 제공해 드릴 수 있습니다:\n\n"
                response += "1. 주문 내역 조회: 주문 번호를 알려주시면 결제 상태를 확인해 드립니다.\n"
                response += "2. 결제 방법 안내: 신용카드, 계좌이체, 모바일 결제 등의 정보를 안내해 드립니다.\n"
                response += "3. 환불 정책: 환불 신청 방법과 처리 기간 등을 안내해 드립니다.\n\n"
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
