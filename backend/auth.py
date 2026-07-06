import sqlite3
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status

from database import create_user, get_demo_user, get_user_by_email, get_user_by_id
from schemas import AuthLoginRequest, AuthRegisterRequest, AuthResponse, UserPublic
from security import create_access_token, decode_access_token, hash_password, verify_password


def public_user(row: Dict[str, Any]) -> UserPublic:
    return UserPublic(
        id=int(row["id"]),
        email=row["email"],
        username=row.get("username"),
        created_at=row.get("created_at"),
        is_active=int(row.get("is_active", 1)),
    )


def _auth_response(user: Dict[str, Any]) -> AuthResponse:
    return AuthResponse(user=public_user(user), access_token=create_access_token(str(user["id"])))


def register_user(payload: AuthRegisterRequest) -> AuthResponse:
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        user = create_user(payload.email, payload.username, hash_password(payload.password))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    return _auth_response(user)


def login_user(payload: AuthLoginRequest) -> AuthResponse:
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if int(user.get("is_active", 1)) != 1:
        raise HTTPException(status_code=403, detail="User is inactive")
    return _auth_response(user)


def _token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def get_current_user(request: Request) -> UserPublic:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
    user = get_user_by_id(user_id)
    if not user or int(user.get("is_active", 1)) != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return public_user(user)


def get_current_user_or_demo(request: Request) -> UserPublic:
    token = _token_from_request(request)
    if not token:
        return public_user(get_demo_user())
    return get_current_user(request)


CurrentUser = Depends(get_current_user_or_demo)
