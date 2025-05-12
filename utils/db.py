"""
SQLite 데이터베이스 유틸리티 모듈
psycopg2 인터페이스를 사용하여 SQLite 데이터베이스에 접근합니다.
"""
import sqlite3
import logging
import os
import traceback
from typing import Dict, List, Any, Optional, Tuple

# 로깅 설정
logger = logging.getLogger(__name__)

# 데이터베이스 경로
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "a2a_test.db")


class Database:
    """SQLite 데이터베이스 클래스"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._create_tables_if_not_exist()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 객체 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 결과를 딕셔너리 형태로 반환
        return conn

    def _create_tables_if_not_exist(self):
        """필요한 테이블이 없으면 생성"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 에이전트 정보 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            version TEXT,
            base_url TEXT NOT NULL,
            auth_required INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 작업 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT, -- JSON 형식으로 저장
            FOREIGN KEY (agent_id) REFERENCES agents (id)
        )
        """)

        # 메시지 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        """)

        # 에이전트 기능 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_capabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            parameters TEXT, -- JSON 형식으로 저장
            FOREIGN KEY (agent_id) REFERENCES agents (id)
        )
        """)

        conn.commit()
        conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """SQL 쿼리 실행 및 결과 반환 (psycopg2 스타일)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            
            # SELECT 쿼리인 경우 결과 반환
            if query.strip().upper().startswith('SELECT'):
                result = [dict(row) for row in cursor.fetchall()]
                return result
            
            # INSERT, UPDATE, DELETE 등의 경우 영향받은 행 수 반환
            conn.commit()
            return [{"affected_rows": cursor.rowcount}]
        
        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            logger.error(f"데이터베이스 쿼리 실행 오류: {str(e)}")
            raise
        
        finally:
            conn.close()

    # 에이전트 관련 메소드
    def save_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 정보 저장 또는 업데이트"""
        query = """
        INSERT INTO agents (id, name, description, version, base_url, auth_required)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            version = excluded.version,
            base_url = excluded.base_url,
            auth_required = excluded.auth_required
        """
        
        params = (
            agent_data['id'],
            agent_data['name'],
            agent_data.get('description', ''),
            agent_data.get('version', '1.0.0'),
            agent_data['base_url'],
            1 if agent_data.get('auth_required', False) else 0
        )
        
        self.execute_query(query, params)
        
        # 기능 정보 저장
        if 'capabilities' in agent_data:
            # 기존 기능 정보 삭제
            self.execute_query("DELETE FROM agent_capabilities WHERE agent_id = ?", (agent_data['id'],))
            
            # 새 기능 정보 저장
            for capability in agent_data['capabilities']:
                import json
                self.execute_query(
                    """
                    INSERT INTO agent_capabilities (agent_id, name, description, parameters)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        agent_data['id'],
                        capability['name'],
                        capability.get('description', ''),
                        json.dumps(capability.get('parameters', {}))
                    )
                )
        
        return self.get_agent_by_id(agent_data['id'])

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """ID로 에이전트 정보 조회"""
        query = "SELECT * FROM agents WHERE id = ?"
        agents = self.execute_query(query, (agent_id,))
        
        if not agents:
            return None
        
        agent = agents[0]
        
        # 기능 정보 함께 조회
        import json
        capabilities_query = "SELECT name, description, parameters FROM agent_capabilities WHERE agent_id = ?"
        capabilities_data = self.execute_query(capabilities_query, (agent_id,))
        
        capabilities = []
        for capability in capabilities_data:
            capabilities.append({
                'name': capability['name'],
                'description': capability['description'],
                'parameters': json.loads(capability['parameters']) if capability['parameters'] else {}
            })
        
        agent['capabilities'] = capabilities
        agent['auth_required'] = bool(agent['auth_required'])
        
        return agent

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """모든 에이전트 정보 조회"""
        query = "SELECT id, name, description, base_url FROM agents"
        return self.execute_query(query)

    # 작업 관련 메소드
    def save_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """작업 정보 저장 또는 업데이트"""
        import json
        
        query = """
        INSERT INTO tasks (id, title, description, status, agent_id, metadata, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            status = excluded.status,
            metadata = excluded.metadata,
            updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            task_data['id'],
            task_data['title'],
            task_data.get('description', ''),
            task_data['status'],
            task_data['agent_id'],
            json.dumps(task_data.get('metadata', {}))
        )
        
        self.execute_query(query, params)
        return self.get_task_by_id(task_data['id'])

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """ID로 작업 정보 조회"""
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE t.id = ?
        """
        tasks = self.execute_query(query, (task_id,))
        
        if not tasks:
            return None
        
        task = tasks[0]
        
        # 메타데이터 파싱
        import json
        task['metadata'] = json.loads(task['metadata']) if task['metadata'] else {}
        
        # 메시지 정보 함께 조회
        messages_query = "SELECT * FROM messages WHERE task_id = ? ORDER BY created_at"
        messages = self.execute_query(messages_query, (task_id,))
        task['messages'] = messages
        
        return task

    def get_tasks_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """에이전트별 작업 정보 조회"""
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE t.agent_id = ?
        ORDER BY t.updated_at DESC
        """
        tasks = self.execute_query(query, (agent_id,))
        
        # 메타데이터 파싱
        import json
        for task in tasks:
            task['metadata'] = json.loads(task['metadata']) if task['metadata'] else {}
        
        return tasks

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 작업 정보 조회"""
        query = """
        SELECT t.*, a.name as agent_name
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        ORDER BY t.updated_at DESC
        LIMIT ?
        """
        tasks = self.execute_query(query, (limit,))
        
        # 메타데이터 파싱
        import json
        for task in tasks:
            task['metadata'] = json.loads(task['metadata']) if task['metadata'] else {}
        
        return tasks

    # 메시지 관련 메소드
    def save_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """메시지 정보 저장"""
        query = """
        INSERT INTO messages (id, task_id, type, content)
        VALUES (?, ?, ?, ?)
        """
        
        params = (
            message_data['id'],
            message_data['task_id'],
            message_data['type'],
            message_data['content']
        )
        
        self.execute_query(query, params)
        
        # 작업 업데이트 시간 갱신
        update_task_query = """
        UPDATE tasks
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        self.execute_query(update_task_query, (message_data['task_id'],))
        
        return message_data

    def get_messages_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """작업별 메시지 정보 조회"""
        query = """
        SELECT *
        FROM messages
        WHERE task_id = ?
        ORDER BY created_at
        """
        return self.execute_query(query, (task_id,))


# 싱글톤 패턴으로 인스턴스 생성
db = Database()
