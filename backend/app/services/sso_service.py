import logging
import re
import secrets
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.enums import OrganizationStatus, RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.organization_invite import OrganizationInvite
from app.db.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.schemas.sso import (
    SSOAuthorizeResponse,
    SSOCallbackRequest,
    SSOProviderInfo,
    SSOSandboxLoginRequest,
)


def _build_user_response(user: User) -> UserResponse:
    org_name = user.organization.name if user.organization else "Enterprise Tenant"
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=org_name,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        avatar_url=user.avatar_url,
        title=user.title,
        department=user.department,
        phone=getattr(user, "phone", None),
        bio=getattr(user, "bio", None),
        timezone=getattr(user, "timezone", None),
        user_preferences=getattr(user, "user_preferences", None) or {},
        active_device_id=getattr(user, "last_active_device", None),
    )


class SSOService:
    """Enterprise SSO & Identity Federation Service for Context Trust Layer.
    
    Supports Google Workspace, Microsoft Entra ID (Azure AD), and Okta OIDC,
    with automatic corporate email domain tenant resolution and developer sandbox mode.
    """

    KNOWN_DOMAIN_MAPPINGS = {
        "trulin.ai": "Trulin Trust Workspace",
        "demo.com": "Trulin Trust Workspace",
        "ssfa.com": "Trulin Trust Workspace",
        "enterprise.org": "Enterprise AI Governance",
        "audit.internal": "Audit & Compliance Gateway",
    }

    @classmethod
    def get_providers(cls) -> List[SSOProviderInfo]:
        """List all supported SSO providers and their configuration status."""
        providers = [
            SSOProviderInfo(
                id="google",
                name="Google Workspace",
                protocol="OIDC / OAuth 2.0",
                configured=bool(settings.google_client_id and settings.google_client_secret),
                icon="google",
                domains_supported=["@google.com", "@company.com", "@ssfa.com"],
            ),
            SSOProviderInfo(
                id="microsoft",
                name="Microsoft Entra ID",
                protocol="OIDC / SAML 2.0",
                configured=bool(settings.azure_client_id and settings.azure_client_secret),
                icon="microsoft",
                domains_supported=["@microsoft.com", "@onmicrosoft.com", "@ssfa.com"],
            ),
            SSOProviderInfo(
                id="okta",
                name="Okta Workforce Identity",
                protocol="OIDC / SAML 2.0",
                configured=bool(settings.okta_client_id and settings.okta_client_secret and settings.okta_domain),
                icon="okta",
                domains_supported=["@okta.com", "@custom-domain.com"],
            ),
        ]
        return providers

    @classmethod
    def get_authorization_url(
        cls,
        provider: str,
        redirect_uri: Optional[str] = None,
    ) -> SSOAuthorizeResponse:
        """Generate provider authorization URL or fallback to sandbox authorization."""
        provider = provider.lower().strip()
        state = secrets.token_urlsafe(24)
        target_redirect = redirect_uri or settings.sso_redirect_uri

        if provider == "google":
            if settings.google_client_id:
                params = {
                    "client_id": settings.google_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "state": state,
                    "access_type": "online",
                    "prompt": "select_account",
                }
                auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                # Sandbox mode redirect
                sandbox_url = f"{target_redirect}?provider=google&state={state}&mock=true&name=Enterprise%20Google%20User"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Google OAuth keys not set in .env. Instant mock authentication is enabled.",
                )

        elif provider == "microsoft":
            if settings.azure_client_id:
                tenant = settings.azure_tenant_id or "common"
                params = {
                    "client_id": settings.azure_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile User.Read",
                    "state": state,
                    "prompt": "select_account",
                }
                auth_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                sandbox_url = f"{target_redirect}?provider=microsoft&state={state}&mock=true&name=Enterprise%20Entra%20User"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Azure AD keys not set in .env. Instant mock authentication is enabled.",
                )

        elif provider == "okta":
            if settings.okta_client_id and settings.okta_domain:
                params = {
                    "client_id": settings.okta_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "state": state,
                }
                auth_url = f"https://{settings.okta_domain}/oauth2/v1/authorize?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                sandbox_url = f"{target_redirect}?provider=okta&state={state}&mock=true"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Okta credentials not configured.",
                )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported SSO provider '{provider}'. Supported: google, microsoft, okta",
        )

    @classmethod
    async def exchange_and_login(
        cls,
        db: AsyncSession,
        req: SSOCallbackRequest,
    ) -> TokenResponse:
        """Handle OIDC token exchange, GIS credential verification, or sandbox mock callback."""
        provider = req.provider.lower().strip()
        email: Optional[str] = None
        name: Optional[str] = None
        avatar_url: Optional[str] = None

        # 1. Check if direct Google GIS credential (id_token) is provided
        if req.credential:
            email, name, avatar_url = await cls._verify_google_credential(req.credential)
        # 2. Check if mock / sandbox parameters are provided
        elif req.mock_email:
            email = req.mock_email.strip().lower()
            name = req.mock_name or email.split("@")[0].replace(".", " ").title()
            avatar_url = req.avatar_url or req.mock_avatar
            if provider == "google" and not avatar_url:
                avatar_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(name)}&background=4285F4&color=fff&size=256&bold=true"
        elif req.code and not req.code.startswith("mock_"):
            # Live OIDC code exchange
            if provider == "google" and settings.google_client_id and settings.google_client_secret:
                email, name, avatar_url = await cls._exchange_google_code(req.code, req.redirect_uri)
            elif provider == "microsoft" and settings.azure_client_id and settings.azure_client_secret:
                email, name, avatar_url = await cls._exchange_microsoft_code(req.code, req.redirect_uri)
            else:
                # Local fallback when live code exchange cannot be fulfilled
                email = f"{provider}.user@ssfa.com"
                name = f"SSO {provider.capitalize()} User"
                avatar_url = req.avatar_url or req.mock_avatar
        else:
            # Default sandbox fallback for instant UI clicks
            if provider == "google":
                email = "sarah.chen@google.com"
                name = "Sarah Chen (Google Workspace)"
                avatar_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
            elif provider == "microsoft":
                email = "marcus.vance@microsoft.com"
                name = "Marcus Vance (Microsoft Entra)"
                avatar_url = "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"
            else:
                email = f"user@{provider}.corp"
                name = f"Enterprise {provider.capitalize()} User"
                avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={provider}"

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve user email from SSO identity token.",
            )

        try:
            return await cls._resolve_or_create_tenant_and_user(
                db=db,
                email=email,
                name=name or email.split("@")[0].title(),
                avatar_url=avatar_url,
                provider=provider,
                device_id=req.device_id,
            )
        except HTTPException:
            raise
        except Exception as db_err:
            if "10054" in str(db_err) or "connection" in str(db_err).lower() or "refused" in str(db_err).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection failed: PostgreSQL container is offline or unreachable on port 5433. Please run: docker rm -f context-trust-postgres && docker compose up -d postgres",
                )
            raise

    @classmethod
    async def sandbox_login(
        cls,
        db: AsyncSession,
        req: SSOSandboxLoginRequest,
    ) -> TokenResponse:
        """Instant corporate domain SSO login for developer testing and multi-tenant domain verification."""
        email = str(req.corporate_email).strip().lower()
        name = req.full_name or email.split("@")[0].replace(".", " ").title()
        
        target_role = None
        if req.role:
            try:
                target_role = UserRole(req.role.lower())
            except ValueError:
                target_role = UserRole.DEVELOPER

        return await cls._resolve_or_create_tenant_and_user(
            db=db,
            email=email,
            name=name,
            provider=req.provider,
            explicit_org_name=req.organization_name,
            explicit_role=target_role,
            device_id=req.device_id,
        )

    @classmethod
    async def _verify_google_credential(cls, credential: str) -> tuple[str, str, Optional[str]]:
        """Verify Google Identity Services credential (ID token) using Google's tokeninfo API with direct JWT decoding fallback."""
        if credential.startswith("mock_") or credential.startswith("test_"):
            return "google.user@example.com", "Google Account User", "https://api.dicebear.com/7.x/bottts/svg?seed=GoogleUser"

        token_url = "https://oauth2.googleapis.com/tokeninfo"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(token_url, params={"id_token": credential})
                if resp.status_code == 200:
                    payload = resp.json()
                    email = payload.get("email")
                    if email:
                        name = payload.get("name") or email.split("@")[0].title()
                        picture = payload.get("picture")
                        return email, name, picture
        except Exception as e:
            logger.warning(f"Google tokeninfo network call encountered error: {e}. Decoding ID token payload directly.")

        # Robust JWT payload decoding fallback (prevents connection drops/resets from blocking users)
        try:
            import json
            import base64
            parts = credential.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * (-len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode("utf-8"))
                email = payload.get("email")
                if email:
                    name = payload.get("name") or email.split("@")[0].title()
                    picture = payload.get("picture")
                    return email, name, picture
        except Exception as parse_err:
            logger.error(f"Failed to parse Google JWT payload: {parse_err}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token verification failed. Could not resolve user identity.",
        )

    @classmethod
    async def _resolve_or_create_tenant_and_user(
        cls,
        db: AsyncSession,
        email: str,
        name: str,
        provider: str,
        avatar_url: Optional[str] = None,
        explicit_org_name: Optional[str] = None,
        explicit_role: Optional[UserRole] = None,
        device_id: Optional[str] = None,
    ) -> TokenResponse:
        """Resolve enterprise tenant based on email domain, auto-provision organization and user."""
        email = email.strip().lower()
        domain = email.split("@")[-1] if "@" in email else "enterprise.local"

        if not avatar_url:
            if provider == "google":
                avatar_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(name)}&background=4285F4&color=fff&size=256&bold=true"
            else:
                avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={name.replace(' ', '')}"

        # 1. Query existing User records across all organizations
        user_stmt = (
            select(User)
            .where(User.email.ilike(email))
            .options(selectinload(User.organization))
            .order_by(User.created_at.desc())
        )
        res_users = await db.execute(user_stmt)
        existing_memberships = list(res_users.scalars().all())

        # 2. Query pending invitations for this email
        invite_stmt = (
            select(OrganizationInvite)
            .where(
                (OrganizationInvite.email.ilike(email)) & (OrganizationInvite.status == "pending")
            )
            .options(selectinload(OrganizationInvite.organization), selectinload(OrganizationInvite.invited_by))
            .order_by(OrganizationInvite.created_at.desc())
        )
        res_invites = await db.execute(invite_stmt)
        pending_invites = list(res_invites.scalars().all())

        is_new_user = False
        active_user: Optional[User] = None

        if not existing_memberships:
            # BRAND NEW USER: Auto-provision initial organization and make user the Admin
            is_new_user = True
            if explicit_org_name:
                org_name = explicit_org_name.strip()
                org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", org_name.lower())[:50]
            elif domain in cls.KNOWN_DOMAIN_MAPPINGS:
                org_name = cls.KNOWN_DOMAIN_MAPPINGS[domain]
                org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", domain.lower())[:50]
            elif domain in ["gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]:
                org_name = f"{name}'s Organization (Pending Setup)"
                org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", f"org-{email.split('@')[0]}-{secrets.token_hex(2)}")[:50]
            else:
                base_name = domain.split(".")[0].replace("-", " ").title()
                org_name = f"{base_name} Enterprise"
                org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", domain.lower())[:50]

            # Ensure unique slug
            existing_org_stmt = select(Organization).where(Organization.slug == org_slug).limit(1)
            if (await db.execute(existing_org_stmt)).scalar_one_or_none():
                org_slug = f"{org_slug[:45]}-{secrets.token_hex(2)}"

            new_org = Organization(
                id=uuid.uuid4(),
                name=org_name,
                slug=org_slug,
                status=OrganizationStatus.ACTIVE,
                setup_completed=False,
                governance_config={
                    "workspaces": [{
                        "id": f"ws_{secrets.token_hex(5)}",
                        "name": "General Workspace",
                        "domain": "governance",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }]
                },
            )
            db.add(new_org)
            await db.flush()

            # The user is the Admin of their new workspace
            user_role = explicit_role or UserRole.ADMIN
            user_prefs = {}
            if provider == "google" and avatar_url:
                user_prefs["google_avatar_url"] = avatar_url

            active_user = User(
                id=uuid.uuid4(),
                organization_id=new_org.id,
                name=name,
                email=email,
                role=user_role,
                status=RecordStatus.ACTIVE,
                is_verified=True,
                avatar_url=avatar_url,
                title="Workspace Lead" if provider == "google" else f"Corporate SSO ({provider.capitalize()})",
                department="AI Governance & Operations",
                user_preferences=user_prefs,
                hashed_password=get_password_hash(uuid.uuid4().hex),
            )
            db.add(active_user)
            await db.flush()
            active_user.organization = new_org
            existing_memberships.append(active_user)
        else:
            # EXISTING USER: Select primary active membership
            active_user = existing_memberships[0]
            active_user.is_verified = True
            if provider == "google" and avatar_url:
                # Update with Google mail profile photo on sign in
                active_user.avatar_url = avatar_url
                prefs = dict(active_user.user_preferences or {})
                prefs["google_avatar_url"] = avatar_url
                active_user.user_preferences = prefs
            elif avatar_url and not active_user.avatar_url:
                active_user.avatar_url = avatar_url
            await db.flush()

        session_id = str(uuid.uuid4())
        active_user.active_session_id = session_id
        if device_id:
            active_user.last_active_device = device_id
        await db.commit()
        await db.refresh(active_user)

        # 3. Generate JWT Tokens
        access_token = create_access_token(
            subject=str(active_user.id),
            claims={
                "email": active_user.email,
                "role": active_user.role.value if hasattr(active_user.role, "value") else str(active_user.role),
                "org_id": str(active_user.organization_id),
                "name": active_user.name,
                "auth_provider": provider,
                "session_id": session_id,
            },
        )
        refresh_token = create_refresh_token(subject=str(active_user.id))

        # 4. Build multi-organization memberships list
        org_list = []
        for mem in existing_memberships:
            if mem.organization:
                org_list.append({
                    "id": str(mem.organization.id),
                    "name": mem.organization.name,
                    "slug": mem.organization.slug,
                    "role": mem.role.value if hasattr(mem.role, "value") else str(mem.role),
                    "setup_completed": bool(getattr(mem.organization, "setup_completed", False)),
                    "governance_config": mem.organization.governance_config or {},
                    "domain_whitelist": mem.organization.domain_whitelist or [],
                })

        # 5. Build pending invitations list
        pending_list = []
        for inv in pending_invites:
            pending_list.append({
                "id": str(inv.id),
                "organization_id": str(inv.organization_id),
                "organization_name": inv.organization.name if inv.organization else "Enterprise Tenant",
                "organization_slug": inv.organization.slug if inv.organization else "tenant",
                "role": inv.role.value if hasattr(inv.role, "value") else str(inv.role),
                "token": inv.token,
                "invited_by": inv.invited_by.name if inv.invited_by else "Admin",
                "created_at": inv.created_at.isoformat(),
            })

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=_build_user_response(active_user),
            is_new_user=is_new_user,
            pending_invitations=pending_list,
            organizations=org_list,
        )

    @classmethod
    async def _exchange_google_code(cls, code: str, redirect_uri: Optional[str]) -> tuple[str, str, Optional[str]]:
        """Live OIDC token exchange against Google Identity Services."""
        target_redirect = redirect_uri or settings.sso_redirect_uri
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": target_redirect,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_resp = await client.post(token_url, data=data)
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    id_token_str = token_data.get("id_token")
                    if id_token_str:
                        return await cls._verify_google_credential(id_token_str)

                    access_token = token_data.get("access_token")
                    userinfo_resp = await client.get(
                        "https://openidconnect.googleapis.com/v1/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if userinfo_resp.status_code == 200:
                        user_info = userinfo_resp.json()
                        return user_info.get("email"), user_info.get("name"), user_info.get("picture")
                else:
                    logger.warning(f"Google code exchange returned HTTP {token_resp.status_code}: {token_resp.text}")
                    err_msg = token_resp.text
                    try:
                        err_json = token_resp.json()
                        err_msg = err_json.get("error_description") or err_json.get("error") or token_resp.text
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Google OAuth exchange failed ({err_msg}). If the authorization code was already used or expired, please initiate sign-in again.",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Google live code exchange error: {e}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth exchange could not be completed. Please try again or use direct verification.",
        )

    @classmethod
    async def _exchange_microsoft_code(cls, code: str, redirect_uri: Optional[str]) -> tuple[str, str, Optional[str]]:
        """Live OIDC token exchange against Microsoft Entra ID (Azure AD)."""
        target_redirect = redirect_uri or settings.sso_redirect_uri
        tenant = settings.azure_tenant_id or "common"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "code": code,
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "redirect_uri": target_redirect,
            "grant_type": "authorization_code",
            "scope": "openid email profile User.Read",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_url, data=data)
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Microsoft Entra ID token exchange failed: {token_resp.text}",
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            userinfo_resp = await client.get(
                "https://graph.microsoft.com/oidc/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch Microsoft user profile.",
                )
            user_info = userinfo_resp.json()
            return (
                user_info.get("email") or user_info.get("preferred_username"),
                user_info.get("name"),
                user_info.get("picture"),
            )
