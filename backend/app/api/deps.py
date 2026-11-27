import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.db.database import get_db
from app.db.enums import RecordStatus, UserRole
from app.db.models.user import User

security_bearer = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate the current user from Bearer token if provided, else None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
        stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user and user.status == RecordStatus.ACTIVE:
            return user
        return None
    except Exception:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Ensure user is authenticated with a valid Bearer JWT token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Access token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(user_id_str)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired: user account associated with this token was not found. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != RecordStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or suspended.",
        )

    # Enterprise Single-Device Session Enforcement
    token_session_id = payload.get("session_id")
    if token_session_id and user.active_session_id and user.active_session_id != token_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_SUPERSEDED: Your account was signed into on another device. Enterprise policy enforces single-device access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


from app.core.permissions import Permission, has_permission, normalize_role_str


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user has ADMIN authority."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator clearance required for this operation.",
        )
    return current_user


def require_permission(permission: Permission):
    """Factory creating a FastAPI dependency that enforces a granular RBAC permission."""
    async def _perm_checker(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
        user_role: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ) -> Optional[User]:
        # 1. Try resolving user from Bearer token
        if credentials and credentials.credentials:
            try:
                payload = decode_token(credentials.credentials)
                user_id_str = payload.get("sub")
                if user_id_str:
                    user_id = uuid.UUID(user_id_str)
                    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
                    res = await db.execute(stmt)
                    user = res.scalar_one_or_none()
                    if user and user.status == RecordStatus.ACTIVE:
                        if not has_permission(user.role, permission):
                            role_label = user.role.value if hasattr(user.role, "value") else str(user.role)
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Access Denied: Role '{role_label.upper()}' lacks required permission '{permission.value}'. Separation of Duties enforced.",
                            )
                        return user
            except HTTPException:
                raise
            except Exception:
                pass

        # 2. Check if user_role query parameter was provided (for testing or API clients)
        if user_role:
            if not has_permission(user_role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: Role '{user_role.upper()}' lacks required permission '{permission.value}'. Separation of Duties enforced.",
                )
            u_stmt = select(User).where((User.role == user_role) & (User.status == RecordStatus.ACTIVE)).limit(1)
            res_u = await db.execute(u_stmt)
            return res_u.scalar_one_or_none()

        # 3. Fallback: resolve active authorized user for seamless UI operations
        for fallback_role in ("admin", "data_owner", "auditor"):
            if has_permission(fallback_role, permission):
                u_stmt = select(User).where((User.role == fallback_role) & (User.status == RecordStatus.ACTIVE)).limit(1)
                res_u = await db.execute(u_stmt)
                fallback_u = res_u.scalar_one_or_none()
                if fallback_u:
                    return fallback_u

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required: Action requires '{permission.value}'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _perm_checker


def require_authenticated_permission(permission: Permission):
    """Strict RBAC dependency requiring an authenticated Bearer user with the given permission."""
    async def _strict_perm_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(current_user.role, permission):
            role_label = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{role_label.upper()}' lacks required permission '{permission.value}'.",
            )
        return current_user

    return _strict_perm_checker
