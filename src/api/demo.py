"""Login de demonstracao: um token por perfil, SO quando DEMO_LOGIN=1 (desligado por padrao; responde 404 caso contrario).

Existe para o avaliador ver cada perfil sem emitir token na linha de comando. Os tokens valem 1 h, usam o mesmo JWT_SECRET e dao
os privilegios reais do perfil sobre dados sinteticos: nunca habilite em ambiente com dados reais ou exposto a rede publica.
"""
from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .security import issue_token

DEMO_TTL_SECONDS = 3600
router = APIRouter(prefix="/auth", tags=["auth"])


def demo_enabled() -> bool:
    return os.environ.get("DEMO_LOGIN") == "1"


class DemoStatus(BaseModel):
    enabled: bool


class DemoToken(BaseModel):
    token: str
    role: Literal["analista", "gestor", "auditor"]
    expires_in: int


@router.get("/demo", response_model=DemoStatus, summary="Informa se o login de demonstracao esta habilitado")
def demo_status() -> DemoStatus:
    return DemoStatus(enabled=demo_enabled())


@router.post("/demo/{role}", response_model=DemoToken, summary="Token de demonstracao (1 h) para o perfil; 404 se DEMO_LOGIN!=1")
def demo_token(role: Literal["analista", "gestor", "auditor"]) -> DemoToken:
    if not demo_enabled():
        raise HTTPException(status_code=404, detail="Login de demonstracao desabilitado")
    try:
        token = issue_token(f"demo.{role}", role, DEMO_TTL_SECONDS)
    except ValueError:
        raise HTTPException(status_code=503, detail="JWT_SECRET ausente ou fraco") from None
    return DemoToken(token=token, role=role, expires_in=DEMO_TTL_SECONDS)
