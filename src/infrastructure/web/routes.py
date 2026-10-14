from fastapi import APIRouter
from opentelemetry import trace

from src.infrastructure.web.role_routes import build_role_router
from src.infrastructure.web.user_routes import build_user_router

router = APIRouter()

tracer = trace.get_tracer(__name__)


def register_routes(
    request_counter,
    logger,
    get_current_user,
    require_user_manage,
    require_role_manage,
    get_session,
):
    @router.get("/")
    async def root():
        with tracer.start_as_current_span(
            "custom_db_query_span"
        ) as span:
            span.set_attribute(
                "custom.attribute",
                "some_value",
            )

            logger.info("Executing database query...")

        request_counter.add(
            1,
            {"endpoint": "/"},
        )

        logger.info("Root endpoint was called!")

        return {
            "message": "Observability data sent to LTGM"
        }

    router.include_router(
        build_user_router(
            request_counter=request_counter,
            logger=logger,
            get_current_user=get_current_user,
            require_user_manage=require_user_manage,
            get_session=get_session,
        )
    )
    router.include_router(
        build_role_router(
            request_counter=request_counter,
            logger=logger,
            require_role_manage=require_role_manage,
            get_session=get_session,
        )
    )

    return router
