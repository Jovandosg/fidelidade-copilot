"""App FastAPI somente leitura. Conecta com DATABASE_URL_RO (papel fidelidade_ro, so SELECT); queries parametrizadas."""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from psycopg import sql

from ..schemas import CustomerFeature, RouteMetric
from .agent import router as agent_router
from .deps import Conn
from .models import CustomerPage, DistributionItem, Kpis, NbaPage, NbaSummary, RoutePage
from .ops import router as ops_router
from .security import RateLimitMiddleware, RequestLogMiddleware, SecurityHeadersMiddleware, configure_logging, make_limiter, require

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CUSTOMER_SORTS = tuple(CustomerFeature.model_fields)
ROUTE_SORTS = tuple(RouteMetric.model_fields)
NBA_COLS = ("customer_id", "profile", "segment", "hvs", "risk_score", "nba_action", "nba_expected_margin_brl", "nba_requires_approval")
MAX_LIMIT = 200
CUSTOMER_ID_PATTERN = r"^C\d{6}$"
READ = [Depends(require("analista", "gestor", "auditor"))]


Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]


def _where(conds: list[sql.Composable]) -> sql.Composable:
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conds) if conds else sql.SQL("")


def _order(sort: str, allowed: tuple[str, ...], desc: bool, tiebreak: str) -> sql.Composable:
    if sort not in allowed:
        raise HTTPException(status_code=422, detail=f"sort invalido; use um de {list(allowed)}")
    return sql.SQL(" ORDER BY {} {}, {} ASC").format(sql.Identifier(sort), sql.SQL("DESC" if desc else "ASC"), sql.Identifier(tiebreak))


def _table(name: str) -> sql.Composable:
    return sql.Identifier("analytics", name)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ancora Azul - API de analytics",
        version="1.1.0",
        description="Dados SINTETICOS. Autenticacao por JWT (perfis analista, gestor, auditor); leitura do PostgreSQL e um unico POST de aprovacao que grava em ops.audit_log. Sem PII.",
    )
    configure_logging()
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]
    app.state.limiter = make_limiter()
    # o ultimo adicionado e o mais externo: CORS > log > headers > rate limit
    app.add_middleware(RateLimitMiddleware, limiter=app.state.limiter)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
                       expose_headers=["X-Request-ID", "Retry-After"], allow_credentials=False)
    app.include_router(ops_router)
    app.include_router(agent_router)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/kpis", response_model=Kpis, summary="Indicadores executivos", dependencies=READ)
    def kpis(conn: Conn, risk_threshold: Annotated[float, Query(ge=0, le=100)] = 40.0) -> Kpis:
        cf, rm = _table("customer_features"), _table("route_metrics")
        row = conn.execute(
            sql.SQL(
                """SELECT count(*) AS total_customers,
                          coalesce(avg(hvs), 0)::float8 AS avg_hvs,
                          coalesce(avg(risk_score), 0)::float8 AS avg_risk_score,
                          count(*) FILTER (WHERE risk_score >= %(t)s) AS high_risk_customers,
                          coalesce(sum(spend_12m_brl) FILTER (WHERE risk_score >= %(t)s), 0)::float8 AS spend_12m_at_risk_brl,
                          coalesce(sum(nba_expected_margin_brl), 0)::float8 AS nba_expected_margin_brl,
                          count(*) FILTER (WHERE nba_requires_approval) AS nba_pending_approval
                   FROM {}"""
            ).format(cf),
            {"t": risk_threshold},
        ).fetchone()
        ivr = conn.execute(sql.SQL("SELECT coalesce(avg(ivr), 0)::float8 AS v FROM {}").format(rm)).fetchone()["v"]

        def dist(col: str) -> list[DistributionItem]:  # col e sempre literal interno, nunca vem da requisicao
            q = sql.SQL("SELECT {c} AS k, count(*) AS n FROM {t} GROUP BY {c} ORDER BY {c}").format(c=sql.Identifier(col), t=cf)
            return [DistributionItem(key=r["k"], customers=r["n"]) for r in conn.execute(q).fetchall()]

        return Kpis(risk_threshold=risk_threshold, avg_route_ivr=ivr, profiles=dist("profile"), segments=dist("segment"), **row)

    @app.get("/clientes", response_model=CustomerPage, summary="Lista de clientes (paginada)", dependencies=READ)
    def clientes(
        conn: Conn,
        limit: Limit = 50,
        offset: Offset = 0,
        profile: Annotated[str | None, Query(pattern="^[A-E]$")] = None,
        segment: Annotated[str | None, Query(max_length=40)] = None,
        min_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
        max_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
        sort: str = "hvs",
        desc: bool = True,
    ) -> CustomerPage:
        conds: list[sql.Composable] = []
        params: dict[str, object] = {}
        for col, op, val in (("profile", "=", profile), ("segment", "=", segment), ("risk_score", ">=", min_risk), ("risk_score", "<=", max_risk)):
            if val is not None:
                key = f"p{len(params)}"
                conds.append(sql.SQL("{} {} %({})s").format(sql.Identifier(col), sql.SQL(op), sql.SQL(key)))
                params[key] = val
        where, order = _where(conds), _order(sort, CUSTOMER_SORTS, desc, "customer_id")
        total = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(_table("customer_features")) + where, params).fetchone()["n"]
        rows = conn.execute(
            sql.SQL("SELECT * FROM {}").format(_table("customer_features")) + where + order + sql.SQL(" LIMIT %(limit)s OFFSET %(offset)s"),
            {**params, "limit": limit, "offset": offset},
        ).fetchall()
        return CustomerPage(total=total, limit=limit, offset=offset, items=rows)

    @app.get("/clientes/{customer_id}", response_model=CustomerFeature, summary="Perfil e explicacao de um cliente", dependencies=READ)
    def cliente(conn: Conn, customer_id: Annotated[str, PathParam(pattern=CUSTOMER_ID_PATTERN)]) -> CustomerFeature:
        row = conn.execute(sql.SQL("SELECT * FROM {} WHERE customer_id = %s").format(_table("customer_features")), (customer_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")
        return CustomerFeature.model_validate(row)

    @app.get("/rotas", response_model=RoutePage, summary="Metricas por rota (IVR)", dependencies=READ)
    def rotas(conn: Conn, limit: Limit = 50, offset: Offset = 0, sort: str = "ivr", desc: bool = True) -> RoutePage:
        order = _order(sort, ROUTE_SORTS, desc, "route")
        total = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(_table("route_metrics"))).fetchone()["n"]
        rows = conn.execute(
            sql.SQL("SELECT * FROM {}").format(_table("route_metrics")) + order + sql.SQL(" LIMIT %(limit)s OFFSET %(offset)s"),
            {"limit": limit, "offset": offset},
        ).fetchall()
        return RoutePage(total=total, limit=limit, offset=offset, items=rows)

    @app.get("/nba", response_model=NbaPage, summary="Next Best Action (sugestoes; exigem aprovacao humana quando indicado)", dependencies=READ)
    def nba(
        conn: Conn,
        limit: Limit = 50,
        offset: Offset = 0,
        requires_approval: bool | None = None,
        action: Annotated[str | None, Query(max_length=120)] = None,
        sort: str = "nba_expected_margin_brl",
        desc: bool = True,
    ) -> NbaPage:
        conds: list[sql.Composable] = []
        params: dict[str, object] = {}
        if requires_approval is not None:
            conds.append(sql.SQL("nba_requires_approval = %(ra)s"))
            params["ra"] = requires_approval
        if action is not None:
            conds.append(sql.SQL("nba_action = %(act)s"))
            params["act"] = action
        where, order = _where(conds), _order(sort, NBA_COLS, desc, "customer_id")
        t = _table("customer_features")
        total = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(t) + where, params).fetchone()["n"]
        items = conn.execute(
            sql.SQL("SELECT {} FROM {}").format(sql.SQL(", ").join(map(sql.Identifier, NBA_COLS)), t) + where + order + sql.SQL(" LIMIT %(limit)s OFFSET %(offset)s"),
            {**params, "limit": limit, "offset": offset},
        ).fetchall()
        summary = conn.execute(
            sql.SQL(
                """SELECT nba_action, count(*) AS customers, coalesce(sum(nba_expected_margin_brl), 0)::float8 AS expected_margin_brl,
                          count(*) FILTER (WHERE nba_requires_approval) AS pending_approval
                   FROM {} GROUP BY nba_action ORDER BY expected_margin_brl DESC"""
            ).format(t)
        ).fetchall()
        return NbaPage(total=total, limit=limit, offset=offset, summary=[NbaSummary(**s) for s in summary], items=items)

    return app


app = create_app()
