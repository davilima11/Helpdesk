"""Detecta dado sensível na mensagem antes de qualquer processamento.

Se o usuário digitar senha, código de verificação, CPF ou cartão, o Bit
descarta a mensagem e não guarda nada (privacidade by design).
"""
import re

# a ordem importa: cartão vem antes do CPF porque um número de cartão
# também tem 11 dígitos seguidos e seria confundido com CPF
PADROES = [
    ("uma senha", re.compile(r"\bsenha\s*(?:é|eh|:|=|era|seria)\s*\S+", re.IGNORECASE)),
    ("um código de verificação",
     re.compile(r"\b(?:c[oó]digo|token|2fa|verifica[cç][aã]o)\D{0,20}\d{4,8}\b", re.IGNORECASE)),
    ("um número de cartão", re.compile(r"\b(?:\d[ -]?){15,16}\b")),
    ("um CPF", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
]


def encontrar_dado_sensivel(texto):
    """Retorna o tipo de dado sensível encontrado ou None."""
    for tipo, padrao in PADROES:
        if padrao.search(texto or ""):
            return tipo
    return None
