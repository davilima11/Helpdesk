"""Registro de chamados e feedback em SQLite.

O chamado guarda só o tema e um resumo curto (o que já foi tentado),
nunca a conversa inteira. É a coleta mínima: o técnico precisa saber o
problema, não precisa ler tudo o que a pessoa digitou.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

BANCO_PADRAO = Path(__file__).resolve().parent.parent / "database" / "chamados.db"


def _conectar(banco=None):
    caminho = Path(banco or BANCO_PADRAO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.execute("""CREATE TABLE IF NOT EXISTS chamados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT, resumo TEXT, prioridade TEXT, status TEXT, criado_em TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intencao TEXT, resolveu INTEGER, criado_em TEXT)""")
    return con


def abrir_chamado(tema, resumo, prioridade="normal", banco=None):
    with _conectar(banco) as con:
        cur = con.execute(
            "INSERT INTO chamados (tema, resumo, prioridade, status, criado_em) VALUES (?, ?, ?, ?, ?)",
            (tema, resumo, prioridade, "aberto", datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
        return f"CH-{cur.lastrowid:04d}"


def consultar_chamado(protocolo, banco=None):
    try:
        numero = int(protocolo.upper().replace("CH-", ""))
    except ValueError:
        return None
    with _conectar(banco) as con:
        linha = con.execute(
            "SELECT tema, prioridade, status, criado_em FROM chamados WHERE id = ?", (numero,)
        ).fetchone()
    if not linha:
        return None
    return {"protocolo": protocolo.upper(), "tema": linha[0], "prioridade": linha[1],
            "status": linha[2], "data": linha[3]}


def registrar_feedback(intencao, resolveu, banco=None):
    with _conectar(banco) as con:
        con.execute("INSERT INTO feedback (intencao, resolveu, criado_em) VALUES (?, ?, ?)",
                    (intencao, int(resolveu), datetime.now().strftime("%d/%m/%Y %H:%M")))
