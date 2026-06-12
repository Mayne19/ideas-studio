from pydantic import BaseModel
from typing import Optional


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str
    category: str
    requires_llm: bool = True
    requires_search: bool = False
    icon: str = "robot"
    has_implementation: bool = False


class AgentAssignmentCreate(BaseModel):
    project_id: Optional[str] = None
    agent_id: str
    provider_id: str
    enabled: bool = True
    priority: int = 0


class AgentAssignmentUpdate(BaseModel):
    provider_id: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AgentAssignmentPublic(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    project_id: Optional[str] = None
    agent_id: str
    provider_id: str
    enabled: bool
    priority: int
    created_at: str
    updated_at: str


class AgentAssignmentWithDetails(AgentAssignmentPublic):
    agent: AgentInfo
    provider_name: str = ""
    provider_label: str = ""
