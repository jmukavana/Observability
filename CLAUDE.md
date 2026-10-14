# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A FastAPI service (`observability`) built to demonstrate/exercise the LGTM observability
stack (Loki, Grafana, Tempo, Prometheus) via the OpenTelemetry Collector, plus a DDD-structured
`User` bounded context secured by Keycloak (OIDC). The app emits traces, metrics, and logs over
OTLP; the collector fans them out to Tempo (traces), Prometheus (metrics), and Loki (logs), and
Grafana visualizes all three with cross-linked datasources (trace-to-metrics, service map).

The project uses `uv` for dependency management (Python >=3.13).

## Commands

```bash
# Install dependencies
uv sync

# Run the API locally (reload enabled) — requires Postgres + Keycloak reachable,
# see "Running the full stack" below
uv run python -m src.main
# or
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Apply database migrations (Postgres must be reachable at Settings.database_url)
uv run alembic upgrade head
uv run alembic revision -m "description"   # new migration (hand-written, not autogenerate —
                                            # autogenerate needs a live DB connection)

# Run tests
uv run pytest
uv run pytest path/to/test_file.py::test_name   # single test

# Lint / format
uv run ruff check .
uv run black .

# Type check
uv run mypy src

# Full observability + auth + db stack (collector, Prometheus, Tempo, Loki, Promtail,
# Grafana, Postgres, Keycloak, and the app)
docker compose up --build
```

Service endpoints when running via `docker compose`:
- API: http://localhost:8001
- Grafana: http://localhost:4000
- Prometheus: http://localhost:4090
- Tempo: http://localhost:4200
- Loki: http://localhost:4100
- OTel Collector: OTLP gRPC 4317 / HTTP 4318
- Postgres: localhost:4432 (db/user/password: `observability`)
- Keycloak: http://localhost:4080 (admin console login `admin`/`admin`)

The app talks to the collector via `OTEL_EXPORTER_OTLP_ENDPOINT` (defaults to
`http://localhost:4318`, overridden to `http://otel-collector:4318` in docker-compose).
DB and OIDC settings are read by `src/infrastructure/config.py` (`DATABASE_URL`,
`OIDC_ISSUER`, `OIDC_AUDIENCE`), defaulting to the docker-compose host port mappings above
so the app also runs standalone against `docker compose up postgres keycloak`.

### Running the full stack / getting a token to call the API

```bash
docker compose up -d postgres keycloak otel-collector
uv run alembic upgrade head

# Keycloak realm "observability" is auto-provisioned from
# configs/keycloak/realm-export.json on first boot (client "observability-api",
# demo users admin-demo/admin-demo and member-demo/member-demo).
curl -s -X POST http://localhost:4080/realms/observability/protocol/openid-connect/token \
  -d grant_type=password -d client_id=observability-api \
  -d username=admin-demo -d password=admin-demo | jq -r .access_token
```

Use the resulting token as `Authorization: Bearer <token>` against `GET /users/me` (any
authenticated user), `GET /users` / `PATCH /users/{id}/roles` (require `user:manage`), and
`GET|POST /roles` / `PATCH /roles/{id}/permissions` (require `role:manage`) — the seeded
`admin` role has both. Example: create a role and grant it a permission —

```bash
TOKEN=$(curl -s -X POST http://localhost:4080/realms/observability/protocol/openid-connect/token \
  -d grant_type=password -d client_id=observability-api \
  -d username=admin-demo -d password=admin-demo | jq -r .access_token)
curl -s -X POST http://localhost:8000/roles -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Claims Manager", "permissions": ["claim:create", "claim:approve"]}'
```

## Architecture

The `src/` tree follows a clean/hexagonal-architecture layout. There are no `__init__.py`
files anywhere under `src/` — packages are implicit namespace packages; keep new modules
consistent with that (don't add `__init__.py`). Because internal imports use absolute
`from src.foo.bar import ...` paths, `[tool.mypy]` in `pyproject.toml` sets
`explicit_package_bases = true` (otherwise mypy misresolves modules reachable under two
names) and `[tool.pytest.ini_options]` sets `pythonpath = ["."]` (otherwise `src` isn't
importable from `tests/`).

- `src/domain/` — entities, value objects, and repository ports (interfaces only, no I/O).
  - `src/domain/user/`: `entities.py` (`User` aggregate — frozen dataclass, references
    roles by id via `role_ids: frozenset[RoleId]`, `with_roles()` wither), `value_objects.py`
    (`UserId`), `repository.py` (abstract `UserRepository` port: `get_by_external_subject`,
    `get_by_id`, `add`, `update`, `list_all`), `exceptions.py` (`UserNotFoundError`).
  - `src/domain/role/`: `entities.py` (`Role` aggregate — id, name, `permissions:
    frozenset[Permission]`, with `grant()`/`revoke()`/`has_permission()` withers),
    `value_objects.py` (`Permission` — validated `resource:action` value object with
    `Permission.parse("x:y")`; `RoleId`), `repository.py` (abstract `RoleRepository` port),
    `exceptions.py` (`RoleNotFoundError`).
  - `User` and `Role` are separate aggregates linked only by id (not embedded) — a role's
    permissions can change independently of any user holding it, and a `User` doesn't cache
    a stale copy of its roles' permissions.
- `src/application/` — use cases, depending only on domain ports.
  - `src/application/user/use_cases.py`: `SyncUserFromIdentity` (get-or-creates the local
    `User` for a federated IdP identity, resolving Keycloak's realm role *names* to internal
    `Role` ids by name as a one-time bootstrap seed at first login only — see "Auth/RBAC
    conventions" below) and `ListUsers`. `SetUserRoles` (validates the given role ids exist,
    then replaces a user's `role_ids` wholesale — this is the only role-assignment
    operation; there's no separate incremental grant/revoke-a-role-from-a-user use case).
  - `src/application/role/use_cases.py`: `CreateRole`, `UpdateRolePermissions` (grant/revoke
    permission sets on an existing role), `ListRoles`.
  - `src/application/authorization/use_cases.py`: `GetEffectivePermissions(user)` — the only
    place that resolves a user's `role_ids` into an actual permission set (loads the
    matching `Role`s via `RoleRepository.get_by_ids` and unions their permissions). This
    cross-aggregate computation deliberately lives here, not on either entity.
- `src/infrastructure/` — adapters to the outside world:
  - `infrastructure/observability/` — OTel bootstrap: `logging.py`, `metrics.py`,
    `tracing.py`, each exposing a single `configure_*()` function called once from
    `src/main.py` during app startup.
  - `infrastructure/config.py` — `pydantic-settings` `Settings` (`database_url`,
    `oidc_issuer`, `oidc_audience`, derived `oidc_jwks_url`), via cached `get_settings()`.
  - `infrastructure/db.py` — async SQLAlchemy engine/session setup
    (`create_db_engine`/`create_session_factory`/`get_session_dependency`), instruments the
    engine with `SQLAlchemyInstrumentor` the same way `main.py` instruments FastAPI.
  - `infrastructure/persistence/user_repository.py` / `role_repository.py` — `UserModel` /
    `RoleModel` (SQLModel tables) + `SqlAlchemyUserRepository` / `SqlAlchemyRoleRepository`.
    Both store their many-valued fields (`role_ids` on `UserModel`, `permissions` on
    `RoleModel`) as a comma-joined string column rather than a join table — a deliberate
    simplification at this scale; if that ever needs real relational queries, introduce a
    proper `user_roles` join table instead of parsing the string further. Repositories
    commit their own writes (no separate unit-of-work); `update()` uses `session.merge()`.
  - `infrastructure/auth/token_validator.py` — `KeycloakTokenValidator`: validates a bearer
    JWT's signature/issuer/audience against Keycloak's JWKS endpoint (`PyJWKClient`),
    extracting `sub`/`email`/realm role *names* (raw strings, unfiltered) into `TokenClaims`.
  - `infrastructure/auth/dependencies.py` — FastAPI dependencies built from already-wired
    collaborators: `build_current_user_dependency(token_validator, get_session, logger)`
    returns a `get_current_user` dependency that validates the bearer token, then runs
    `SyncUserFromIdentity` to resolve/create the local `User`; `require_permission(permission,
    get_current_user, get_session)` computes the user's effective permissions fresh on
    *every* request via `GetEffectivePermissions` (no caching) and 403s if the required
    permission isn't present — this is what makes role/permission changes take effect
    immediately without re-login.
  - `infrastructure/web/routes.py` / `user_routes.py` / `role_routes.py` — FastAPI routing.
    `register_routes()`, `build_user_router()`, `build_role_router()` take already-built
    collaborators (`request_counter`, `logger`, `get_current_user`, `require_user_manage`,
    `require_role_manage`, `get_session`) as explicit parameters and close over them in
    route handlers, rather than using global state or FastAPI's DI container directly in
    the composition root.

`src/main.py` is the composition root: it builds settings, the DB engine/session factory,
the Keycloak token validator, and the `get_current_user`/`require_user_manage`/
`require_role_manage` dependencies, then wires them all into `register_routes()`. This
manual-wiring style (build once in `main.py`, pass down as explicit parameters/closures) is
the established convention here — `dependency-injector` is a listed dependency but is *not*
used; don't introduce its container as a second wiring mechanism.

### Auth/RBAC conventions

- Identity is federated: Keycloak owns credentials, the app never stores passwords. The
  local `users` table exists to hold role assignments/profile data keyed by the IdP's `sub`
  claim (`external_subject`), populated lazily on first authenticated request via
  `SyncUserFromIdentity` — there's no separate signup/registration endpoint.
- **The app, not Keycloak, is the source of truth for authorization.** Keycloak's realm
  roles are consulted *only* at first login, as a one-time bootstrap seed (matched by name
  against the `roles` table via `RoleRepository.get_by_name` — this is why the seeded
  built-in roles are literally named `"admin"` and `"member"`, matching the Keycloak realm
  roles in `configs/keycloak/realm-export.json`). After that first sync, role changes in
  Keycloak have no effect; all subsequent role assignment happens exclusively through
  `PATCH /users/{id}/roles` (needs `user:manage`). This avoids the alternative of two
  competing authorities for "what can this user do."
- Permissions are **fully dynamic strings** (`resource:action`, validated by
  `Permission.parse`) — there is no closed enum of permissions. Anyone with `role:manage`
  can invent a new permission by naming it in `POST /roles` or a `grant` list; nothing stops
  a typo from creating a permission no route ever checks. Roles are equally dynamic — the
  four seeded roles (`admin`, `member`, `Claims Manager`, `Auditor` with `claim:create`/
  `claim:approve`/`claim:view`/`report:view`) are just example data proving the shape works,
  not a fixed set. There is currently no actual `claim`/`report` business resource — those
  permission strings aren't checked by any route except as illustrative seed data.
  `role:manage` and `user:manage` are the only two permissions actually enforced by code
  (gating the role-management and user/role-assignment endpoints, respectively) — that
  pairing is itself a bootstrap-safety concern: whatever seed data exists must grant the
  first admin both, or no one could ever create further roles or assign them.
- `configs/keycloak/realm-export.json` is dev-only fixture data (plaintext demo passwords,
  `sslRequired: none`, public client with direct-access-grants enabled for easy `curl`
  testing) — do not model production Keycloak config on this file. Keycloak itself has no
  persistent volume in `docker-compose.yml`, so recreating that container wipes and
  re-imports the realm from scratch, generating fresh random Keycloak user ids (`sub`
  claims) each time — expect a new local `User` row to be created on next login after that,
  not a match against the previous one.

### Observability conventions

- Tracing, metrics, and logging are each configured independently in
  `infrastructure/observability/*.py` and return the primitive the rest of the app needs
  (a `Logger` from `configure_logging()`, a `Counter` from `configure_metrics()`).
  `configure_tracing()` sets the global tracer provider and also returns a tracer, though
  callers elsewhere have favored calling `trace.get_tracer(__name__)` directly instead of
  using that return value.
  Metric/trace exporters read `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` /
  `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, falling back to `OTEL_EXPORTER_OTLP_ENDPOINT`.
- The pattern for wiring a new route into observability is: open a span with
  `tracer.start_as_current_span(...)`, set attributes, log through an injected `logger`,
  and increment a request counter with an `{"endpoint": ...}` label — follow this rather
  than introducing a second metrics/tracing setup path.
- The OTel Collector pipeline (`configs/otelcol/otelcol.yml`) fans traces to
  `otlp/tempo` + `debug`, metrics to `prometheus` + `debug`, and logs to `debug` only
  (no log backend wired into the collector pipeline yet — Loki ingestion instead goes
  through Promtail scraping Docker container logs directly, per
  `configs/promtail/promtail.yml`).

## Known gaps (don't assume these exist)

- There is no `[tool.ruff]` or `[tool.black]` configuration in `pyproject.toml` — those two
  tools run with their default settings. (`[tool.pytest.ini_options]` and `[tool.mypy]` do
  exist, see above.)
- Only the `User`/`Role`/auth bounded contexts are implemented; there's no other
  domain/application code yet (no actual `claim`/`report` resources — see above).
- Alembic migrations are hand-written, not autogenerated — there's no live DB available in
  most dev/CI contexts to run `alembic revision --autogenerate` against.
- No pagination on `GET /users` or `GET /roles` — both load every row. Fine at demo scale,
  would need addressing before this became a real service.
