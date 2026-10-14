from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from opentelemetry import trace

from src.application.authorization.use_cases import GetEffectivePermissions
from src.application.user.use_cases import IdentityClaims, SyncUserFromIdentity
from src.domain.role.value_objects import Permission
from src.domain.user.entities import User
from src.infrastructure.auth.token_validator import (
    InvalidTokenError,
    KeycloakTokenValidator,
)
from src.infrastructure.persistence.role_repository import SqlAlchemyRoleRepository
from src.infrastructure.persistence.user_repository import SqlAlchemyUserRepository

tracer = trace.get_tracer(__name__)


def _extract_bearer_token(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return token


def _validate_bearer_token(token_validator: KeycloakTokenValidator, token: str, logger):
    try:
        return token_validator.validate(token)
    except InvalidTokenError as error:
        logger.info("Rejected invalid bearer token: %s", error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from error


def build_current_user_dependency(
    token_validator: KeycloakTokenValidator, get_session, logger
):
    async def get_current_user(request: Request, session=Depends(get_session)) -> User:
        token = _extract_bearer_token(request)

        with tracer.start_as_current_span("authenticate_request") as span:
            claims = _validate_bearer_token(token_validator, token, logger)
            span.set_attribute("user.subject", claims.subject)

            use_case = SyncUserFromIdentity(
                SqlAlchemyUserRepository(session), SqlAlchemyRoleRepository(session)
            )
            return await use_case.execute(
                IdentityClaims(
                    subject=claims.subject,
                    email=claims.email,
                    claimed_role_names=claims.claimed_role_names,
                )
            )

    return get_current_user


def require_permission(permission: Permission, get_current_user, get_session):
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
        session=Depends(get_session),
    ) -> User:
        permissions = await GetEffectivePermissions(
            SqlAlchemyRoleRepository(session)
        ).execute(user)
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {permission}",
            )
        return user

    return dependency
