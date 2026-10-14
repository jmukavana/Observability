from dataclasses import dataclass

import jwt
from jwt import PyJWKClient


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    email: str
    claimed_role_names: frozenset[str]


class KeycloakTokenValidator:
    def __init__(self, issuer: str, audience: str, jwks_url: str) -> None:
        self._issuer = issuer
        self._audience = audience
        self._jwks_client = PyJWKClient(jwks_url)

    def validate(self, token: str) -> TokenClaims:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError(str(error)) from error

        return TokenClaims(
            subject=payload["sub"],
            email=payload.get("email", ""),
            claimed_role_names=self._extract_role_names(payload),
        )

    @staticmethod
    def _extract_role_names(payload: dict) -> frozenset[str]:
        return frozenset(payload.get("realm_access", {}).get("roles", []))
