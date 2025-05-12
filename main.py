import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent.customer_support_agent import CustomerSupportAgent
from api.routes import init_routes
from api.web_routes import init_web_routes
from config import SERVER_HOST, SERVER_PORT, LOG_LEVEL
from utils.db import db

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# 전역 변수로 에이전트 선언
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프스팸 관리를 위한 비동기 컨텍스트 매니저"""
    # 시작 시 실행 (startup)
    global agent
    logger.info("A2A 고객 지원 에이전트 시작 중...")
    
    # 데이터베이스 초기화 - 생성자에서 자동으로 처리됨
    # 테이블은 Database 클래스 생성자에서 자동으로 생성됩니다.
    logger.info("데이터베이스 초기화 중...")

    # 고객 지원 에이전트 인스턴스 생성
    agent = CustomerSupportAgent()
    
    # API 라우트 초기화
    app.include_router(init_routes(agent), prefix="/api")
    
    # 웹 인터페이스 라우트 초기화
    app.include_router(init_web_routes(agent))
    
    # 정적 파일 디렉토리 설정
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # 에이전트 시작
    await agent.startup()
    
    logger.info(f"A2A 고객 지원 에이전트가 http://{SERVER_HOST}:{SERVER_PORT}에서 실행 중입니다")
    
    yield  # 여기서 FastAPI 애플리케이션 실행
    
    # 종료 시 실행 (shutdown)
    # 필요한 정리 작업이 있다면 여기에 추가


app = FastAPI(
    title="A2A 고객 지원 에이전트",
    description="Google의 Agent2Agent(A2A) 프로토콜을 활용한 고객 지원 에이전트",
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

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level=LOG_LEVEL.lower(),
    )