from fastapi import APIRouter
from app.api.admin import (
    employees, dashboard, raw_data, policies, reports,
    companies, departments, ws, notice, today_meal_check, admins, settings as admin_settings,
    hardware_terminals,
)

router = APIRouter()
router.include_router(ws.router, tags=["Websocket"])
router.include_router(notice.router, tags=["Admin Notice"])
router.include_router(today_meal_check.router, tags=["Admin Today Meal Check"])
router.include_router(admins.router, prefix="/admins", tags=["Admin Admins"])
router.include_router(admin_settings.router, prefix="/settings", tags=["Admin Settings"])
router.include_router(
    hardware_terminals.printer_router, prefix="/printer-terminals", tags=["Admin Printer"]
)
router.include_router(
    hardware_terminals.qlight_router, prefix="/qlight-terminals", tags=["Admin Qlight"]
)
router.include_router(employees.router, prefix="/employees", tags=["Admin Employees"])
router.include_router(dashboard.router, prefix="/stats", tags=["Admin Dashboard"])
router.include_router(raw_data.router, prefix="/raw-data", tags=["Admin Raw Data"])
router.include_router(policies.router, prefix="/policies", tags=["Admin Policies"])
router.include_router(reports.router, prefix="/reports", tags=["Admin Reports"])
router.include_router(companies.router, prefix="/companies", tags=["Admin Companies"])
router.include_router(departments.router, prefix="/departments", tags=["Admin Departments"])
