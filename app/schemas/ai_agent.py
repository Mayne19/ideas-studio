from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str
    category: str
    phase: str = "unknown"
    requires_llm: bool = True
    requires_search: bool = False
    requires_external_api: bool = False
    icon: str = "robot"
    has_implementation: bool = False
    status: str = "planned"
    output_json_field: str | None = None
    visible_in_frontend: bool = True


class AgentAssignmentCreate(BaseModel):
    project_id: Optional[str] = None
    agent_id: str
    provider_code: str
    model: Optional[str] = None
    enabled: bool = True
    priority: int = 0


class AgentAssignmentUpdate(BaseModel):
    provider_code: Optional[str] = None
    model: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AgentAssignmentPublic(BaseModel):
    id: str
    project_id: Optional[str] = None
    agent_id: str
    provider_code: str
    model: Optional[str] = None
    enabled: bool
    priority: int


class AgentAssignmentWithDetails(AgentAssignmentPublic):
    agent: AgentInfo
    provider_name: str = ""
    provider_label: str = ""
