"""Paridade entre contrato (YAML), pandera, DDL das migracoes e schemas Pydantic."""
import re
import typing

import pytest

from src.contracts import build_schema, load_contract
from src.db import ENTITIES, LAYER_TABLES, MIGRATIONS_DIR, PG_TYPES
from src.schemas import MODELS

PY_TYPES = {"string": str, "integer": int, "decimal": float, "boolean": bool}


def parse_ddl() -> dict[str, dict[str, tuple[str, bool]]]:
    """{schema.tabela: {coluna: (tipo base, not_null)}} lido dos CREATE TABLE das migracoes."""
    tables = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+\.\w+) \((.*?)\n\);", text, re.S):
            cols = {}
            for line in m.group(2).splitlines():
                col = re.match(r"\s+(\w+)\s+(\w+)(?:\(\d+,\d+\))?(.*)", line)
                if col:
                    name, typ, rest = col.groups()
                    cols[name] = (typ, "NOT NULL" in rest or "PRIMARY KEY" in rest)
            tables[m.group(1)] = cols
    return tables


@pytest.mark.parametrize("entity", ENTITIES)
def test_contract_pandera_columns_match(entity):
    contract = load_contract()
    schema = build_schema(entity, contract)
    assert list(schema.columns) == list(contract["entities"][entity]["columns"])


@pytest.mark.parametrize("table,entity", [(f"{s}.{t}", e) for (s, t), e in LAYER_TABLES.items()])
def test_contract_matches_sql_ddl(table, entity):
    spec = load_contract()["entities"][entity]["columns"]
    ddl = parse_ddl()[table]
    assert set(ddl) == set(spec), f"colunas divergentes: {set(ddl) ^ set(spec)}"
    assert list(ddl) == list(spec), "ordem das colunas diverge do contrato"
    for col, s in spec.items():
        typ, not_null = ddl[col]
        assert typ == PG_TYPES[s["type"]], f"{table}.{col}: {typ} != {PG_TYPES[s['type']]}"
        assert not_null == (not s["nullable"]), f"{table}.{col}: nulabilidade divergente"


@pytest.mark.parametrize("entity", ENTITIES)
def test_contract_matches_pydantic(entity):
    spec = load_contract()["entities"][entity]["columns"]
    fields = MODELS[entity].model_fields
    assert set(fields) == set(spec)
    for col, s in spec.items():
        assert fields[col].annotation is PY_TYPES[s["type"]], f"{entity}.{col}"


def test_entities_have_primary_key_in_ddl():
    ddl_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS_DIR.glob("*.sql")))
    for (schema, table), entity in LAYER_TABLES.items():
        pk = load_contract()["entities"][entity]["primary_key"]
        block = re.search(rf"CREATE TABLE (?:IF NOT EXISTS )?{schema}\.{table} \((.*?)\n\);", ddl_text, re.S).group(1)
        assert re.search(rf"\b{pk}\s+\w+\s+PRIMARY KEY", block), f"{schema}.{table}"


def test_every_ops_and_layer_schema_is_created_by_migrations():
    ddl_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS_DIR.glob("*.sql")))
    for schema in ("raw", "treated", "analytics", "ops"):
        assert f"CREATE SCHEMA IF NOT EXISTS {schema};" in ddl_text


def test_new_migrations_are_idempotent_sql():
    for name in ("003_layers_and_roles.sql", "004_raw_treated_tables.sql", "005_ops_tables.sql"):
        text = (MIGRATIONS_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"CREATE TABLE (?!IF NOT EXISTS)", text), name
        assert not re.search(r"CREATE SCHEMA (?!IF NOT EXISTS)", text), name


def test_container_init_script_uses_lf():
    # CRLF no .sh faz o container falhar com "bad interpreter" e o login da API nao e criado
    script = MIGRATIONS_DIR.parents[1] / "db" / "init" / "01-api-role.sh"
    assert b"\r" not in script.read_bytes()


def test_init_script_creates_a_login_for_every_db_role():
    script = (MIGRATIONS_DIR.parents[1] / "db" / "init" / "01-api-role.sh").read_text(encoding="utf-8")
    for role in ("fidelidade_ro", "fidelidade_etl", "fidelidade_api_audit"):
        assert f"CREATE ROLE {role} LOGIN" in script


def test_no_pii_columns_in_any_layer():
    banned = {"name", "email", "cpf", "phone", "birth_date"}
    for entity, ent in load_contract()["entities"].items():
        assert not banned & set(ent["columns"]), entity
