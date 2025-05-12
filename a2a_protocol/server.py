import uuid
from datetime import datetime, timezone
from typing import Dict, Callable, Awaitable

from fastapi import APIRouter, HTTPException

from a2a_protocol.models import Task, Message, TaskStatus, AgentCard, MessageType


class A2AServer:
    """A2A 프로토콜 서버 구현"""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.tasks: Dict[str, Task] = {}
        self.message_handlers: Dict[str, Callable[[Task, Message], Awaitable[None]]] = {}
        self.router = APIRouter(prefix="/a2a")

        # 라우트 설정
        self.setup_routes()

    def setup_routes(self):
        """API 라우트 설정"""

        @self.router.get("/.well-known/agent.json")
        async def get_agent_card():
            return self.agent_card.model_dump()

        @self.router.post("/tasks", response_model=Task)
        async def create_task(task_data: dict):
            task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:10]}")

            # 이미 존재하는 작업인지 확인
            if task_id in self.tasks:
                raise HTTPException(status_code=409, detail="작업 ID가 이미 존재합니다")

            # 새 작업 생성
            task = Task(
                id=task_id,
                title=task_data.get("title", "새 작업"),
                description=task_data.get("description", ""),
                status=TaskStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                metadata=task_data.get("metadata", {})
            )

            self.tasks[task_id] = task

            # 새 작업 생성에 대한 핸들러 호출
            await self.handle_new_task(task)

            return task

        @self.router.get("/tasks/{task_id}", response_model=Task)
        async def get_task(task_id: str):
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

            return self.tasks[task_id]

        @self.router.post("/tasks/{task_id}/messages", response_model=Message)
        async def add_message(task_id: str, message_data: dict):
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

            task = self.tasks[task_id]

            # 새 메시지 생성
            message_id = message_data.get("id", f"msg_{uuid.uuid4().hex[:10]}")
            message = Message(
                id=message_id,
                type=message_data.get("type", MessageType.TEXT),
                content=message_data.get("content", ""),
                created_at=datetime.now(timezone.utc)
            )

            # 작업에 메시지 추가
            task.messages.append(message)
            task.updated_at = datetime.now(timezone.utc)
            task.status = TaskStatus.IN_PROGRESS

            # 메시지 핸들러 호출
            await self.handle_new_message(task, message)

            return message

        @self.router.put("/tasks/{task_id}", response_model=Task)
        async def update_task(task_id: str, task_update: dict):
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

            task = self.tasks[task_id]

            # 상태 업데이트
            if "status" in task_update:
                task.status = TaskStatus(task_update["status"])

            task.updated_at = datetime.now(timezone.utc)

            return task

    async def handle_new_task(self, task: Task):
        """새 작업 생성 시 호출되는 핸들러"""
        # 하위 클래스에서 구현
        pass

    async def handle_new_message(self, task: Task, message: Message):
        """새 메시지 수신 시 호출되는 핸들러"""
        # 특정 작업 ID에 대한 핸들러가 있는지 확인
        if task.id in self.message_handlers:
            await self.message_handlers[task.id](task, message)

    def register_message_handler(self, task_id: str, handler: Callable[[Task, Message], Awaitable[None]]):
        """특정 작업에 대한 메시지 핸들러 등록"""
        self.message_handlers[task_id] = handler
