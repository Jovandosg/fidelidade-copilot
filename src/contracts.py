"""Carrega docs/02-dados/data_contracts.yml e gera schemas pandera a partir dele.

O YAML e a unica fonte das regras de formato dos dados; nada e duplicado a mao.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
import yaml

CONTRACT_PATH = Path(__file__).parents[1] / "docs" / "02-dados" / "data_contracts.yml"
ALLOWED_TYPES = {"string": str, "integer": int, "decimal": float, "boolean": bool, "date": None}
IATA_RE = r"^[A-Z]{3}$"
NUM = r"-?\d+(?:\.\d+)?"
DATE = r"\d{4}-\d{2}-\d{2}"
_COL_KEYS = {"type", "nullable", "constraints"}


class ContractError(ValueError):
    pass


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    """Le e valida a estrutura do contrato (chaves, tipos e referencias)."""
    contract = _load(str(path))
    for key in ("version", "entities"):
        if key not in contract:
            raise ContractError(f"contrato sem '{key}'")
    for name, ent in contract["entities"].items():
        cols = ent.get("columns")
        if not cols or ent.get("primary_key") not in cols:
            raise ContractError(f"{name}: primary_key ausente nas colunas")
        for fk in ent.get("foreign_keys", []):
            if fk not in cols:
                raise ContractError(f"{name}: foreign key '{fk}' inexistente")
        for col, spec in cols.items():
            if spec.get("type") not in ALLOWED_TYPES:
                raise ContractError(f"{name}.{col}: tipo invalido {spec.get('type')!r}")
            if set(spec) - _COL_KEYS:
                raise ContractError(f"{name}.{col}: chaves desconhecidas {set(spec) - _COL_KEYS}")
            if "nullable" not in spec:
                raise ContractError(f"{name}.{col}: 'nullable' obrigatorio")
    return contract


def _bound(value: str, is_date: bool):
    return pd.Timestamp(value) if is_date else float(value)


def _series(s: pd.Series, is_date: bool) -> pd.Series:
    return pd.to_datetime(s) if is_date else s


def _compare(op: str, bound, is_date: bool, col: str) -> pa.Check:
    fn = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}[op]
    return pa.Check(lambda s: fn(_series(s, is_date), bound), name=f"{col}_{op}")


def _constraint_checks(col: str, ctype: str, text: str | None, entity_cols: dict) -> tuple[list[pa.Check], list[pa.Check]]:
    """Traduz constraints do YAML em (checks de coluna, checks de tabela); erra em texto desconhecido."""
    checks: list[pa.Check] = []
    frame_checks: list[pa.Check] = []
    if not text:
        return checks, frame_checks
    is_date = ctype == "date"
    for part in (p.strip() for p in text.split(";")):
        if m := re.fullmatch(r"regex (.+)", part):
            checks.append(pa.Check.str_matches(m.group(1)))
        elif m := re.fullmatch(r"one of \[(.+)\]", part):
            checks.append(pa.Check.isin([v.strip() for v in m.group(1).split(",")]))
        elif part == "IATA-like 3 uppercase letters":
            checks.append(pa.Check.str_matches(IATA_RE))
        elif part == "unique" or re.fullmatch(r"must exist in \w+", part):
            continue  # unicidade e integridade referencial tem tratamento proprio
        elif m := re.fullmatch(r"different from (\w+)", part):
            other = m.group(1)
            if other not in entity_cols:
                raise ContractError(f"{col}: coluna '{other}' inexistente")
            frame_checks.append(pa.Check(lambda df, c=col, o=other: df[c] != df[o], name=f"{col}_ne_{other}"))
        elif m := re.fullmatch(rf"({NUM}|{DATE})\.\.({NUM}|{DATE})", part):
            lo, hi = _bound(m.group(1), is_date), _bound(m.group(2), is_date)
            checks.append(pa.Check(lambda s, lo=lo, hi=hi, d=is_date: (_series(s, d) >= lo) & (_series(s, d) <= hi), name=f"{col}_range"))
        elif m := re.fullmatch(rf"(>=|<=|>|<) ?({NUM}|{DATE})(?: and (>=|<=|>|<) ?({NUM}|{DATE}))?", part):
            for op, val in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
                if op:
                    checks.append(_compare(op, _bound(val, is_date), is_date, col))
        else:
            raise ContractError(f"{col}: constraint nao suportada: {part!r}")
    return checks, frame_checks


def build_schema(entity: str, contract: dict | None = None) -> pa.DataFrameSchema:
    contract = contract or load_contract()
    ent = contract["entities"][entity]
    cols = ent["columns"]
    columns = {}
    frame_checks: list[pa.Check] = []
    for name, spec in cols.items():
        col_checks, df_checks = _constraint_checks(name, spec["type"], spec.get("constraints"), cols)
        frame_checks += df_checks
        columns[name] = pa.Column(
            ALLOWED_TYPES[spec["type"]],
            checks=col_checks,
            nullable=spec["nullable"],
            unique=(name == ent["primary_key"] or "unique" in (spec.get("constraints") or "")),
        )
    return pa.DataFrameSchema(columns, checks=frame_checks, strict=True)


def _check_rule(frame: pd.DataFrame, schema: pa.DataFrameSchema) -> int:
    """Valida o frame contra um schema de uma unica regra; devolve o numero de casos de falha (0 = passou)."""
    try:
        schema.validate(frame, lazy=True)
        return 0
    except pa.errors.SchemaErrors as exc:
        index = exc.failure_cases["index"].dropna()
        return max(int(index.nunique()), 1)


def rule_results(entity: str, frame: pd.DataFrame, contract: dict | None = None) -> list[dict]:
    """Resultado do pandera por regra do contrato: [{entity, rule, passed, failed_rows}].

    Cada regra (colunas, tipo/nulabilidade, unicidade, cada constraint, regras entre colunas) e avaliada isoladamente
    pelos mesmos checks gerados por build_schema, entao um unico dado ruim aponta a regra exata.
    """
    contract = contract or load_contract()
    spec = build_schema(entity, contract)
    results = []

    def add(rule: str, failed: int) -> None:
        results.append({"entity": entity, "rule": rule, "passed": failed == 0, "failed_rows": failed})

    expected = list(spec.columns)
    add("columns_match_contract", 0 if list(frame.columns) == expected else max(len(set(frame.columns) ^ set(expected)), 1))
    present = [c for c in expected if c in frame.columns]
    for name in present:
        col = spec.columns[name]
        add(f"{name}:type_nullable", _check_rule(frame, pa.DataFrameSchema({name: pa.Column(col.dtype, nullable=col.nullable)})))
        if col.unique:
            add(f"{name}:unique", _check_rule(frame, pa.DataFrameSchema({name: pa.Column(None, nullable=True, unique=True)})))
        seen: dict[str, int] = {}
        for check in col.checks:
            seen[check.name] = seen.get(check.name, 0) + 1
            suffix = f"#{seen[check.name]}" if seen[check.name] > 1 else ""
            add(f"{name}:{check.name}{suffix}", _check_rule(frame, pa.DataFrameSchema({name: pa.Column(None, checks=[check], nullable=True)})))
    for check in spec.checks:
        add(f"table:{check.name}", _check_rule(frame, pa.DataFrameSchema(checks=[check], strict=False)))
    return results


def check_foreign_keys(frames: dict[str, pd.DataFrame], contract: dict | None = None) -> None:
    """Verifica 'must exist in <entidade>' entre as entidades fornecidas."""
    contract = contract or load_contract()
    for name, ent in contract["entities"].items():
        if name not in frames:
            continue
        for fk in ent.get("foreign_keys", []):
            m = re.search(r"must exist in (\w+)", ent["columns"][fk].get("constraints") or "")
            if not m or m.group(1) not in frames:
                continue
            target = m.group(1)
            target_pk = contract["entities"][target]["primary_key"]
            missing = set(frames[name][fk]) - set(frames[target][target_pk])
            if missing:
                raise ValueError(f"{name}.{fk} sem correspondencia em {target}: {sorted(missing)[:5]}")
