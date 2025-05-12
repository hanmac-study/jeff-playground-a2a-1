from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


class Message(BaseModel):
    id: str
    type: MessageType = MessageType.TEXT
    content: Union[str, Dict[str, Any]]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123456",
                "type": "text",
                "content": "안녕하세요, 어떻게 도와드릴까요?",
                "created_at": "2025-05-12T12:00:00Z"
            }
        }


class TaskStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[Message] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "task_123456",
                "title": "고객 문의 처리",
                "description": "제품 배송 상태에 대한 문의",
                "status": "in_progress",
                "created_at": "2025-05-12T12:00:00Z",
                "updated_at": "2025-05-12T12:05:00Z",
                "messages": [],
                "metadata": {"customer_id": "cust_987654"}
            }
        }


class AgentCapability(BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class AgentCard(BaseModel):
    id: str
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability] = []
    base_url: str
    auth_required: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "customer-support-agent",
                "name": "고객 지원 에이전트",
                "description": "고객 질문에 답변하고 필요시 다른 전문 에이전트와 통신하는 A2A 호환 에이전트",
                "version": "1.0.0",
                "capabilities": [
                    {
                        "name": "answer_product_questions",
                        "description": "제품 관련 질문에 답변"
                    },
                    {
                        "name": "track_shipping",
                        "description": "배송 추적 정보 제공",
                        "parameters": {
                            "order_id": "주문 번호"
                        }
                    }
                ],
                "base_url": "http://localhost:8000",
                "auth_required": False
            }
        }


class Artifact(BaseModel):
    id: str
    type: str
    content: Any
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
