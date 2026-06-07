from datetime import datetime

from pydantic import BaseModel


class AlertEventRead(BaseModel):
    id: int
    event_type: str
    severity: str
    message: str
    payload: dict
    acknowledged: bool
    created_at: datetime