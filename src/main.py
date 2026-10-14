import uvicorn
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,
)

from src.domain.role.value_objects import Permission
from src.infrastructure.auth.dependencies import (
    build_current_user_dependency,
    require_permission,
)
from src.infrastructure.auth.token_validator import KeycloakTokenValidator
from src.infrastructure.config import get_settings
from src.infrastructure.db import (
    create_db_engine,
    create_session_factory,
    get_session_dependency,
)
from src.infrastructure.observability.logging import (
    configure_logging,
)
from src.infrastructure.observability.metrics import (
    configure_metrics,
)
from src.infrastructure.observability.tracing import (
    configure_tracing,
)
from src.infrastructure.web.routes import register_routes


def create_application() -> FastAPI:
    settings = get_settings()

    # Infrastructure setup
    configure_tracing()
    logger = configure_logging()
    request_counter = configure_metrics()

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    get_session = get_session_dependency(session_factory)

    token_validator = KeycloakTokenValidator(
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        jwks_url=settings.oidc_jwks_url,
    )
    get_current_user = build_current_user_dependency(
        token_validator, get_session, logger
    )
    require_user_manage = require_permission(
        Permission.parse("user:manage"), get_current_user, get_session
    )
    require_role_manage = require_permission(
        Permission.parse("role:manage"), get_current_user, get_session
    )

    # Application bootstrap
    application = FastAPI(
        title="LTGM Observability API"
    )

    FastAPIInstrumentor.instrument_app(application)

    application.include_router(
        register_routes(
            request_counter=request_counter,
            logger=logger,
            get_current_user=get_current_user,
            require_user_manage=require_user_manage,
            require_role_manage=require_role_manage,
            get_session=get_session,
        )
    )

    return application


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
