from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel

from src.application.authorization.use_cases import GetEffectivePermissions
from src.application.user.use_cases import ListUsers, SetUserRoles
from src.domain.role.entities import Role
from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.value_objects import Permission, RoleId
from src.domain.user.entities import User
from src.domain.user.exceptions import UserNotFoundError
from src.domain.user.value_objects import UserId
from src.infrastructure.persistence.role_repository import SqlAlchemyRoleRepository
from src.infrastructure.persistence.user_repository import SqlAlchemyUserRepository

tracer = trace.get_tracer(__name__)


class SetUserRolesRequest(BaseModel):
    role_ids: list[UUID]


def _serialize_user(user: User, permissions: frozenset[Permission]) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role_ids": sorted(str(role_id) for role_id in user.role_ids),
        "permissions": sorted(str(permission) for permission in permissions),
    }


def _effective_permissions(user: User, roles_by_id: dict[RoleId, Role]) -> frozenset[Permission]:
    permissions: frozenset[Permission] = frozenset()
    for role_id in user.role_ids:
        role = roles_by_id.get(role_id)
        if role is not None:
            permissions |= role.permissions
    return permissions


def build_user_router(
    request_counter, logger, get_current_user, require_user_manage, get_session
) -> APIRouter:
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get("/me")
    async def get_my_profile(
        user: User = Depends(get_current_user), session=Depends(get_session)
    ):
        with tracer.start_as_current_span("get_my_profile") as span:
            permissions = await GetEffectivePermissions(
                SqlAlchemyRoleRepository(session)
            ).execute(user)
            span.set_attribute("user.id", str(user.id))
            logger.info("Fetched profile for user %s", user.external_subject)

        request_counter.add(1, {"endpoint": "/users/me"})

        return _serialize_user(user, permissions)

    @router.get("")
    async def list_users(
        _: User = Depends(require_user_manage), session=Depends(get_session)
    ):
        with tracer.start_as_current_span("list_users") as span:
            users = await ListUsers(SqlAlchemyUserRepository(session)).execute()
            roles_by_id = {
                role.id: role
                for role in await SqlAlchemyRoleRepository(session).list_all()
            }
            span.set_attribute("users.count", len(users))
            logger.info("Listed %d users", len(users))

        request_counter.add(1, {"endpoint": "/users"})

        return [
            _serialize_user(user, _effective_permissions(user, roles_by_id))
            for user in users
        ]

    @router.patch("/{user_id}/roles")
    async def set_user_roles(
        user_id: UUID,
        body: SetUserRolesRequest,
        _: User = Depends(require_user_manage),
        session=Depends(get_session),
    ):
        role_ids = frozenset(RoleId(role_id) for role_id in body.role_ids)

        try:
            with tracer.start_as_current_span("set_user_roles") as span:
                role_repository = SqlAlchemyRoleRepository(session)
                try:
                    user = await SetUserRoles(
                        SqlAlchemyUserRepository(session), role_repository
                    ).execute(UserId(user_id), role_ids)
                except (UserNotFoundError, RoleNotFoundError) as error:
                    raise HTTPException(status_code=404, detail=str(error)) from error

                permissions = await GetEffectivePermissions(role_repository).execute(
                    user
                )
                span.set_attribute("user.id", str(user.id))
                logger.info("Set roles for user %s", user.id)
        finally:
            request_counter.add(1, {"endpoint": "/users/{id}/roles"})

        return _serialize_user(user, permissions)

    return router
