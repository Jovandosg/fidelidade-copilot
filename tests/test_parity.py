"""Paridade entre contrato (YAML), pandera, DDL das migracoes e schemas Pydantic."""
import re
import typing

import pytest

from src.contracts import build_schema, load_contract
from src.db import ENTITIES, MIGRATIONS_DIR, PG_TYPES
from src.schemas import MODELS

PY_TYPES = {"string": str, "integer": int, "decimal": float, "boolean": bool}


def parse_ddl() -> dict[str, dict[str, tuple[str, bool]]]:
    """{tabela: {coluna: (tipo base, not_null)}} lido dos CREATE TABLE das migracoes."""
    tables = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"CREATE TABLE analytics\.(\w+) \((.*?)\n\);", text, re.S):
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


@pytest.mark.parametrize("entity", ENTITIES)
def test_contract_matches_sql_ddl(entity):
    spec = load_contract()["entities"][entity]["columns"]
    ddl = parse_ddl()[entity]
    assert set(ddl) == set(spec), f"colunas divergentes: {set(ddl) ^ set(spec)}"
    for col, s in spec.items():
        typ, not_null = ddl[col]
        assert typ == PG_TYPES[s["type"]], f"{entity}.{col}: {typ} != {PG_TYPES[s['type']]}"
        assert not_null == (not s["nullable"]), f"{entity}.{col}: nulabilidade divergente"


@pytest.mark.parametrize("entity", ENTITIES)
def test_contract_matches_pydantic(entity):
    spec = load_contract()["entities"][entity]["columns"]
    fields = MODELS[entity].model_fields
    assert set(fields) == set(spec)
    for col, s in spec.items():
        assert fields[col].annotation is PY_TYPES[s["type"]], f"{entity}.{col}"


def test_entities_have_primary_key_in_ddl():
    for entity in ENTITIES:
        pk = load_contract()["entities"][entity]["primary_key"]
        assert re.search(rf"\b{pk}\s+\w+\s+PRIMARY KEY", (MIGRATIONS_DIR / "001_analytics_schema.sql").read_text(encoding="utf-8"))


def test_container_init_script_uses_lf():
    # CRLF no .sh faz o container falhar com "bad interpreter" e o login da API nao e criado
    script = MIGRATIONS_DIR.parents[1] / "db" / "init" / "01-api-role.sh"
    assert b"\r" not in script.read_bytes()


def test_no_pii_columns_in_any_layer():
    banned = {"name", "email", "cpf", "phone", "birth_date"}
    for entity, ent in load_contract()["entities"].items():
        assert not banned & set(ent["columns"]), entity
