from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SSOProviderInfo(BaseModel):
    id: str = Field(..., description="Provider identifier, e.g. google, microsoft, okta")
    name: str = Field(..., description="Human-readable provider name")
    protocol: str = Field(default="OIDC", description="Federation protocol: OIDC, SAML 2.0")
    configured: bool = Field(..., description="True if production client ID/secret are configured in env")
    auth_url: Optional[str] = Field(None, description="Direct authorization URL if configured")
    icon: Optional[str] = Field(None, description="Provider icon identifier")
    domains_supported: list[str] = Field(default_factory=list, description="Corporate domains explicitly pre-bound")


class SSOAuthorizeResponse(BaseModel):
    provider: str
    authorization_url: str
    state: str
    is_sandbox: bool = False
    message: Optional[str] = None


class SSOCallbackRequest(BaseModel):
    provider: str
    code: Optional[str] = None
    credential: Optional[str] = None  # Google Identity Services One-Tap / ID token
    state: Optional[str] = None
    redirect_uri: Optional[str] = None
    # Developer sandbox override parameters for instant testing
    mock_email: Optional[str] = None
    mock_name: Optional[str] = None
    mock_avatar: Optional[str] = None
    avatar_url: Optional[str] = None
    device_id: Optional[str] = None


class SSOSandboxLoginRequest(BaseModel):
    provider: str = Field(..., description="Provider identifier: google, microsoft, okta")
    corporate_email: EmailStr = Field(..., description="Corporate email address e.g. user@ssfa.com")
    full_name: Optional[str] = Field(None, description="Full name of employee")
    organization_name: Optional[str] = Field(None, description="Explicit organization or tenant name if not auto-inferred")
    role: Optional[str] = Field(None, description="Target role: admin, data_owner, reviewer, developer")
    device_id: Optional[str] = None
