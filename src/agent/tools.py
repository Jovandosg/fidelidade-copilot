"""Ferramentas do agente: unica via de acesso a dados. Entradas e saidas validadas por Pydantic; nada de SQL livre."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ValidationError

from ..knowledge.embeddings import Embedder
from ..knowledge.search import search_rules
from ..models.nba import ACTIONS, compute_nba
from .schemas import CustomerQuery, CustomerView, EligibilityOption, EligibilityResult, RuleHit, RuleQuery, RuleSearchResult

MIN_RULE_SCORE = 0.15  # abaixo disso o trecho nao e considerado fonte para a pergunta
STOPWORDS = {"qual", "quais", "sobre", "como", "para", "com", "que", "uma", "das", "dos", "nao", "sao", "esta", "esse", "essa", "cliente",
             "melhor", "acao", "analise", "considerando", "programa", "azul", "fidelidade"}


def _words(text: str) -> set[str]:
    return set(_word_list(text))


def _word_list(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [w for w in re.findall(r"[a-z]{4,}", plain) if w not in STOPWORDS]


def content_query(text: str) -> str:
    """Remove palavras de enchimento da pergunta para a busca lexical; sem palavras de conteudo, devolve o texto original."""
    return " ".join(_word_list(text)) or text


def _shares_content_word(query: str, content: str) -> bool:
    # embeddings por hash sao ruidosos: exige ao menos uma palavra de conteudo em comum alem do score
    return bool(_words(query) & _words(content))
CUSTOMER_COLUMNS = ("customer_id, profile, segment, hvs::float8 AS hvs, risk_score::float8 AS risk_score, risk_drivers, points_balance, recency_days, "
                    "nba_action, nba_expected_margin_brl::float8 AS nba_expected_margin_brl, nba_requires_approval")
ELIGIBILITY_COLUMNS = ("customer_id, profile, risk_score::float8 AS risk_score, margin_12m_brl::float8 AS margin_12m_brl, disruptions_12m, complaints_12m, "
                       "points_balance, recency_days")


class ToolError(Exception):
    """Chamada invalida, ferramenta desconhecida ou dado inexistente."""


class Toolbox:
    """Conexao somente leitura (papel api_ro) + embedder. O agente so enxerga o banco por aqui."""

    def __init__(self, conn: psycopg.Connection, embedder: Embedder | None = None):
        self.conn = conn
        self.embedder = embedder
        self.registry: dict[str, tuple[type[BaseModel], Callable]] = {
            "consultar_cliente": (CustomerQuery, self.consultar_cliente),
            "calcular_elegibilidade": (CustomerQuery, self.calcular_elegibilidade),
            "buscar_regra": (RuleQuery, self.buscar_regra),
        }

    @property
    def names(self) -> list[str]:
        return list(self.registry)

    def call(self, name: str, arguments: dict) -> BaseModel:
        if name not in self.registry:
            raise ToolError("ferramenta desconhecida")
        schema, fn = self.registry[name]
        try:
            args = schema.model_validate(arguments)
        except ValidationError:
            raise ToolError("argumentos invalidos") from None
        return fn(args)

    def consultar_cliente(self, q: CustomerQuery) -> CustomerView:
        with self.conn.cursor(row_factory=dict_row) as cur:
            row = cur.execute(f"SELECT {CUSTOMER_COLUMNS} FROM analytics.customer_features WHERE customer_id = %s", (q.customer_id,)).fetchone()
        if row is None:
            raise ToolError("cliente nao encontrado")
        return CustomerView(**row)

    def calcular_elegibilidade(self, q: CustomerQuery) -> EligibilityResult:
        with self.conn.cursor(row_factory=dict_row) as cur:
            row = cur.execute(f"SELECT {ELIGIBILITY_COLUMNS} FROM analytics.customer_features WHERE customer_id = %s", (q.customer_id,)).fetchone()
        if row is None:
            raise ToolError("cliente nao encontrado")
        df = pd.DataFrame([row])
        p, at_stake = df["risk_score"].iloc[0] / 100, df["margin_12m_brl"].iloc[0]
        options = [EligibilityOption(action=name, cost_brl=cost, assumed_uplift=uplift, expected_net_margin_brl=round(float(p * uplift * at_stake - cost), 2))
                   for name, cost, uplift, eligible in ACTIONS if bool(eligible(df).iloc[0])]
        best = compute_nba(df).iloc[0]
        return EligibilityResult(customer_id=q.customer_id, eligible=options, best_action=str(best["nba_action"]),
                                 best_expected_margin_brl=float(best["nba_expected_margin_brl"]), requires_approval=bool(best["nba_requires_approval"]))

    def buscar_regra(self, q: RuleQuery) -> RuleSearchResult:
        rows = search_rules(self.conn, q.query, k=q.k, embedder=self.embedder)
        return RuleSearchResult(hits=[RuleHit(chunk_id=r["chunk_id"], content=r["content"], section=r["metadata"].get("section", ""), url=r["url"], title=r["title"],
                                              version=r["version"], consulted_at=r["consulted_at"].isoformat(), score=round(r["score"], 4))
                                      for r in rows if r["score"] >= MIN_RULE_SCORE and _shares_content_word(q.query, r["content"])])
