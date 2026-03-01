from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class ActionCall(BaseModel):
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)

class ActionResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: str = ""
    duration_ms: int = 0

class AgentResponse(BaseModel):
    thought: str = Field(description="what I am doing and why")
    action: str = Field(description="action_name")
    params: Dict[str, Any] = Field(default_factory=dict, description="action parameters")