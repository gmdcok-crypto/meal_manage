from fastapi import APIRouter
from app.api.admin import (
    employees, dashboard, raw_data, policies, reports,
    companies, departments, ws
)

router = APIRouter()
router.include_router(ws.router, tags=["Websocket"])
router.include_router(employees.router, prefix="/employees", tags=["Admin Employees"])
router.include_router(dashboard.router, prefix="/stats", tags=["Admin Dashboard"])
router.include_router(raw_data.router, prefix="/raw-data", tags=["Admin Raw Data"])
router.include_router(policies.router, prefix="/policies", tags=["Admin Policies"])
router.include_router(reports.router, prefix="/reports", tags=["Admin Reports"])
router.include_router(companies.router, prefix="/companies", tags=["Admin Companies"])
router.include_router(departments.router, prefix="/departments", tags=["Admin Departments"])
