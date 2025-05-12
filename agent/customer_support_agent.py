import traceback
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import logging

from a2a_protocol.models import Task, Message, TaskStatus, MessageType
from a2a_protocol.client import A2AClient
from a2a_protocol.server import A2AServer
from agent.agent_card import create_agent_card
from agent.knowledge_base import get_faq_answer, get_product_info, get_troubleshooting_tip
from utils.llm_utils import generate_response, categorize_query
from config import PRODUCT_AGENT_URL, SHIPPING_AGENT_URL, BILLING_AGENT_URL


class CustomerSupportAgent:
    """A2A 프로토콜을 사용하는 고객 지원 에이전트"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Agent Card 생성
        self.agent_card = create_agent_card()

        # A2A 서버 및 클라이언트 초기화
        self.server = A2AServer(self.agent_card)
        self.client = A2AClient(self.agent_card.id)

        # 외부 에이전트 URLs
        self.external_agents = {
            "product": PRODUCT_AGENT_URL,
            "shipping": SHIPPING_AGENT_URL,
            "billing": BILLING_AGENT_URL
        }

        # 서버 핸들러 확장
        self._extend_server_handlers()

    def _extend_server_handlers(self):
        """서버 핸들러 확장 메서드"""

        # 원래 핸들러 참조 저장
        original_handle_new_task = self.server.handle_new_task

        # 새 작업 핸들러 오버라이드
        async def extended_handle_new_task(task: Task):
            self.logger.info(f"새 작업 수신: {task.id} - {task.title}")

            # 원래 핸들러 호출
            await original_handle_new_task(task)

            # 작업 자동 처리 시작
            asyncio.create_task(self.process_task(task))

        # 핸들러 교체
        self.server.handle_new_task = extended_handle_new_task

    async def startup(self):
        """에이전트 시작 및 외부 에이전트 검색"""
        for agent_type, agent_url in self.external_agents.items():
            try:
                agent_card = await self.client.discover_agent(agent_url)
                self.logger.info(f"{agent_type} 에이전트 발견: {agent_card.name}")
                # 발견된 에이전트를 타입으로 직접 저장 (ID가 아닌 agent_type을 키로 사용)
                self.client.registered_agents[agent_type] = agent_card
            except Exception as e:
                traceback.print_exc()
                self.logger.info(f"{agent_type} 에이전트는 현재 사용할 수 없습니다: {str(e)}")

    async def process_task(self, task: Task):
        """작업 처리 로직"""
        self.logger.info(f"작업 처리 시작: {task.id}")

        # 초기 상태 업데이트
        task.status = TaskStatus.IN_PROGRESS

        # 내용이 없는 경우 인사말 메시지 추가
        if not task.messages:
            greeting_message = Message(
                id=f"msg_greeting_{task.id}",
                type=MessageType.TEXT,
                content="안녕하세요! 고객 지원 에이전트입니다. 어떻게 도와드릴까요?"
            )
            task.messages.append(greeting_message)
            return

        # 마지막 메시지 가져오기
        latest_message = task.messages[-1]

        # 메시지가 클라이언트로부터 온 것인지 확인
        if latest_message.id.startswith("msg_"):
            query = latest_message.content

            # 카테고리 분류
            category = await categorize_query(query)
            self.logger.info(f"쿼리 카테고리: {category}")

            # 카테고리에 따라 처리
            if category == "general":
                # 내부 지식 베이스 검색
                answer = get_faq_answer(query)
                if not answer:
                    # LLM을 사용하여 응답 생성
                    answer = await generate_response(query)

                await self.send_response(task, answer)

            elif category == "product":
                # 제품 정보 검색 시도
                product_info = None
                for product_type in ["스마트폰", "노트북"]:
                    if product_type.lower() in query.lower():
                        product_info = get_product_info(product_type)
                        break

                if product_info:
                    await self.send_response(task, product_info)
                else:
                    # 제품 에이전트에 작업 위임
                    await self.delegate_to_product_agent(task, query)

            elif category == "shipping":
                # 배송 관련 정보가 있는지 확인
                if "배송" in query and "정책" in query:
                    shipping_policy = get_faq_answer("배송정책")
                    await self.send_response(task, shipping_policy)
                else:
                    # 배송 에이전트에 작업 위임
                    await self.delegate_to_shipping_agent(task, query)

            elif category == "billing":
                # 결제 에이전트에 작업 위임
                await self.delegate_to_billing_agent(task, query)

            else:  # "other"
                # LLM을 사용하여 일반 응답 생성
                answer = await generate_response(query)
                await self.send_response(task, answer)

    async def send_response(self, task: Task, content: str):
        """작업에 응답 메시지 추가"""
        response_message = Message(
            id=f"msg_response_{task.id}_{len(task.messages)}",
            type=MessageType.TEXT,
            content=content
        )
        task.messages.append(response_message)
        task.updated_at = response_message.created_at

    async def delegate_to_product_agent(self, task: Task, query: str):
        """제품 에이전트에 작업 위임"""
        try:
            agent_url = self.external_agents["product"]

            # 에이전트 검색이 아직 안 되었으면 검색 시도
            if "product" not in self.client.registered_agents:
                await self.client.discover_agent(agent_url)

            try:
                agent_id = self.client.registered_agents["product"].id
            except KeyError as e:
                traceback.print_exc()
                self.logger.error(f"제품 에이전트가 등록되지 않음: {str(e)}")
                await self.send_response(task, "죄송합니다. 제품 정보 서비스에 일시적인 문제가 발생했습니다. 나중에 다시 시도해주세요.")
                return

            # 새 작업 생성
            delegated_task = await self.client.create_task(
                agent_id=agent_id,
                title="제품 정보 요청",
                description=f"고객 질문: {query}",
                metadata={"original_task_id": task.id}
            )

            # 작업 위임 메시지 추가
            await self.send_response(task, "제품 전문가에게 문의를 전달했습니다. 잠시만 기다려주세요...")

            # 제품 에이전트로부터 실제 응답 받기
            try:
                # 제품 에이전트 작업 상태 확인 및 응답 받기
                max_retries = 10  # 최대 재시도 횟수 증가
                wait_time = 2  # 대기 시간 증가
                
                for attempt in range(max_retries):
                    self.logger.info(f"제품 에이전트 응답 확인 {attempt+1}/{max_retries} 시도")
                    
                    try:
                        # 작업 상태 확인
                        task_status = await self.client.get_task_status(agent_id, delegated_task.id)
                        
                        # 작업 상태 로깅
                        self.logger.info(f"제품 에이전트 작업 상태: {task_status.status}, 메시지 수: {len(task_status.messages) if task_status.messages else 0}")
                        
                        # 작업에 메시지가 있는 경우 응답 추출
                        if task_status.messages and len(task_status.messages) > 0:
                            self.logger.info(f"제품 에이전트 메시지 찾음: {len(task_status.messages)}개")
                            # 에이전트 응답 메시지 가져오기
                            for message in task_status.messages:
                                if message.content:
                                    self.logger.info(f"제품 에이전트 응답: {message.content[:30]}...")
                                    await self.send_response(task, message.content)
                                    return
                            
                            # 메시지가 있지만 내용이 없는 경우
                            if task_status.status == TaskStatus.COMPLETED:
                                await self.send_response(task, "제품 에이전트가 응답을 완료했지만 메시지 내용이 없습니다.")
                                return
                    except Exception as e:
                        self.logger.error(f"작업 상태 확인 시도 {attempt+1} 실패: {str(e)}")
                    
                    # 응답을 기다리는 동안 잠시 대기
                    await asyncio.sleep(wait_time)
                
                # 최대 재시도 횟수를 초과한 경우
                await self.send_response(task, "제품 에이전트로부터 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                traceback.print_exc()
                self.logger.error(f"제품 에이전트 응답 처리 중 오류: {str(e)}")
                await self.send_response(task, "제품 정보를 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

        except Exception as e:
            traceback.print_exc()
            error_msg = f"제품 정보 요청 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            await self.send_response(task, "죄송합니다. 제품 정보를 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")

    async def delegate_to_shipping_agent(self, task: Task, query: str):
        """배송 에이전트에 작업 위임"""
        try:
            agent_url = self.external_agents["shipping"]

            # 에이전트 검색이 아직 안 되었으면 검색 시도
            if "shipping" not in self.client.registered_agents:
                await self.client.discover_agent(agent_url)

            try:
                agent_id = self.client.registered_agents["shipping"].id
            except KeyError as e:
                traceback.print_exc()
                self.logger.error(f"배송 에이전트가 등록되지 않음: {str(e)}")
                await self.send_response(task, "죄송합니다. 배송 서비스에 일시적인 문제가 발생했습니다. 나중에 다시 시도해주세요.")
                return

            # 새 작업 생성
            delegated_task = await self.client.create_task(
                agent_id=agent_id,
                title="배송 정보 요청",
                description=f"고객 질문: {query}",
                metadata={"original_task_id": task.id}
            )

            # 작업 위임 메시지 추가
            await self.send_response(task, "배송 전문가에게 문의를 전달했습니다. 잠시만 기다려주세요...")

            # 배송 에이전트로부터 실제 응답 받기
            try:
                # 배송 에이전트 작업 상태 확인 및 응답 받기
                max_retries = 10  # 최대 재시도 횟수 증가
                wait_time = 2  # 대기 시간 증가
                
                for attempt in range(max_retries):
                    self.logger.info(f"배송 에이전트 응답 확인 {attempt+1}/{max_retries} 시도")
                    
                    try:
                        # 작업 상태 확인
                        task_status = await self.client.get_task_status(agent_id, delegated_task.id)
                        
                        # 작업 상태 로깅
                        self.logger.info(f"배송 에이전트 작업 상태: {task_status.status}, 메시지 수: {len(task_status.messages) if task_status.messages else 0}")
                        
                        # 작업에 메시지가 있는 경우 응답 추출
                        if task_status.messages and len(task_status.messages) > 0:
                            self.logger.info(f"배송 에이전트 메시지 찾음: {len(task_status.messages)}개")
                            # 에이전트 응답 메시지 가져오기
                            for message in task_status.messages:
                                if message.content:
                                    self.logger.info(f"배송 에이전트 응답: {message.content[:30]}...")
                                    await self.send_response(task, message.content)
                                    return
                            
                            # 메시지가 있지만 내용이 없는 경우
                            if task_status.status == TaskStatus.COMPLETED:
                                await self.send_response(task, "배송 에이전트가 응답을 완료했지만 메시지 내용이 없습니다.")
                                return
                    except Exception as e:
                        self.logger.error(f"작업 상태 확인 시도 {attempt+1} 실패: {str(e)}")
                    
                    # 응답을 기다리는 동안 잠시 대기
                    await asyncio.sleep(wait_time)
                
                # 최대 재시도 횟수를 초과한 경우
                await self.send_response(task, "배송 에이전트로부터 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                traceback.print_exc()
                self.logger.error(f"배송 에이전트 응답 처리 중 오류: {str(e)}")
                await self.send_response(task, "배송 정보를 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

        except Exception as e:
            traceback.print_exc()
            error_msg = f"배송 정보 요청 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            await self.send_response(task, "죄송합니다. 배송 정보를 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")

    async def delegate_to_billing_agent(self, task: Task, query: str):
        """결제 에이전트에 작업 위임"""
        try:
            agent_url = self.external_agents["billing"]

            # 에이전트 검색이 아직 안 되었으면 검색 시도
            if "billing" not in self.client.registered_agents:
                await self.client.discover_agent(agent_url)

            try:
                agent_id = self.client.registered_agents["billing"].id
            except KeyError as e:
                traceback.print_exc()
                self.logger.error(f"청구 에이전트가 등록되지 않음: {str(e)}")
                await self.send_response(task, "죄송합니다. 결제 정보 서비스에 일시적인 문제가 발생했습니다. 나중에 다시 시도해주세요.")
                return

            # 새 작업 생성
            delegated_task = await self.client.create_task(
                agent_id=agent_id,
                title="결제 정보 요청",
                description=f"고객 질문: {query}",
                metadata={"original_task_id": task.id}
            )

            # 작업 위임 메시지 추가
            await self.send_response(task, "결제 전문가에게 문의를 전달했습니다. 잠시만 기다려주세요...")

            # 청구 에이전트로부터 실제 응답 받기
            try:
                # 청구 에이전트 작업 상태 확인 및 응답 받기
                max_retries = 10  # 최대 재시도 횟수 증가
                wait_time = 2  # 대기 시간 증가
                
                for attempt in range(max_retries):
                    self.logger.info(f"청구 에이전트 응답 확인 {attempt+1}/{max_retries} 시도")
                    
                    try:
                        # 작업 상태 확인
                        task_status = await self.client.get_task_status(agent_id, delegated_task.id)
                        
                        # 작업 상태 로깅
                        self.logger.info(f"청구 에이전트 작업 상태: {task_status.status}, 메시지 수: {len(task_status.messages) if task_status.messages else 0}")
                        
                        # 작업에 메시지가 있는 경우 응답 추출
                        if task_status.messages and len(task_status.messages) > 0:
                            self.logger.info(f"청구 에이전트 메시지 찾음: {len(task_status.messages)}개")
                            # 에이전트 응답 메시지 가져오기
                            for message in task_status.messages:
                                if message.content:
                                    self.logger.info(f"청구 에이전트 응답: {message.content[:30]}...")
                                    await self.send_response(task, message.content)
                                    return
                            
                            # 메시지가 있지만 내용이 없는 경우
                            if task_status.status == TaskStatus.COMPLETED:
                                await self.send_response(task, "청구 에이전트가 응답을 완료했지만 메시지 내용이 없습니다.")
                                return
                    except Exception as e:
                        self.logger.error(f"작업 상태 확인 시도 {attempt+1} 실패: {str(e)}")
                    
                    # 응답을 기다리는 동안 잠시 대기
                    await asyncio.sleep(wait_time)
                
                # 최대 재시도 횟수를 초과한 경우
                await self.send_response(task, "청구 에이전트로부터 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                traceback.print_exc()
                self.logger.error(f"청구 에이전트 응답 처리 중 오류: {str(e)}")
                await self.send_response(task, "결제 정보를 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

        except Exception as e:
            traceback.print_exc()
            error_msg = f"결제 정보 요청 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            await self.send_response(task, "죄송합니다. 결제 정보를 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
