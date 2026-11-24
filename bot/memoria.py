"""Memória do Bit.

- Curta: as últimas trocas da conversa (para entender um "não funcionou").
- Média: um resumo da sessão (qual é o problema que está sendo resolvido).
- Longa: não existe de propósito. Quando a conversa acaba, tudo é apagado.
"""
from collections import deque


class Memoria:
    TAMANHO_CURTA = 6

    def __init__(self):
        self.curta = deque(maxlen=self.TAMANHO_CURTA)
        self.limpar_media()

    def registrar(self, autor, texto):
        self.curta.append((autor, texto))

    def definir_problema(self, intencao):
        self.problema_atual = intencao

    def limpar_media(self):
        self.problema_atual = None

    def limpar(self):
        self.curta.clear()
        self.limpar_media()
