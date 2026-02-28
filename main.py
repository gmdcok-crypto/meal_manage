from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import auth, meal, admin
from app.core.database import engine, Base

app = FastAPI(title="PWA Meal Auth System")

# 앱 시작 시 DB 테이블 생성
@app.on_event("startup")
async def startup():
    pass

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
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "traceback": traceback.format_exc()}
    )

# 라우터 등록
app.include_router(auth.router, prefix="/api")
app.include_router(meal.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")

# static 파일 서빙 (PWA 프론트엔드용)
_admin_dist = os.path.join(os.path.dirname(__file__), "static", "admin", "dist")
if os.path.isdir(_admin_dist):
    app.mount("/admin", StaticFiles(directory=_admin_dist, html=True), name="admin")
# (없으면 /admin 미서빙 - Railway 등에서 React 빌드 전에는 생략됨)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

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
