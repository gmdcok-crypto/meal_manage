"""PWA 공지사항: 백엔드 static/notice.html 읽기·쓰기 API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

# 프로젝트 루트 = app/api/admin 의 상위 3단계
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
NOTICE_PATH = os.path.join(_base, "static", "notice.html")


class NoticeBody(BaseModel):
    content: str = ""


@router.get("/notice")
async def get_notice():
    """공지 내용 반환 (PWA·PC 앱 로드용)."""
    if not os.path.isfile(NOTICE_PATH):
        return {"content": ""}
    try:
        with open(NOTICE_PATH, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read notice: {e}")


@router.put("/notice")
async def save_notice(body: NoticeBody):
    """공지 내용 저장 (PC 앱 저장 시 호출). 줄바꿈은 <br>로 저장해 PWA에서 그대로 표시."""
    try:
        os.makedirs(os.path.dirname(NOTICE_PATH), exist_ok=True)
        with open(NOTICE_PATH, "w", encoding="utf-8") as f:
            f.write(body.content or "")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save notice: {e}")
