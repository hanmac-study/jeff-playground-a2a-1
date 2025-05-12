import traceback
import uuid
from typing import Dict, Optional, Any

import httpx

from a2a_protocol.models import Task, Message, MessageType, AgentCard


class A2AClient:
    """A2A 프로토콜을 사용하여 다른 에이전트와 통신하는 클라이언트"""

    def __init__(self, agent_id: str, base_url: Optional[str] = None):
        self.agent_id = agent_id
        self.base_url = base_url
        self.registered_agents: Dict[str, AgentCard] = {}

    async def discover_agent(self, agent_url: str) -> AgentCard:
        """에이전트 카드를 검색하여 에이전트 정보 확인"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{agent_url}/.well-known/agent.json")
                response.raise_for_status()
                agent_card = AgentCard.model_validate(response.json())
                self.registered_agents[agent_card.id] = agent_card
                return agent_card
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"에이전트 발견 오류: {str(e)}")

    async def create_task(self, agent_id: str, title: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> Task:
        """다른 에이전트에게 새 작업 생성 요청"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"등록되지 않은 에이전트: {agent_id}")

        agent_card = self.registered_agents[agent_id]
        task_id = f"task_{uuid.uuid4().hex[:10]}"

        task_data = {
            "id": task_id,
            "title": title,
            "description": description,
            "metadata": metadata or {}
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{agent_card.base_url}/a2a/tasks",
                    json=task_data
                )
                response.raise_for_status()
                return Task.model_validate(response.json())
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"작업 생성 오류: {str(e)}")

    async def send_message(self, agent_id: str, task_id: str, content: str, message_type: MessageType = MessageType.TEXT) -> Message:
        """기존 작업에 새 메시지 전송"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"등록되지 않은 에이전트: {agent_id}")

        agent_card = self.registered_agents[agent_id]
        message_id = f"msg_{uuid.uuid4().hex[:10]}"

        message_data = {
            "id": message_id,
            "type": message_type,
            "content": content
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{agent_card.base_url}/a2a/tasks/{task_id}/messages",
                    json=message_data
                )
                response.raise_for_status()
                return Message.model_validate(response.json())
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"메시지 전송 오류: {str(e)}")

    async def get_task_status(self, agent_id: str, task_id: str) -> Task:
        """작업 상태 확인"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"등록되지 않은 에이전트: {agent_id}")

        agent_card = self.registered_agents[agent_id]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{agent_card.base_url}/a2a/tasks/{task_id}"
                )
                response.raise_for_status()
                return Task.model_validate(response.json())
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"작업 상태 확인 오류: {str(e)}")
