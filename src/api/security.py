"""Seguranca da API: JWT (RBAC), rate limit em memoria, headers de seguranca e logs estruturados.

O token e assinado com JWT_SECRET (HS256, >= 32 caracteres, nunca no repositorio) e emitido por
`python -m src.api.tokens`. A API so valida tokens; nao ha cadastro de usuarios nem dado pessoal (sub e um apelido).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

ROLES = ("analista", "gestor", "auditor")
ISSUER = "ancora-azul-api"
ALGORITHM = "HS256"
MIN_SECRET_LEN = 32
MAX_TOKEN_LIFETIME_S = 24 * 3600
SUB_PATTERN = re.compile(r"^[a-z0-9._-]{1,64}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
DOC_PATHS = ("/docs", "/redoc")
LOG = logging.getLogger("ancora.api")

bearer = HTTPBearer(auto_error=False, description="JWT emitido por `python -m src.api.tokens`")


@dataclass(frozen=True)
class Principal:
    sub: str
    role: str


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LEN:
        raise HTTPException(status_code=503, detail="Autenticacao nao configurada")
    return secret


def issue_token(sub: str, role: str, ttl_seconds: int = 8 * 3600, secret: str | None = None) -> str:
    if role not in ROLES:
        raise ValueError(f"role invalida; use {ROLES}")
    if not SUB_PATTERN.match(sub):
        raise ValueError("sub deve casar ^[a-z0-9._-]{1,64}$ (apelido; nunca dado pessoal)")
    if not 0 < ttl_seconds <= MAX_TOKEN_LIFETIME_S:
        raise ValueError(f"ttl deve estar entre 1 e {MAX_TOKEN_LIFETIME_S} segundos")
    now = int(time.time())
    key = secret or os.environ.get("JWT_SECRET", "")
    if len(key) < MIN_SECRET_LEN:
        raise ValueError(f"JWT_SECRET precisa ter pelo menos {MIN_SECRET_LEN} caracteres")
    return jwt.encode({"iss": ISSUER, "sub": sub, "role": role, "iat": now, "exp": now + ttl_seconds}, key, algorithm=ALGORITHM)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Token ausente ou invalido", headers={"WWW-Authenticate": "Bearer"})


def current_principal(request: Request, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal:
    if creds is None:
        raise _unauthorized()
    secret = _secret()
    try:
        claims = jwt.decode(creds.credentials, secret, algorithms=[ALGORITHM], issuer=ISSUER, options={"require": ["exp", "iat", "sub", "role", "iss"]})
    except jwt.PyJWTError:
        raise _unauthorized() from None
    sub, role = claims["sub"], claims["role"]
    if (role not in ROLES or not isinstance(sub, str) or not SUB_PATTERN.match(sub)
            or not isinstance(claims["iat"], int) or claims["exp"] - claims["iat"] > MAX_TOKEN_LIFETIME_S):
        raise _unauthorized()
    principal = Principal(sub=sub, role=role)
    request.state.principal = principal
    return principal


def require(*roles: str):
    """Dependencia FastAPI: 401 sem token valido, 403 se a role nao esta entre as permitidas."""
    assert roles and set(roles) <= set(ROLES)

    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Perfil sem permissao para este recurso")
        return principal

    return dependency


class RateLimiter:
    """Janela deslizante de 60 s por (cliente, balde). Em memoria: vale por processo."""

    def __init__(self, read_per_min: int, write_per_min: int):
        self.limits = {"read": read_per_min, "write": write_per_min}
        self.hits: dict[tuple[str, str], deque[float]] = {}

    def reset(self) -> None:
        self.hits.clear()

    def check(self, client: str, bucket: str, now: float | None = None) -> int:
        """0 se permitido; senao segundos ate liberar."""
        now = time.monotonic() if now is None else now
        if len(self.hits) > 10_000:
            self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < 60}
        window = self.hits.setdefault((client, bucket), deque())
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= self.limits[bucket]:
            return max(1, int(60 - (now - window[0])) + 1)
        window.append(now)
        return 0


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def make_limiter() -> RateLimiter:
    return RateLimiter(_int_env("RATE_LIMIT_PER_MINUTE", 120), _int_env("RATE_LIMIT_WRITE_PER_MINUTE", 20))


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"  # X-Forwarded-For nao e confiavel sem proxy conhecido
        wait = self.limiter.check(client, "read" if request.method in ("GET", "HEAD") else "write")
        if wait:
            return JSONResponse({"detail": "Limite de requisicoes excedido"}, status_code=429, headers={"Retry-After": str(wait)})
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path not in DOC_PATHS:  # Swagger UI carrega scripts de CDN
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if REQUEST_ID_PATTERN.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            principal = getattr(request.state, "principal", None)
            route = request.scope.get("route")
            LOG.info(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z", "event": "http_request", "request_id": request_id,
                "method": request.method, "path": getattr(route, "path", request.url.path) if route else request.url.path,
                "status": status, "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "client": request.client.host if request.client else None,
                "sub": principal.sub if principal else None, "role": principal.role if principal else None,
            }, ensure_ascii=False))  # sem query string, headers ou corpo: evita vazar token e dados


def configure_logging() -> None:
    if not LOG.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOG.addHandler(handler)
        LOG.setLevel(logging.INFO)
        LOG.propagate = False
