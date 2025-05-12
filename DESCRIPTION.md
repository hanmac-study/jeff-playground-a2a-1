# A2A 에이전트 카드(Agent Card) 교환 설명

## A2A 에이전트 카드란?

A2A(Agent-to-Agent) 프로토콜에서 에이전트 카드는 AI 에이전트가 자신을 식별하고 자신의 기능을 다른 에이전트에게 알리는 방법입니다. 이는 마치 사람들이 처음 만났을 때 명함을 교환하는 것과 유사합니다. 에이전트 카드에는 다음과 같은 정보가 포함됩니다:

- **ID**: 에이전트의 고유 식별자
- **이름**: 에이전트의 이름
- **설명**: 에이전트가 수행하는 작업에 대한 설명
- **버전**: 에이전트의 프로토콜 버전
- **기능(capabilities)**: 에이전트가 수행할 수 있는 작업 목록
- **기본 URL**: 에이전트와 통신하기 위한 기본 URL
- **인증 필요 여부**: 에이전트와 통신할 때 인증이 필요한지 여부

## 에이전트 카드 교환의 의미

에이전트 카드를 교환한다는 것은 서로 다른 AI 에이전트들이 상호작용을 시작하기 전에 서로의 기능, 통신 방법, 그리고 어떤 종류의 작업을 처리할 수 있는지에 대한 정보를 공유하는 프로세스를 말합니다. 이 프로젝트에서는 다음과 같은 방식으로 구현되었습니다:

1. **에이전트 카드 생성**: 
   ```python
   # agent/agent_card.py에서
   def create_agent_card() -> AgentCard:
       # 에이전트의 기능 정의
       capabilities = [
           AgentCapability(
               name="answer_general_questions",
               description="일반적인 고객 질문에 답변"
           ),
           # 다른 기능들...
       ]
       
       # 에이전트 카드 생성
       agent_card = AgentCard(
           id=AGENT_ID,
           name=AGENT_NAME,
           description=AGENT_DESCRIPTION,
           version=A2A_PROTOCOL_VERSION,
           capabilities=capabilities,
           base_url=base_url,
           auth_required=False
       )
       
       return agent_card
   ```

2. **에이전트 카드 노출**: 
   ```python
   # a2a_protocol/server.py에서
   @self.router.get("/.well-known/agent.json")
   async def get_agent_card():
       return self.agent_card.model_dump()
   ```
   - 각 에이전트는 `/.well-known/agent.json` 엔드포인트를 통해 자신의 에이전트 카드를 외부에 노출합니다.

3. **에이전트 발견/검색**: 
   ```python
   # a2a_protocol/client.py에서
   async def discover_agent(self, agent_url: str) -> AgentCard:
       """에이전트 카드를 검색하여 에이전트 정보 확인"""
       async with httpx.AsyncClient() as client:
           response = await client.get(f"{agent_url}/.well-known/agent.json")
           agent_card = AgentCard.model_validate(response.json())
           self.registered_agents[agent_card.id] = agent_card
           return agent_card
   ```
   - 에이전트는 다른 에이전트의 URL을 알고 있을 때, 해당 URL에서 에이전트 카드를 가져와서 등록합니다.

4. **시작 시 에이전트 검색**:
   ```python
   # agent/customer_support_agent.py에서 
   async def startup(self):
       """에이전트 시작 및 외부 에이전트 검색"""
       for agent_type, agent_url in self.external_agents.items():
           try:
               agent_card = await self.client.discover_agent(agent_url)
               self.logger.info(f"{agent_type} 에이전트 발견: {agent_card.name}")
           except Exception as e:
               self.logger.warning(f"{agent_type} 에이전트 검색 실패: {str(e)}")
   ```
   - 고객 지원 에이전트는 시작할 때 다른 전문 에이전트(제품, 배송, 결제 등)를 발견하여 통신할 준비를 합니다.

## 에이전트 카드 교환의 중요성

에이전트 카드 교환은 다음과 같은 여러 이유로 A2A 프로토콜에서 중요합니다:

1. **자동 발견(Auto Discovery)**: 에이전트는 다른 에이전트의 존재와 위치를 자동으로 발견할 수 있습니다.

2. **기능 파악**: 에이전트는 다른 에이전트가 어떤 기능을 제공하는지 알 수 있으므로, 필요한 작업을 위해 적절한 에이전트에게 작업을 위임할 수 있습니다.

3. **버전 관리**: 프로토콜 버전이 포함되어 있어 호환성 문제를 방지할 수 있습니다.

4. **분산 시스템**: 여러 전문 에이전트가 독립적으로 동작하면서도 필요에 따라 협업할 수 있는 분산 시스템을 가능하게 합니다.

이 프로젝트에서는 고객 지원 에이전트가 제품, 배송, 결제 등의 전문 에이전트와 통신하여 고객 문의를 효과적으로 처리하는 데 에이전트 카드 교환이 핵심적인 역할을 합니다. 고객 지원 에이전트는 자신이 직접 처리할 수 없는 전문적인 문의가 들어오면, 적절한 전문 에이전트를 찾아 작업을 위임하고 그 결과를 고객에게 전달합니다.
