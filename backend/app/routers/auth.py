from datetime import datetime, timedelta
import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import OTPCode, User
from ..schemas import (
    LoginCodeRequest,
    LoginPasswordRequest,
    RegisterRequest,
    SendCodeRequest,
    TokenResponse,
    UserInfo,
)
from ..security import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_cn_phone,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _resolve_role(phone: str) -> str:
    settings = get_settings()
    return "admin" if phone in settings.admin_phone_list else "user"


def _sync_admin_role(user: User, db: Session) -> None:
    expected = _resolve_role(user.phone)
    if user.role != expected:
        user.role = expected
        db.commit()
        db.refresh(user)


def _get_valid_code(db: Session, phone: str, code: str, purpose: str) -> OTPCode | None:
    now = datetime.utcnow()
    return (
        db.query(OTPCode)
        .filter(
            OTPCode.phone == phone,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.used.is_(False),
            OTPCode.expires_at > now,
        )
        .order_by(OTPCode.id.desc())
        .first()
    )


@router.post("/send-code")
def send_code(payload: SendCodeRequest, db: Session = Depends(get_db)):
    settings = get_settings()

    if not validate_cn_phone(payload.phone):
        raise HTTPException(status_code=400, detail="手机号格式不合法")

    code = f"{random.randint(0, 999999):06d}"
    otp = OTPCode(
        phone=payload.phone,
        code=code,
        purpose=payload.purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes),
    )
    db.add(otp)
    db.commit()

    # TODO: Replace with real SMS provider integration (Aliyun/Tencent Cloud).
    return {
        "message": "验证码已发送",
        "expires_minutes": settings.otp_expire_minutes,
        "debug_code": code if settings.otp_debug_return_code else None,
    }


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if not validate_cn_phone(payload.phone):
        raise HTTPException(status_code=400, detail="手机号格式不合法")

    user = db.query(User).filter(User.phone == payload.phone).first()
    if user:
        raise HTTPException(status_code=400, detail="手机号已注册")

    otp = _get_valid_code(db, payload.phone, payload.code, "register")
    if not otp:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    new_user = User(phone=payload.phone, password_hash=hash_password(payload.password), role=_resolve_role(payload.phone))
    db.add(new_user)
    otp.used = True
    db.commit()
    db.refresh(new_user)

    token = create_access_token(str(new_user.id))
    return TokenResponse(access_token=token)


@router.post("/login/password", response_model=TokenResponse)
def login_password(payload: LoginPasswordRequest, db: Session = Depends(get_db)):
    if not validate_cn_phone(payload.phone):
        raise HTTPException(status_code=400, detail="手机号格式不合法")

    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    _sync_admin_role(user, db)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login/code", response_model=TokenResponse)
def login_code(payload: LoginCodeRequest, db: Session = Depends(get_db)):
    if not validate_cn_phone(payload.phone):
        raise HTTPException(status_code=400, detail="手机号格式不合法")

    otp = _get_valid_code(db, payload.phone, payload.code, "login")
    if not otp:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在，请先注册")
    _sync_admin_role(user, db)

    otp.used = True
    db.commit()

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _sync_admin_role(current_user, db)
    return UserInfo(id=current_user.id, phone=current_user.phone, role=current_user.role)
