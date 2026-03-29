from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# 로그가 어디에도 안 찍히지 않도록 기본 설정 (한 번만 적용)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from app.api import auth, meal, admin
from app.core.database import engine, Base
from app.core.schema_repair import ensure_meal_logs_columns
from app.models.models import SystemSetting  # Base.metadata에 등록 (startup에서 create_all용)

app = FastAPI(title="PWA Meal Auth System")

# SQLAlchemy/aiomysql의 "connection open" 등이 stderr로 나가 Railway에서 Error로 표시되는 것 방지
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiomysql").setLevel(logging.WARNING)

_logger = logging.getLogger("meal_auth")

# 앱 시작 시
@app.on_event("startup")
async def startup():
    _logger.info("서버 올라옴 (Application started)")
    # Railway 등 배포 환경에서 repair_db 미실행 시 system_settings 테이블 자동 생성
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))
        _logger.info("DB 스키마 확인 완료 (system_settings 등)")
    except Exception as e:
        _logger.warning("DB 스키마 확인 중 예외 (무시하고 진행): %s", e)
    try:
        await ensure_meal_logs_columns(engine)
        _logger.info("DB 누락 컬럼 보강 완료 (meal_logs: path, qr_terminal_id, void 등)")
    except Exception as e:
        _logger.warning("DB 누락 컬럼 보강 실패: %s", e)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback


class EnsureApiReturnsJsonMiddleware(BaseHTTPMiddleware):
    """ /api/* 요청이 HTML(StaticFiles)로 떨어지지 않도록 404 시 JSON 반환 (ngrok 등에서 경로 꼬임 방지) """
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        response = await call_next(request)
        if response.status_code == 404:
            return JSONResponse(status_code=404, content={"detail": "Not Found", "path": request.url.path})
        # Content-Type이 HTML이면 경로 미매칭으로 index.html이 온 경우 → JSON 404로 대체
        ct = response.headers.get("content-type", "")
        if "text/html" in ct and request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"detail": "API route not found", "path": request.url.path})
        return response


app.add_middleware(EnsureApiReturnsJsonMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).exception("Unhandled exception: %s", exc)
    is_production = os.environ.get("ENV", "development").lower() in ("production", "prod")
    content = {"detail": "Internal Server Error"}
    if not is_production:
        content["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=content)

# 라우터 등록
app.include_router(auth.router, prefix="/api")
app.include_router(meal.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")

# static 파일 서빙 (PWA 프론트엔드용)
_base = os.path.dirname(os.path.abspath(__file__))
_admin_dist = os.path.join(_base, "static", "admin", "dist")
_static_dir = os.path.join(_base, "static")
if os.path.isdir(_admin_dist):
    app.mount("/admin", StaticFiles(directory=_admin_dist, html=True), name="admin")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "PWA Meal Auth System is running"}

# static 파일 서빙 (PWA 프론트엔드용)
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("ENV", "development") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
