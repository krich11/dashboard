import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.dashboard import Dashboard, WidgetInstance
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardExport,
    DashboardImportRequest,
    DashboardRead,
    DashboardUpdate,
    WidgetInstanceBase,
)


def list_dashboards(db: Session) -> list[DashboardRead]:
    rows = (
        db.query(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .order_by(Dashboard.name)
        .all()
    )
    return [DashboardRead.model_validate(row) for row in rows]


def get_dashboard(db: Session, dashboard_id: str) -> DashboardRead | None:
    row = (
        db.query(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .filter(Dashboard.id == dashboard_id)
        .first()
    )
    if row is None:
        return None
    return DashboardRead.model_validate(row)


def get_default_dashboard(db: Session) -> DashboardRead | None:
    row = (
        db.query(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .filter(Dashboard.is_default.is_(True))
        .first()
    )
    if row is None:
        return None
    return DashboardRead.model_validate(row)


def _apply_widgets(dashboard: Dashboard, widgets: list[WidgetInstanceBase]) -> None:
    dashboard.widgets.clear()
    for widget in widgets:
        dashboard.widgets.append(
            WidgetInstance(
                id=widget.id or str(uuid.uuid4()),
                widget_type=widget.widget_type,
                title=widget.title,
                config=widget.config,
                grid_x=widget.grid_x,
                grid_y=widget.grid_y,
                grid_w=widget.grid_w,
                grid_h=widget.grid_h,
            )
        )


def create_dashboard(db: Session, payload: DashboardCreate) -> DashboardRead:
    if payload.is_default:
        db.query(Dashboard).filter(Dashboard.is_default.is_(True)).update({"is_default": False})
    dashboard = Dashboard(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        layout=payload.layout,
        is_default=payload.is_default,
    )
    _apply_widgets(dashboard, payload.widgets)
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return DashboardRead.model_validate(dashboard)


def update_dashboard(db: Session, dashboard_id: str, payload: DashboardUpdate) -> DashboardRead | None:
    dashboard = (
        db.query(Dashboard)
        .options(joinedload(Dashboard.widgets))
        .filter(Dashboard.id == dashboard_id)
        .first()
    )
    if dashboard is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    widgets = data.pop("widgets", None)
    if data.get("is_default"):
        db.query(Dashboard).filter(Dashboard.id != dashboard_id).update({"is_default": False})
    for key, value in data.items():
        setattr(dashboard, key, value)
    if widgets is not None:
        _apply_widgets(dashboard, [WidgetInstanceBase(**w) for w in widgets])
    db.commit()
    db.refresh(dashboard)
    return DashboardRead.model_validate(dashboard)


def delete_dashboard(db: Session, dashboard_id: str) -> bool:
    dashboard = db.get(Dashboard, dashboard_id)
    if dashboard is None:
        return False
    if dashboard.is_default:
        raise ValueError("Cannot delete the default dashboard")
    db.delete(dashboard)
    db.commit()
    return True


def export_dashboard(db: Session, dashboard_id: str) -> DashboardExport | None:
    dashboard = get_dashboard(db, dashboard_id)
    if dashboard is None:
        return None
    return DashboardExport(
        name=dashboard.name,
        description=dashboard.description,
        layout=dashboard.layout,
        widgets=[
            WidgetInstanceBase(
                id=w.id,
                widget_type=w.widget_type,
                title=w.title,
                config=w.config,
                grid_x=w.grid_x,
                grid_y=w.grid_y,
                grid_w=w.grid_w,
                grid_h=w.grid_h,
            )
            for w in dashboard.widgets
        ],
    )


def import_dashboard(db: Session, payload: DashboardImportRequest) -> DashboardRead:
    export = payload.dashboard
    widgets = [
        WidgetInstanceBase(
            widget_type=w.widget_type,
            title=w.title,
            config=w.config,
            grid_x=w.grid_x,
            grid_y=w.grid_y,
            grid_w=w.grid_w,
            grid_h=w.grid_h,
        )
        for w in export.widgets
    ]
    return create_dashboard(
        db,
        DashboardCreate(
            name=export.name,
            description=export.description,
            layout=export.layout,
            is_default=payload.set_as_default,
            widgets=widgets,
        ),
    )


def seed_default_dashboard(db: Session) -> None:
    if db.query(Dashboard).count() > 0:
        return
    create_dashboard(
        db,
        DashboardCreate(
            name="Overview",
            description="Default high-level operational view",
            is_default=True,
            layout={"cols": 12, "rowHeight": 30},
            widgets=[
                WidgetInstanceBase(
                    widget_type="UpDownOverallStatus",
                    title="Overall Status",
                    config={"title": "Datacenter Status", "showBreakdown": True},
                    grid_x=0,
                    grid_y=0,
                    grid_w=12,
                    grid_h=4,
                ),
                WidgetInstanceBase(
                    widget_type="InternetReachability",
                    title="Internet Reachability",
                    config={"title": "Internet Health", "showTargets": True},
                    grid_x=0,
                    grid_y=4,
                    grid_w=12,
                    grid_h=4,
                ),
            ],
        ),
    )