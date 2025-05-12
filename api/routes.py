import uuid
from typing import Dict, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from a2a_protocol.models import Task, Message, MessageType
from agent.customer_support_agent import CustomerSupportAgent


class QueryRequest(BaseModel):
    query: str
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    response: str
    task_id: str


router = APIRouter()
_customer_support_agent = None


@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """고객 질문 처리 API 엔드포인트"""
    global _customer_support_agent

    # 새 작업 ID 생성
    task_id = f"task_{uuid.uuid4().hex[:10]}"

    # 새 작업 생성
    task = Task(
        id=task_id,
        title="고객 질문",
        description=request.query,
        metadata=request.metadata or {}
    )

    # 고객 질문 메시지 추가
    query_message = Message(
        id=f"msg_query_{task_id}",
        type=MessageType.TEXT,
        content=request.query
    )
    task.messages.append(query_message)

    # 작업을 A2A 서버에 추가
    _customer_support_agent.server.tasks[task_id] = task

    # 작업 처리
    await _customer_support_agent.process_task(task)

    # 응답 메시지 가져오기
    if len(task.messages) > 1:
        response_message = task.messages[-1].content
    else:
        response_message = "응답을 생성 중입니다..."

    return QueryResponse(
        response=response_message,
        task_id=task_id
    )


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """작업 상태 조회 API 엔드포인트"""
    global _customer_support_agent

    if task_id not in _customer_support_agent.server.tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    return _customer_support_agent.server.tasks[task_id]


@router.post("/tasks/{task_id}/messages")
async def add_message(task_id: str, request: QueryRequest):
    """기존 작업에 새 메시지 추가 API 엔드포인트"""
    global _customer_support_agent

    if task_id not in _customer_support_agent.server.tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task = _customer_support_agent.server.tasks[task_id]

    # 새 메시지 추가
    message = Message(
        id=f"msg_query_{uuid.uuid4().hex[:8]}",
        type=MessageType.TEXT,
        content=request.query
    )
    task.messages.append(message)

    # 작업 처리
    await _customer_support_agent.process_task(task)

    # 응답 메시지 가져오기
    if len(task.messages) > 1:
        response_message = task.messages[-1].content
    else:
        response_message = "응답을 생성 중입니다..."

    return QueryResponse(
        response=response_message,
        task_id=task_id
    )


def init_routes(agent: CustomerSupportAgent):
    """라우터 초기화 및 에이전트 설정"""
    global _customer_support_agent
    _customer_support_agent = agent

    # A2A 프로토콜 라우터 포함
    router.include_router(agent.server.router)

    return router