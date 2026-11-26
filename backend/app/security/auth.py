
"""Verify Supabase JWTs and map them to provisioned JurisMind users."""

from functools import lru_cache
from typing import Any
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.tenant import AppUser


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _jwks_client(url: str) -> PyJWKClient:
    """Cache Supabase public signing keys, not user credentials."""
    return PyJWKClient(url, cache_keys=True)


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify JWT signature, issuer, audience, expiry and UUID subject."""

    settings = get_settings()

    if not settings.supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured",
        )

    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    try:
        key = _jwks_client(
            f"{issuer}/.well-known/jwks.json"
        ).get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )

        claims["sub"] = str(uuid.UUID(claims["sub"]))
        return claims

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        ) from exc



def get_verified_user_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Verify a Supabase identity without requiring an existing app_users row.

    Used only by the narrowly scoped first-time provisioning endpoint.
    All ordinary workspace routes continue to depend on get_current_user.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    return verify_access_token(credentials.credentials)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Require a verified token and a separately provisioned internal profile."""

    # 1. Require a valid Bearer token.
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    # 2. Verify the Supabase access token.
    claims = verify_access_token(credentials.credentials)
    external_id = claims["sub"]

    # 3. Print safe information about the live API session.
    # Never print the access token or database password.
    print("API AUTH - SESSION ID:", id(db))
    print(
        "API AUTH - DATABASE CONNECTION:",
        db.get_bind().url.render_as_string(hide_password=True),
    )
    print("API AUTH - IN TRANSACTION:", db.in_transaction())

    # 4. Set the verified Supabase identity for transaction-local RLS checks.
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(
            text(
                "SELECT set_config('app.supabase_user_id', :subject, true)"
            ),
            {"subject": external_id},
        )

        # 5. Test the identity and RLS visibility inside this exact API request.
        diagnostic = db.execute(
            text("""
                SELECT
                    current_database() AS database_name,
                    current_user AS database_role,
                    current_setting(
                        'app.supabase_user_id',
                        true
                    ) AS identity_context,
                    (
                        current_setting(
                            'app.supabase_user_id',
                            true
                        )::uuid = CAST(:subject AS uuid)
                    ) AS identity_matches,
                    (
                        SELECT count(*)
                        FROM public.app_users
                    ) AS visible_accounts,
                    (
                        SELECT count(*)
                        FROM public.app_users
                        WHERE supabase_user_id = CAST(:subject AS uuid)
                    ) AS matching_accounts,
                    pg_backend_pid() AS backend_pid
            """),
            {"subject": external_id},
        ).mappings().one()

        print("API AUTH - POLICY TEST:", dict(diagnostic))

    # 6. Compare raw SQL and ORM account lookup in the same session.
    raw_user = db.execute(
        text("""
            SELECT id, email, supabase_user_id
            FROM public.app_users
            WHERE supabase_user_id = CAST(:subject AS uuid)
        """),
        {"subject": external_id},
    ).mappings().first()

    print(
        "API AUTH - RAW SQL ACCOUNT:",
        dict(raw_user) if raw_user else None,
    )

    # 7. Perform the SQLAlchemy ORM account lookup.
    user = db.scalar(
        select(AppUser).where(
            AppUser.supabase_user_id == uuid.UUID(external_id)
        )
    )

    print("API AUTH - ORM ACCOUNT FOUND:", user is not None)

    # 8. Never automatically provision accounts using JWT email claims.
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JurisMind account is not provisioned",
        )

    # 9. Set the internal JurisMind identity for subsequent tenant RLS checks.
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(
            text(
                "SELECT set_config('app.user_id', :user_id, true)"
            ),
            {"user_id": user.id},
        )

    print("API AUTH - INTERNAL USER ID:", user.id)
    print("API AUTH - AUTHENTICATION SUCCESSFUL")

    # 10. Return verified claims and internal JurisMind identity.
    return {
        **claims,
        "app_user_id": user.id,
        "supabase_user_id": external_id,
    }
