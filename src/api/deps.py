"""Conexoes da API: leitura (papel fidelidade_ro) e trilha de auditoria (papel fidelidade_api_audit)."""
from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated

import psycopg
from fastapi import Depends, HTTPException
from psycopg.rows import dict_row


def _connect(var: str, read_only: bool) -> Iterator[psycopg.Connection]:
    dsn = os.environ.get(var)
    if not dsn:
        raise HTTPException(status_code=503, detail="Banco nao configurado")
    try:
        conn = psycopg.connect(dsn, row_factory=dict_row, options="-c default_transaction_read_only=on" if read_only else None)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Banco indisponivel") from None
    try:
        yield conn
    finally:
        conn.close()


def get_conn() -> Iterator[psycopg.Connection]:
    yield from _connect("DATABASE_URL_RO", read_only=True)


def get_audit_conn() -> Iterator[psycopg.Connection]:
    yield from _connect("DATABASE_URL_AUDIT", read_only=False)


Conn = Annotated[psycopg.Connection, Depends(get_conn)]
AuditConn = Annotated[psycopg.Connection, Depends(get_audit_conn)]
