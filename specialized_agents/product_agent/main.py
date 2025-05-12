import logging
import os
from contextlib import asynccontextmanager
import uuid
from datetime import datetime, timezone
import asyncio
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from product_agent import ProductAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# 전역 변수로 에이전트 선언
agent = None

# TaskStatus Enum
class TaskStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# MessageType Enum
class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

# Task 모델
class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict
    messages: list = []

# Message 모델
class Message(BaseModel):
    id: str
    type: MessageType
    content: str
    created_at: datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프스팸 관리를 위한 비동기 컨텍스트 매니저"""
    # 시작 시 실행 (startup)
    global agent
    logger.info("제품 정보 에이전트 시작 중...")
    
    # 제품 에이전트 인스턴스 생성
    agent = ProductAgent()
    
    # 에이전트 시작
    await agent.startup()
    
    logger.info(f"제품 정보 에이전트가 http://localhost:8001에서 실행 중입니다")
    
    yield  # 여기서 FastAPI 애플리케이션 실행
    
    # 종료 시 실행 (shutdown)
    # 필요한 정리 작업이 있다면 여기에 추가


app = FastAPI(
    title="제품 정보 에이전트",
    description="제품 정보를 제공하는 A2A 프로토콜 호환 에이전트",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A2A 프로토콜 엔드포인트 설정
@app.get("/agent/.well-known/agent.json")
async def agent_card():
    """에이전트 카드 반환"""
    return agent.agent_card.dict()

@app.post("/agent/a2a/tasks")
async def create_task(task_data: dict):
    """새 작업 생성"""
    task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:10]}")
    
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
    
    # 작업 저장 및 핸들러 호출
    agent.server.tasks[task_id] = task
    
    # 기존 메시지가 있으면 삭제하지 않도록 유지 (추가)
    if hasattr(agent.server.tasks[task_id], 'messages') and agent.server.tasks[task_id].messages:
        # 기존 메시지 유지
        task.messages = agent.server.tasks[task_id].messages
    
    asyncio.create_task(agent.server.handle_new_task(task))
    
    return task

@app.get("/agent/a2a/tasks/{task_id}")
async def get_task(task_id: str):
    """작업 정보 조회"""
    if task_id not in agent.server.tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    return agent.server.tasks[task_id]

@app.post("/agent/a2a/tasks/{task_id}/messages")
async def send_message(task_id: str, message_data: dict):
    """메시지 전송"""
    if task_id not in agent.server.tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task = agent.server.tasks[task_id]
    
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
    
    # 메시지 핸들러 호출 전에 작업 상태 확인 및 로깅 (추가)
    logging.info(f"메시지 추가 후 작업 상태: {task.id}, 메시지 수: {len(task.messages)}")
    for idx, msg in enumerate(task.messages):
        logging.info(f"  메시지 {idx}: {msg.id}, 콘텐츠: {msg.content[:30]}...")
    
    # 서버 작업 상태 명시적 업데이트 (추가)
    agent.server.tasks[task_id] = task
    
    # 메시지 핸들러 호출
    asyncio.create_task(agent.server.handle_new_message(task, message))
    
    return message


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
