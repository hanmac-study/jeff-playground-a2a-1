import logging
import asyncio
import json
from typing import Dict, List, Any, Optional

from a2a_protocol.models import Task, Message, TaskStatus, MessageType, AgentCard
from a2a_protocol.client import A2AClient
from a2a_protocol.server import A2AServer


class ProductAgent:
    """제품 정보를 제공하는 A2A 호환 에이전트"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Agent Card 생성
        self.agent_card = self._create_agent_card()

        # A2A 서버 및 클라이언트 초기화
        self.server = A2AServer(self.agent_card)
        self.client = A2AClient(self.agent_card.id)

        # 제품 데이터베이스 (간단한 예시용)
        self.products = {
            "스마트폰": {
                "name": "A2A 스마트폰 Pro",
                "price": "999,000원",
                "description": "최첨단 A2A 기술을 탑재한 프리미엄 스마트폰입니다. 인공지능 기능과 고해상도 카메라가 특징입니다.",
                "specs": {
                    "display": "6.7인치 OLED",
                    "processor": "A2A X1 칩셋",
                    "camera": "50MP 트리플 카메라",
                    "battery": "5000mAh"
                },
                "availability": "재고 있음",
                "warranty": "1년 무상 보증"
            },
            "노트북": {
                "name": "A2A 노트북 Air",
                "price": "1,599,000원",
                "description": "초경량 디자인에 강력한 성능을 갖춘 프리미엄 노트북입니다. 전문가용 소프트웨어 실행에 최적화되어 있습니다.",
                "specs": {
                    "display": "14인치 레티나 디스플레이",
                    "processor": "A2A M2 칩셋",
                    "memory": "16GB 통합 메모리",
                    "storage": "512GB SSD"
                },
                "availability": "재고 있음",
                "warranty": "1년 무상 보증"
            },
            "스마트워치": {
                "name": "A2A 워치 4",
                "price": "499,000원",
                "description": "건강 모니터링과 피트니스 기능이 강화된 최신 스마트워치입니다. 방수 기능과 긴 배터리 수명이 특징입니다.",
                "specs": {
                    "display": "1.9인치 AMOLED",
                    "sensors": "심박수, 혈중 산소, 심전도",
                    "battery": "최대 2일 사용 가능",
                    "connectivity": "블루투스 5.2, WiFi"
                },
                "availability": "재고 있음",
                "warranty": "1년 무상 보증"
            },
            "태블릿": {
                "name": "A2A 태블릿 Pro",
                "price": "899,000원",
                "description": "강력한 성능과 S펜 지원을 갖춘 크리에이티브 작업용 태블릿입니다. 선명한 디스플레이가 특징입니다.",
                "specs": {
                    "display": "11인치 Super AMOLED",
                    "processor": "A2A X1 칩셋",
                    "memory": "8GB RAM",
                    "storage": "256GB"
                },
                "availability": "재고 있음",
                "warranty": "1년 무상 보증"
            }
        }

        # 서버 핸들러 확장
        self._extend_server_handlers()

    def _create_agent_card(self) -> AgentCard:
        """에이전트 카드 생성"""
        return AgentCard(
            id="product-agent",
            name="제품 정보 에이전트",
            description="제품 상세 정보, 사양, 가격, 재고 상태 등을 제공하는 에이전트",
            version="1.0.0",
            base_url="http://localhost:8001/agent",
            capabilities=[
                {
                    "name": "get_product_info",
                    "description": "특정 제품에 대한 상세 정보를 제공합니다",
                    "parameters": {
                        "product_name": {
                            "type": "string",
                            "description": "정보를 원하는 제품명"
                        }
                    }
                },
                {
                    "name": "check_availability",
                    "description": "제품의 재고 상태를 확인합니다",
                    "parameters": {
                        "product_name": {
                            "type": "string",
                            "description": "재고를 확인할 제품명"
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
            self.logger.info(f"새 제품 정보 요청 수신: {task.id} - {task.title}")

            # 원래 핸들러 호출
            await original_handle_new_task(task)

            # 작업 자동 처리 시작
            asyncio.create_task(self.process_task(task))

        # 핸들러 교체
        self.server.handle_new_task = extended_handle_new_task

    async def startup(self):
        """에이전트 시작"""
        self.logger.info("제품 정보 에이전트 준비 완료")

    async def process_task(self, task: Task):
        """작업 처리 로직"""
        self.logger.info(f"제품 정보 요청 처리 시작: {task.id}")

        # 초기 상태 업데이트
        task.status = TaskStatus.IN_PROGRESS

        # 내용이 없는 경우 인사말 메시지 추가
        if not task.messages:
            greeting_message = Message(
                id=f"msg_greeting_{task.id}",
                type=MessageType.TEXT,
                content="안녕하세요! 제품 정보 에이전트입니다. 어떤 제품에 대해 알고 싶으신가요?"
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
            
            # 제품명 추출
            product_keywords = {
                "스마트폰": ["스마트폰", "휴대폰", "폰", "모바일"],
                "노트북": ["노트북", "랩탑", "컴퓨터"],
                "스마트워치": ["스마트워치", "워치", "시계"],
                "태블릿": ["태블릿", "패드", "탭"]
            }
            
            found_product = None
            for product_name, keywords in product_keywords.items():
                if any(keyword in query for keyword in keywords):
                    found_product = product_name
                    break
            
            if found_product and found_product in self.products:
                # 제품 정보 응답
                product_info = self.products[found_product]
                
                # 정보 유형 결정
                if "가격" in query:
                    response = f"{found_product} {product_info['name']}의 가격은 {product_info['price']}입니다."
                elif "사양" in query or "스펙" in query:
                    specs = product_info['specs']
                    specs_text = "\n".join([f"- {key}: {value}" for key, value in specs.items()])
                    response = f"{found_product} {product_info['name']}의 사양:\n{specs_text}"
                elif "재고" in query or "구매" in query or "구입" in query:
                    response = f"{found_product} {product_info['name']}은(는) {product_info['availability']}입니다."
                elif "보증" in query or "as" in query or "a/s" in query:
                    response = f"{found_product} {product_info['name']}의 보증 정책: {product_info['warranty']}"
                else:
                    # 일반 정보
                    response = f"{found_product} {product_info['name']}:\n"
                    response += f"가격: {product_info['price']}\n"
                    response += f"설명: {product_info['description']}\n"
                    response += f"재고: {product_info['availability']}\n"
                    response += f"보증: {product_info['warranty']}"
            else:
                # 제품을 찾지 못함
                available_products = ", ".join(self.products.keys())
                response = f"죄송합니다. 요청하신 제품을 찾을 수 없습니다. 현재 정보를 제공할 수 있는 제품은 다음과 같습니다: {available_products}"
            
            # 응답 메시지 추가
            response_message = Message(
                id=f"msg_response_{task.id}_{len(task.messages)}",
                type=MessageType.TEXT,
                content=response
            )
            task.messages.append(response_message)
            
            # 작업 완료로 상태 업데이트
            if len(task.messages) >= 4:  # 간단한 예시를 위해 몇 번의 메시지 교환 후 완료
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.WAITING_FOR_INPUT
