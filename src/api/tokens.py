"""Emite tokens JWT para a API (uso local/operacao). Exige JWT_SECRET no ambiente.

Uso:  python -m src.api.tokens --sub maria --role gestor [--hours 8]
"""
from __future__ import annotations

import argparse

from .security import ROLES, issue_token


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sub", required=True, help="apelido do usuario (a-z, 0-9, . _ -); nunca nome real")
    p.add_argument("--role", required=True, choices=ROLES)
    p.add_argument("--hours", type=float, default=8, help="validade em horas (max 24)")
    args = p.parse_args()
    try:
        print(issue_token(args.sub, args.role, int(args.hours * 3600)))
    except ValueError as exc:
        raise SystemExit(f"erro: {exc}") from None


if __name__ == "__main__":
    main()
