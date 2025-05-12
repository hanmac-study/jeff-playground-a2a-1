import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 서버 설정
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# A2A 프로토콜 설정
A2A_PROTOCOL_VERSION = "1.0.0"
AGENT_ID = os.getenv("AGENT_ID", "customer-support-agent")
AGENT_NAME = os.getenv("AGENT_NAME", "고객 지원 에이전트")
AGENT_DESCRIPTION = os.getenv("AGENT_DESCRIPTION", "고객 질문에 답변하고 필요시 다른 전문 에이전트와 통신하는 A2A 호환 에이전트")

# LLM 설정
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# 외부 에이전트 설정
PRODUCT_AGENT_URL = os.getenv("PRODUCT_AGENT_URL", "http://localhost:8001/agent")
SHIPPING_AGENT_URL = os.getenv("SHIPPING_AGENT_URL", "http://localhost:8002/agent")
BILLING_AGENT_URL = os.getenv("BILLING_AGENT_URL", "http://localhost:8003/agent")

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
