"""Gera o hash Argon2 de uma senha, para colar em AUTH_PASSWORD_HASH no .env.

    python scripts/hash_password.py

A senha nunca é gravada em nenhum lugar por este script; só o hash é impresso.
"""

from __future__ import annotations

import getpass

from argon2 import PasswordHasher


def main() -> int:
    password = getpass.getpass("Senha: ")
    confirm = getpass.getpass("Confirme: ")
    if password != confirm:
        print("[ERRO] As senhas não coincidem.")
        return 1

    print("\nAUTH_PASSWORD_HASH=" + PasswordHasher().hash(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
