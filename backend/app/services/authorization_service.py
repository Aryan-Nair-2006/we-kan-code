"""
AuthorizationService — Phase 7

Central authorization logic. NEVER trust frontend-supplied roles or access levels.

Local dev: reads DEV_USER_ID / DEV_ROLE from environment (safe only when ENVIRONMENT=local).
Production: parses the JWT passed by API Gateway in the Authorization header.

Fail-closed: any error in auth → deny.
"""
import logging
import os
from typing import List, Optional

from fastapi import Request

from backend.app.models.auth import AuthContext
from shared.constants.access_level import AccessLevel

logger = logging.getLogger(__name__)

# Hierarchical access map: role → which access levels the role can see
_ROLE_ACCESS_LEVELS: dict[str, List[AccessLevel]] = {
    "admin": [AccessLevel.PUBLIC, AccessLevel.TEAM, AccessLevel.DEVELOPER, AccessLevel.ADMIN],
    "developer": [AccessLevel.PUBLIC, AccessLevel.TEAM, AccessLevel.DEVELOPER],
    "team": [AccessLevel.PUBLIC, AccessLevel.TEAM],
    "public": [AccessLevel.PUBLIC],
}

_VALID_ROLES = set(_ROLE_ACCESS_LEVELS.keys())


class AuthorizationService:
    """
    Single entry point for authentication and authorization decisions.
    """

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local").lower()

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def build_auth_context(self, request: Optional[Request] = None) -> AuthContext:
        """
        Build an AuthContext from the incoming request.

        - In production: parse the JWT from the Authorization header.
          API Gateway should have already validated the JWT signature;
          we just decode the claims without re-verifying (trust the gateway).
        - In local dev (ENVIRONMENT=local): use DEV_USER_ID / DEV_ROLE env vars.

        Raises ValueError on any authentication failure (caller should return 401/403).
        """
        if self.environment == "local":
            return self._build_local_auth_context()
        else:
            return self._build_production_auth_context(request)

    def build_auth_context_from_event(self, event: Optional[dict] = None) -> AuthContext:
        """
        Build an AuthContext from a direct Lambda event or API Gateway event.
        - In local dev: returns local context with DEV_ROLE.
        - In production: extracts claims from requestContext.authorizer or Authorization header.
        """
        if self.environment == "local":
            return self._build_local_auth_context()

        if not event or not isinstance(event, dict):
            raise ValueError("No event dictionary provided for authentication")

        # 1. API Gateway Authorizer context (HTTP API / REST API)
        req_ctx = event.get("requestContext", {})
        authorizer = req_ctx.get("authorizer", {})
        claims = authorizer.get("jwt", {}).get("claims") or authorizer.get("claims")

        if claims and isinstance(claims, dict):
            user_id = claims.get("sub") or claims.get("username")
            if not user_id:
                raise ValueError("Claims missing 'sub'")
            email = claims.get("email")
            role = (
                claims.get("custom:role")
                or self._role_from_groups(claims.get("cognito:groups", []))
                or "public"
            ).lower()
            if role not in _VALID_ROLES:
                role = "public"
            return AuthContext(
                user_id=user_id,
                role=role,
                access_levels=_ROLE_ACCESS_LEVELS[role],
                email=email,
            )

        # 2. Check Authorization header
        headers = event.get("headers", {}) or {}
        auth_header = next((v for k, v in headers.items() if str(k).lower() == "authorization"), "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            if token:
                claims = self._decode_jwt_claims(token)
                user_id = claims.get("sub") or claims.get("username")
                if not user_id:
                    raise ValueError("JWT missing 'sub'")
                email = claims.get("email")
                role = (
                    claims.get("custom:role")
                    or self._role_from_groups(claims.get("cognito:groups", []))
                    or "public"
                ).lower()
                if role not in _VALID_ROLES:
                    role = "public"
                return AuthContext(
                    user_id=user_id,
                    role=role,
                    access_levels=_ROLE_ACCESS_LEVELS[role],
                    email=email,
                )

        raise ValueError("Missing or invalid authentication in Lambda event")

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------

    def get_allowed_access_levels(self, auth_ctx: AuthContext) -> List[AccessLevel]:
        """
        Return the access levels the given AuthContext is permitted to see.
        Uses the pre-computed access_levels from the context (already set at build time).
        """
        return auth_ctx.access_levels

    def is_document_authorized(self, auth_ctx: AuthContext, doc_access_level: str) -> bool:
        """
        Returns True only if the document's access level is within what the user can see.
        Fail-closed: any missing/invalid level returns False.
        """
        try:
            normalized = doc_access_level.lower() if doc_access_level else None
            if not normalized:
                logger.warning("Document has no access_level — denying access (fail-closed)")
                return False
            allowed = {lvl.value for lvl in auth_ctx.access_levels}
            return normalized in allowed
        except Exception as e:
            logger.error(f"Authorization check failed: {e} — denying (fail-closed)")
            return False

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_local_auth_context(self) -> AuthContext:
        """
        Local development auth — ONLY active when ENVIRONMENT=local.
        Uses DEV_USER_ID and DEV_ROLE env vars with safe defaults.
        """
        user_id = os.getenv("DEV_USER_ID", "demo-user")
        role = os.getenv("DEV_ROLE", "developer").lower()

        if role not in _VALID_ROLES:
            logger.warning(
                f"DEV_ROLE='{role}' is not a valid role. Defaulting to 'public' (fail-closed)."
            )
            role = "public"

        access_levels = _ROLE_ACCESS_LEVELS[role]
        logger.info(f"[LOCAL AUTH] user_id={user_id} role={role} access_levels={[a.value for a in access_levels]}")
        return AuthContext(
            user_id=user_id,
            role=role,
            access_levels=access_levels,
        )

    def _build_production_auth_context(self, request: Optional[Request]) -> AuthContext:
        """
        Production auth — extract JWT claims from the Authorization header.
        API Gateway with a Cognito JWT Authorizer has already validated the token;
        we extract claims from the decoded token payload.

        Falls back to parsing the raw Bearer token for sub/email/custom claims.
        """
        if request is None:
            raise ValueError("No request object available for production auth")

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise ValueError("Missing or malformed Authorization header")

        token = auth_header[len("Bearer "):]
        if not token:
            raise ValueError("Empty Bearer token")

        try:
            claims = self._decode_jwt_claims(token)
        except Exception as e:
            logger.error(f"JWT decode failed: {e}")
            raise ValueError(f"Invalid JWT: {e}")

        user_id = claims.get("sub") or claims.get("username")
        if not user_id:
            raise ValueError("JWT missing 'sub' claim")

        email = claims.get("email")

        # Preferred role source: cognito:groups, fallback: custom:role, fallback: "public"
        role = (
            self._role_from_groups(claims.get("cognito:groups", []))
            or claims.get("custom:role")
            or "public"
        ).lower()

        if role not in _VALID_ROLES:
            logger.warning(f"Unknown role '{role}' in JWT — defaulting to 'public' (fail-closed)")
            role = "public"

        access_levels = _ROLE_ACCESS_LEVELS[role]
        return AuthContext(
            user_id=user_id,
            role=role,
            access_levels=access_levels,
            email=email,
        )

    @staticmethod
    def _decode_jwt_claims(token: str) -> dict:
        """
        Decode JWT payload WITHOUT signature verification.
        Signature verification is API Gateway's responsibility.
        Only decodes the base64url payload section.
        """
        import base64
        import json

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT does not have 3 parts")

        payload_b64 = parts[1]
        # Base64url → standard base64
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)

    @staticmethod
    def _role_from_groups(groups: list) -> Optional[str]:
        """
        Derive a role from Cognito group membership.
        Priority: admin > developer > team > public.
        """
        if not groups:
            return None
        if isinstance(groups, str):
            groups = [groups]
        group_set = {str(g).lower() for g in groups}
        for role in ("admin", "developer", "team", "public"):
            if role in group_set:
                return role
        return None


def get_required_auth_context(request: Request) -> AuthContext:
    """
    Reusable FastAPI helper/dependency for protected endpoints.
    - Local development (ENVIRONMENT=local): returns dev auth context.
    - Production: extracts & validates claims from API Gateway / JWT.
    - Failure: logs metric and raises HTTPException(401, 'Authentication required').
    """
    from fastapi import HTTPException
    from backend.app.services.metrics_service import MetricsService

    svc = AuthorizationService()
    try:
        return svc.build_auth_context(request)
    except (ValueError, Exception) as e:
        logger.warning(f"Authentication failed: {e}")
        try:
            MetricsService().record_authentication_failure()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Authentication required")

