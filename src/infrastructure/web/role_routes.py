from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel

from src.application.role.use_cases import CreateRole, ListRoles, UpdateRolePermissions
from src.domain.role.entities import Role
from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.value_objects import Permission, RoleId
from src.infrastructure.persistence.role_repository import SqlAlchemyRoleRepository

tracer = trace.get_tracer(__name__)


class CreateRoleRequest(BaseModel):
    name: str
    permissions: list[str] = []


class UpdateRolePermissionsRequest(BaseModel):
    grant: list[str] = []
    revoke: list[str] = []


def _serialize_role(role: Role) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "permissions": sorted(str(permission) for permission in role.permissions),
    }


def build_role_router(request_counter, logger, require_role_manage, get_session) -> APIRouter:
    router = APIRouter(prefix="/roles", tags=["roles"])

    @router.get("")
    async def list_roles(
        _=Depends(require_role_manage), session=Depends(get_session)
    ):
        with tracer.start_as_current_span("list_roles") as span:
            roles = await ListRoles(SqlAlchemyRoleRepository(session)).execute()
            span.set_attribute("roles.count", len(roles))
            logger.info("Listed %d roles", len(roles))

        request_counter.add(1, {"endpoint": "/roles"})

        return [_serialize_role(role) for role in roles]

    @router.post("", status_code=201)
    async def create_role(
        body: CreateRoleRequest,
        _=Depends(require_role_manage),
        session=Depends(get_session),
    ):
        permissions = frozenset(Permission.parse(p) for p in body.permissions)

        with tracer.start_as_current_span("create_role") as span:
            role = await CreateRole(SqlAlchemyRoleRepository(session)).execute(
                body.name, permissions
            )
            span.set_attribute("role.id", str(role.id))
            logger.info("Created role %s", role.name)

        request_counter.add(1, {"endpoint": "/roles"})

        return _serialize_role(role)

    @router.patch("/{role_id}/permissions")
    async def update_role_permissions(
        role_id: UUID,
        body: UpdateRolePermissionsRequest,
        _=Depends(require_role_manage),
        session=Depends(get_session),
    ):
        grant = frozenset(Permission.parse(p) for p in body.grant)
        revoke = frozenset(Permission.parse(p) for p in body.revoke)

        try:
            with tracer.start_as_current_span("update_role_permissions") as span:
                try:
                    role = await UpdateRolePermissions(
                        SqlAlchemyRoleRepository(session)
                    ).execute(RoleId(role_id), grant=grant, revoke=revoke)
                except RoleNotFoundError as error:
                    raise HTTPException(status_code=404, detail=str(error)) from error
                span.set_attribute("role.id", str(role.id))
                logger.info("Updated permissions for role %s", role.name)
        finally:
            request_counter.add(1, {"endpoint": "/roles/{id}/permissions"})

        return _serialize_role(role)

    return router
