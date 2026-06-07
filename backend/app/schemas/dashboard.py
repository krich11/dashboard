from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WidgetInstanceBase(BaseModel):
    widget_type: str
    title: str = ""
    config: dict = Field(default_factory=dict)
    grid_x: int = 0
    grid_y: int = 0
    grid_w: int = 4
    grid_h: int = 3


class WidgetInstanceRead(WidgetInstanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dashboard_id: str


class DashboardBase(BaseModel):
    name: str
    description: str | None = None
    layout: dict = Field(default_factory=dict)
    is_default: bool = False


class DashboardCreate(DashboardBase):
    widgets: list[WidgetInstanceBase] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout: dict | None = None
    is_default: bool | None = None
    widgets: list[WidgetInstanceBase] | None = None


class DashboardRead(DashboardBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    widgets: list[WidgetInstanceRead] = Field(default_factory=list)