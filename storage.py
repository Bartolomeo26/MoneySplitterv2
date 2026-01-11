from typing import Dict, Optional
from models import Session


class InMemoryStorage:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
    
    def create_session(self, session: Session) -> Session:
        self.sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)
    
    def update_session(self, session: Session) -> Session:
        self.sessions[session.id] = session
        return session
    
    def session_exists(self, session_id: str) -> bool:
        return session_id in self.sessions


storage = InMemoryStorage()
