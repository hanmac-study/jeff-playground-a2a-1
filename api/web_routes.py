"""
Jinja2 기반 웹 인터페이스를 위한 라우트 모듈
"""
import json
import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

from a2a_protocol.models import Task, Message, MessageType, TaskStatus
from agent.customer_support_agent import CustomerSupportAgent
from utils.db import db

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="templates")

# 웹 라우터 생성
web_router = APIRouter()

# 글로벌 변수로 에이전트 참조
agent: Optional[CustomerSupportAgent] = None

def get_agent() -> CustomerSupportAgent:
    """고객 지원 에이전트 인스턴스 반환"""
    global agent
    if agent is None:
        raise HTTPException(status_code=500, detail="에이전트가 초기화되지 않았습니다")
    return agent

def set_agent(support_agent: CustomerSupportAgent):
    """전역 에이전트 설정"""
    global agent
    agent = support_agent

# 홈 페이지
@web_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # 최근 작업 가져오기
    recent_tasks = db.get_recent_tasks(5)
    
    # 등록된 에이전트 가져오기
    agents = db.get_all_agents()
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "recent_tasks": recent_tasks,
            "agents": agents
        }
    )

# 에이전트 목록 페이지
@web_router.get("/agents", response_class=HTMLResponse)
async def list_agents(request: Request):
    agents = db.get_all_agents()
    return templates.TemplateResponse(
        "agents.html", 
        {
            "request": request, 
            "agents": agents
        }
    )

# 에이전트 상세 정보 페이지
@web_router.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_id: str):
    # 에이전트 정보 가져오기
    agent_data = db.get_agent_by_id(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다")
    
    # 에이전트의 작업 목록 가져오기
    tasks = db.get_tasks_by_agent(agent_id)
    
    return templates.TemplateResponse(
        "agent_detail.html", 
        {
            "request": request, 
            "agent": agent_data,
            "tasks": tasks
        }
    )

# 에이전트 등록 페이지
@web_router.get("/agents/register", response_class=HTMLResponse)
async def register_agent_form(request: Request):
    return templates.TemplateResponse("agent_register.html", {"request": request})

# 에이전트 등록 처리
@web_router.post("/agents/register")
async def register_agent(
    request: Request,
    agent_url: str = Form(...),
    save_to_db: bool = Form(True)
):
    try:
        # 고객 지원 에이전트 인스턴스 가져오기
        support_agent = get_agent()
        
        # 에이전트 발견 시도
        client = support_agent.client
        agent_card = await client.discover_agent(agent_url)
        
        # 데이터베이스에 저장
        if save_to_db:
            agent_data = agent_card.model_dump()
            db.save_agent(agent_data)
        
        return RedirectResponse(url=f"/agents/{agent_card.id}", status_code=HTTP_302_FOUND)
    
    except Exception as e:
        traceback.print_exc()
        return templates.TemplateResponse(
            "agent_register.html", 
            {
                "request": request,
                "error": f"에이전트 등록 실패: {str(e)}",
                "agent_url": agent_url
            }
        )

# 작업 목록 페이지
@web_router.get("/tasks", response_class=HTMLResponse)
async def list_tasks(
    request: Request, 
    agent_id: Optional[str] = None,
    status: Optional[str] = None
):
    # 에이전트 목록 가져오기
    agents = db.get_all_agents()
    
    # 필터링된 작업 가져오기
    if agent_id and status:
        # SQL 쿼리 작성 - agent_id와 status로 필터링
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE t.agent_id = ? AND t.status = ?
        ORDER BY t.updated_at DESC
        """
        tasks = db.execute_query(query, (agent_id, status))
    elif agent_id:
        # agent_id만으로 필터링
        tasks = db.get_tasks_by_agent(agent_id)
    elif status:
        # status만으로 필터링
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE t.status = ?
        ORDER BY t.updated_at DESC
        """
        tasks = db.execute_query(query, (status,))
    else:
        # 필터 없이 모든 작업 가져오기
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        ORDER BY t.updated_at DESC
        """
        tasks = db.execute_query(query)
    
    # 메타데이터 파싱
    for task in tasks:
        if 'metadata' in task and task['metadata']:
            try:
                task['metadata'] = json.loads(task['metadata'])
            except:
                task['metadata'] = {}
    
    # 선택된 에이전트 이름 가져오기
    agent_name = None
    if agent_id:
        agent_data = db.get_agent_by_id(agent_id)
        if agent_data:
            agent_name = agent_data['name']
    
    return templates.TemplateResponse(
        "tasks.html", 
        {
            "request": request, 
            "tasks": tasks,
            "agents": agents,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "status": status
        }
    )

# 작업 상세 정보 페이지
@web_router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, task_id: str):
    # 작업 정보 가져오기
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    return templates.TemplateResponse(
        "task_detail.html", 
        {
            "request": request, 
            "task": task
        }
    )

# 작업 상태 업데이트
@web_router.post("/tasks/{task_id}/status")
async def update_task_status(task_id: str, status: str = Form(...)):
    # 작업 정보 가져오기
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    # 상태 업데이트
    try:
        new_status = TaskStatus(status)
        task['status'] = new_status
        db.save_task(task)
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=HTTP_302_FOUND)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 작업 상태입니다")

# 작업에 메시지 추가
@web_router.post("/tasks/{task_id}/messages")
async def add_message_to_task(
    task_id: str, 
    message: str = Form(...),
    support_agent: CustomerSupportAgent = Depends(get_agent)
):
    # 작업 정보 가져오기
    task_data = db.get_task_by_id(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    # 메시지 생성
    message_id = f"msg_{uuid.uuid4().hex[:10]}"
    message_data = {
        "id": message_id,
        "task_id": task_id,
        "type": "text",
        "content": message
    }
    
    # 데이터베이스에 메시지 저장
    db.save_message(message_data)
    
    # 작업 상태 업데이트
    task_data['status'] = 'in_progress'
    db.save_task(task_data)
    
    # A2A 프로토콜 모델로 변환
    task_model = Task(
        id=task_data['id'],
        title=task_data['title'],
        description=task_data['description'],
        status=TaskStatus(task_data['status']),
        metadata=task_data['metadata']
    )
    
    # 메시지 목록 구성
    for msg in task_data['messages']:
        task_model.messages.append(Message(
            id=msg['id'],
            type=MessageType(msg['type']),
            content=msg['content'],
            created_at=datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
        ))
    
    # 에이전트 처리 시작
    await support_agent.process_task(task_model)
    
    # 다시 작업 상세 페이지로 리디렉션
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=HTTP_302_FOUND)

# 채팅 인터페이스
@web_router.get("/chat", response_class=HTMLResponse)
async def chat_interface(
    request: Request,
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    support_agent: CustomerSupportAgent = Depends(get_agent)
):
    # 모든 에이전트 가져오기
    agents = db.get_all_agents()
    
    # 선택된 에이전트 (기본값: 고객 지원 에이전트)
    selected_agent_id = agent_id or support_agent.agent_card.id
    selected_agent = db.get_agent_by_id(selected_agent_id)
    
    # 작업 정보 가져오기
    task = None
    if task_id:
        task = db.get_task_by_id(task_id)
    
    return templates.TemplateResponse(
        "chat.html", 
        {
            "request": request,
            "agents": agents,
            "selected_agent_id": selected_agent_id,
            "selected_agent": selected_agent,
            "task": task
        }
    )

# 채팅 메시지 전송
@web_router.post("/chat/send")
async def send_chat_message(
    request: Request,
    message: str = Form(...),
    task_id: Optional[str] = Form(None),
    support_agent: CustomerSupportAgent = Depends(get_agent)
):
    # 작업 정보 가져오기 또는 새 작업 생성
    task_data = None
    if task_id:
        task_data = db.get_task_by_id(task_id)
    
    if not task_data:
        # 새 작업 ID 생성
        new_task_id = f"task_{uuid.uuid4().hex[:10]}"
        
        # 새 작업 생성
        task_data = {
            "id": new_task_id,
            "title": "고객 문의",
            "description": "웹 인터페이스에서 시작된 고객 문의",
            "status": "in_progress",
            "agent_id": support_agent.agent_card.id,
            "metadata": {}
        }
        
        # 데이터베이스에 작업 저장
        db.save_task(task_data)
        
        # 작업 ID 업데이트
        task_id = new_task_id
    
    # 메시지 생성
    message_id = f"msg_{uuid.uuid4().hex[:10]}"
    message_data = {
        "id": message_id,
        "task_id": task_id,
        "type": "text",
        "content": message
    }
    
    # 데이터베이스에 메시지 저장
    db.save_message(message_data)
    
    # 작업 상태 업데이트
    task_data['status'] = 'in_progress'
    db.save_task(task_data)
    
    # A2A 프로토콜 모델로 변환
    task_model = Task(
        id=task_data['id'],
        title=task_data['title'],
        description=task_data['description'],
        status=TaskStatus(task_data['status']),
        metadata=task_data['metadata']
    )
    
    # 메시지 목록 구성
    messages = db.get_messages_by_task(task_id)
    for msg in messages:
        task_model.messages.append(Message(
            id=msg['id'],
            type=MessageType(msg['type']),
            content=msg['content'],
            created_at=datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
        ))
    
    # 에이전트 처리 시작
    await support_agent.process_task(task_model)
    
    # 응답 메시지 가져오기 및 DB에 저장
    if task_model.messages and len(task_model.messages) > len(messages):
        for new_msg in task_model.messages[len(messages):]:
            response_data = {
                "id": new_msg.id,
                "task_id": task_id,
                "type": new_msg.type,
                "content": new_msg.content
            }
            db.save_message(response_data)
    
    # 다시 채팅 인터페이스로 리디렉션
    return RedirectResponse(url=f"/chat?task_id={task_id}", status_code=HTTP_302_FOUND)

# 작업 생성 페이지
@web_router.get("/tasks/create", response_class=HTMLResponse)
async def create_task_form(request: Request):
    # 에이전트 목록 가져오기
    agents = db.get_all_agents()
    
    return templates.TemplateResponse(
        "task_create.html", 
        {
            "request": request,
            "agents": agents
        }
    )

# 작업 생성 처리
@web_router.post("/tasks/create")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    agent_id: str = Form(...),
    initial_message: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    support_agent: CustomerSupportAgent = Depends(get_agent)
):
    try:
        # 에이전트 확인
        agent_data = db.get_agent_by_id(agent_id)
        if not agent_data:
            raise ValueError("선택한 에이전트를 찾을 수 없습니다")
        
        # 메타데이터 파싱
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                if not isinstance(metadata_dict, dict):
                    raise ValueError("메타데이터는 JSON 객체 형식이어야 합니다")
            except json.JSONDecodeError:
                return templates.TemplateResponse(
                    "task_create.html", 
                    {
                        "request": request,
                        "agents": db.get_all_agents(),
                        "error": "메타데이터가 유효한 JSON 형식이 아닙니다"
                    }
                )
        
        # 새 작업 ID 생성
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        
        # 작업 생성
        task_data = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "created",
            "agent_id": agent_id,
            "metadata": metadata_dict
        }
        
        # 데이터베이스에 작업 저장
        db.save_task(task_data)
        
        # 초기 메시지가 있는 경우 추가
        if initial_message and initial_message.strip():
            message_id = f"msg_{uuid.uuid4().hex[:10]}"
            message_data = {
                "id": message_id,
                "task_id": task_id,
                "type": "text",
                "content": initial_message
            }
            
            # 데이터베이스에 메시지 저장
            db.save_message(message_data)
            
            # 작업 상태 업데이트
            task_data['status'] = 'in_progress'
            db.save_task(task_data)
            
            # A2A 프로토콜 모델로 변환
            task_model = Task(
                id=task_data['id'],
                title=task_data['title'],
                description=task_data['description'],
                status=TaskStatus(task_data['status']),
                metadata=task_data['metadata']
            )
            
            # 메시지 추가
            task_model.messages.append(Message(
                id=message_id,
                type=MessageType.TEXT,
                content=initial_message,
                created_at=datetime.now()
            ))
            
            # 에이전트 처리 시작
            await support_agent.process_task(task_model)
        
        # 작업 상세 페이지로 리디렉션
        return RedirectResponse(url=f"/tasks/{task_id}", status_code=HTTP_302_FOUND)
    
    except ValueError as e:
        return templates.TemplateResponse(
            "task_create.html", 
            {
                "request": request,
                "agents": db.get_all_agents(),
                "error": str(e)
            }
        )
    
    except Exception as e:
        traceback.print_exc()
        return templates.TemplateResponse(
            "task_create.html", 
            {
                "request": request,
                "agents": db.get_all_agents(),
                "error": f"작업 생성 실패: {str(e)}"
            }
        )

# 웹 인터페이스 초기화 함수
def init_web_routes(support_agent: CustomerSupportAgent) -> APIRouter:
    """웹 인터페이스용 라우트 초기화"""
    # 에이전트 설정
    set_agent(support_agent)
    
    # 에이전트 카드 데이터베이스에 저장
    agent_data = support_agent.agent_card.model_dump()
    db.save_agent(agent_data)
    
    return web_router
