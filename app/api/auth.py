from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import Token, UserResponse, VerifyDeviceRequest
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.meal import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/verify_device")
async def verify_device(req: VerifyDeviceRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.emp_no == req.emp_no))
        user = result.scalar_one_or_none()
        
        if not user or user.name != req.name:
            raise HTTPException(status_code=400, detail="사번 또는 이름이 일치하지 않습니다.")
        
        safe_password = (req.password or "")[:72]

        if not user.is_verified:
            # 최초 인증: 비밀번호 저장, is_verified=True 로 설정
            if not safe_password:
                raise HTTPException(status_code=400, detail="최초 접속 시 비밀번호를 설정해야 합니다.")
            user.password_hash = get_password_hash(safe_password)
            user.is_verified = True
        else:
            # 이미 인증된 사용자(키 변경·토큰 만료 등으로 재로그인): 기존 비밀번호만 검증, DB는 수정하지 않음
            if not user.password_hash:
                raise HTTPException(status_code=400, detail="기기 초기화된 사번입니다. 비밀번호를 다시 설정해 주세요.")
            if not verify_password(safe_password, user.password_hash):
                raise HTTPException(status_code=400, detail="이미 인증된 사번이거나 비밀번호가 일치하지 않습니다.")
        
        await db.commit()
        await db.refresh(user)
        
        try:
            from app.api.websocket import manager
            import asyncio
            asyncio.create_task(manager.broadcast({
                "type": "USER_VERIFIED",
                "data": {"emp_no": user.emp_no, "name": user.name}
            }))
        except Exception:
            pass
        
        access_token = create_access_token(subject=user.id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"name": user.name, "emp_no": user.emp_no}
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(err_msg)
        raise HTTPException(
            status_code=500,
            detail=f"기기 인증 처리 중 오류: {str(e)}",
        )

@router.get("/status")
async def get_auth_status(
    current_user: User = Depends(get_current_user)
):
    """
    기기 인증: 인증된 사원(is_verified)은 기간 관계없이 2차 인증 없이 패스.
    사원관리에서 '기기 초기화'한 경우(is_verified=False)만 재로그인 필요.
    """
    return {
        "status": "authenticated",
        "user": {
            "name": current_user.name,
            "emp_no": current_user.emp_no
        }
    }

