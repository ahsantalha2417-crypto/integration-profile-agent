"""The context layer: one IntegrationProfile per partner system.

A profile captures everything an engineer (or an integration-building agent)
needs to know before building against a partner's API, plus the status of
the access we still need to secure.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER_TOKEN = "bearer_token"
    OTHER = "other"
    UNKNOWN = "unknown"


class AccessStatus(str, Enum):
    NOT_STARTED = "not_started"
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_REQUIRED = "not_required"


class Endpoint(BaseModel):
    method: str = Field(description="HTTP method, e.g. GET or POST")
    path: str = Field(description="Endpoint path, e.g. /v1/customers")
    purpose: str = Field(description="One sentence on what the endpoint is for")


class Auth(BaseModel):
    type: AuthType
    details: str = Field(description="Scopes, token lifetime, where credentials come from")


class RateLimits(BaseModel):
    documented: bool
    details: str = Field(default="", description="Limits as stated in the docs, or empty")


class Sandbox(BaseModel):
    available: bool
    how_to_get: str = Field(default="", description="How to obtain a sandbox or test account")


class PartnerProgram(BaseModel):
    required: bool = Field(description="Must we join a partner/developer program to get API access?")
    url: str = Field(default="", description="Signup page for the partner program, if found")
    notes: str = Field(default="", description="Approval steps or lead times mentioned in the docs")


class ExtractedProfile(BaseModel):
    """The part of a profile that Claude fills in from the partner's docs."""

    partner: str
    category: str = Field(description="Martech category, e.g. ecommerce platform, CRM, helpdesk, loyalty")
    base_url: str = Field(default="", description="API base URL, if documented")
    api_style: str = Field(description="REST, GraphQL, SOAP, etc.")
    auth: Auth
    key_endpoints: list[Endpoint] = Field(
        description="Up to 8 endpoints most relevant to syncing customers, orders, products, or events"
    )
    webhooks: bool = Field(description="Does the API support webhooks or event subscriptions?")
    rate_limits: RateLimits
    sandbox: Sandbox
    partner_program: PartnerProgram
    open_questions: list[str] = Field(
        description="Things the docs did not answer that someone must find out before building"
    )


class IntegrationProfile(ExtractedProfile):
    """Full context-layer record: extracted facts plus tracking fields we maintain ourselves."""

    docs_url: str
    access_status: AccessStatus = AccessStatus.NOT_STARTED
    access_requested_on: Optional[date] = None
    access_granted_on: Optional[date] = None
    last_updated: date = Field(default_factory=date.today)

    @property
    def days_to_access(self) -> Optional[int]:
        if self.access_requested_on and self.access_granted_on:
            return (self.access_granted_on - self.access_requested_on).days
        return None

    @property
    def build_ready(self) -> bool:
        """Ready for an agent to build: we have docs, auth is understood, and access is sorted."""
        access_ok = self.access_status in (AccessStatus.APPROVED, AccessStatus.NOT_REQUIRED)
        return access_ok and self.auth.type != AuthType.UNKNOWN and bool(self.key_endpoints)
