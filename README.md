
## 사용 방법

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정 (`.env` 파일 생성):
```
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
AGENT_ID=customer-support-agent
AGENT_NAME=고객 지원 에이전트
AGENT_DESCRIPTION=고객 질문에 답변하고 필요시 다른 전문 에이전트와 통신하는 A2A 호환 에이전트
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
PRODUCT_AGENT_URL=http://localhost:8001/agent
SHIPPING_AGENT_URL=http://localhost:8002/agent
BILLING_AGENT_URL=http://localhost:8003/agent
LOG_LEVEL=INFO
```

3. 서버 실행:
```bash
python main.py
```

4. API 사용 예시:
```bash
# 질문하기
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "노트북 모델에 대해 알려주세요", "metadata": {"customer_id": "cust123"}}'

# 작업 상태 확인
curl "http://localhost:8000/tasks/task_123456"

# 기존 작업에 메시지 추가
curl -X POST "http://localhost:8000/tasks/task_123456/messages" \
  -H "Content-Type: application/json" \
  -d '{"query": "배터리 수명은 어떻게 되나요?"}'
```

## 확장 가능성

1. 여러 다른 전문 에이전트 추가 (예: 기술 지원, 마케팅, 영업 등)
2. 다국어 지원 추가
3. 사용자 인증 및 세션 관리 기능 추가
4. 대화 내역 데이터베이스 저장 및 분석
5. 웹소켓을 통한 실시간 응답 구현