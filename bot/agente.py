"""O agente Bit, organizado nas 4 camadas vistas na Unidade 4:

1. perceber  -> camada perceptiva: recebe o texto e prepara
2. entender  -> camada cognitiva: descobre qual é o assunto
3. decidir   -> camada decisória: aplica as regras (confiança, escopo, segurança)
4. executar  -> camada executiva: responde, abre chamado ou encaminha
"""
import json
import re
import unicodedata
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from bot import chamados
from bot.memoria import Memoria
from bot.privacidade import encontrar_dado_sensivel

BASE_PADRAO = Path(__file__).resolve().parent.parent / "data" / "base_conhecimento.json"

# Limiares de confiança. Os valores foram escolhidos testando (ver docs/4-testes.md).
# Acima do ALTO o Bit responde direto. Entre os dois ele responde, mas avisa
# que pode ter entendido errado. Abaixo do BAIXO ele admite que não sabe.
LIMIAR_ALTO = 0.55
LIMIAR_BAIXO = 0.35

PADRAO_PROTOCOLO = re.compile(r"\bCH-\d{1,6}\b", re.IGNORECASE)

# TF-IDF não entende negação: "nada funcionou" fica parecido com "funcionou".
# Essas palavras impedem que uma reclamação seja lida como agradecimento.
NEGACOES = {"nao", "nada", "nem", "sem", "nunca", "continua", "ainda"}


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


class Agente:
    def __init__(self, caminho_base=BASE_PADRAO, banco=None):
        with open(caminho_base, encoding="utf-8") as arquivo:
            base = json.load(arquivo)
        self.intencoes = base["intencoes"]
        self.msgs = base["mensagens"]
        self.sinonimos = base["sinonimos"]
        self.ofensas = base["palavras_ofensivas"]
        self.banco = banco
        self.memoria = Memoria()
        self._treinar()

    def _treinar(self):
        frases, self.rotulos = [], []
        for nome, dados in self.intencoes.items():
            for exemplo in dados["exemplos"]:
                frases.append(self.normalizar(exemplo))
                self.rotulos.append(nome)
        # n-gramas de caracteres aguentam melhor erro de digitação do que palavras inteiras
        self.vetorizador = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        self.matriz = self.vetorizador.fit_transform(frases)

    def normalizar(self, texto):
        """Minúsculas, sem acento, sem pontuação e com gírias/abreviações trocadas."""
        texto = sem_acento(texto.lower())
        texto = re.sub(r"[^\w\s-]", " ", texto)
        return " ".join(self.sinonimos.get(p, p) for p in texto.split())

    # ---------- camada 1: perceptiva ----------
    def perceber(self, texto):
        texto = (texto or "").strip()
        protocolo = PADRAO_PROTOCOLO.search(texto)
        return {
            "original": texto,
            "normalizado": self.normalizar(texto),
            "dado_sensivel": encontrar_dado_sensivel(texto),
            "protocolo": protocolo.group(0).upper() if protocolo else None,
        }

    # ---------- camada 2: cognitiva ----------
    def entender(self, percepcao):
        if not percepcao["normalizado"] or percepcao["dado_sensivel"]:
            return None, 0.0
        vetor = self.vetorizador.transform([percepcao["normalizado"]])
        similaridades = cosine_similarity(vetor, self.matriz)[0]
        melhor = similaridades.argmax()
        intencao = self.rotulos[melhor]
        if intencao == "agradecimento" and NEGACOES & set(percepcao["normalizado"].split()):
            intencao = "nao_resolveu"
        return intencao, float(similaridades[melhor])

    # ---------- camada 3: decisória ----------
    def decidir(self, percepcao, intencao, confianca):
        if percepcao["dado_sensivel"]:
            return "bloquear_dado"
        if percepcao["protocolo"]:
            return "consultar_chamado"
        if confianca < LIMIAR_BAIXO:
            return "acalmar" if self._tem_ofensa(percepcao["normalizado"]) else "nao_entendi"
        # em segurança o erro mais caro é NÃO agir, então escala mesmo com confiança média
        if intencao == "seguranca":
            return "escalar"
        # abrir chamado é uma ação no mundo, então só com confiança alta
        if intencao in ("nao_resolveu", "abrir_chamado") and confianca < LIMIAR_ALTO:
            return "nao_entendi"
        if intencao == "nao_resolveu":
            return "abrir_chamado" if self.memoria.problema_atual else "perguntar_problema"
        if intencao == "abrir_chamado":
            return "abrir_chamado"
        if confianca < LIMIAR_ALTO:
            return "responder_com_duvida"
        return "responder"

    def _tem_ofensa(self, texto):
        return any(re.search(rf"\b{re.escape(p)}\b", texto) for p in self.ofensas)

    # ---------- camada 4: executiva ----------
    def executar(self, acao, intencao):
        dados = self.intencoes.get(intencao, {})
        protocolo = None

        if acao == "bloquear_dado":
            texto = ""  # preenchido em responder(), que conhece o tipo do dado
        elif acao == "nao_entendi":
            texto = self.msgs["nao_entendi"]
        elif acao == "acalmar":
            texto = self.msgs["acalmar"]
        elif acao == "perguntar_problema":
            texto = self.msgs["perguntar_problema"]
        elif acao == "escalar":
            protocolo = chamados.abrir_chamado(dados["tema"], "Possível incidente relatado no chat.",
                                               prioridade="alta", banco=self.banco)
            texto = dados["resposta"].format(protocolo=protocolo)
            self.memoria.limpar_media()
        elif acao == "abrir_chamado":
            problema = self.memoria.problema_atual
            tema = self.intencoes[problema]["tema"] if problema else "não informado"
            if problema:
                resumo = f"Usuário seguiu o passo a passo do Bit para {tema} e não resolveu."
            else:
                resumo = "Usuário pediu para abrir chamado sem dizer o problema."
            protocolo = chamados.abrir_chamado(tema, resumo, banco=self.banco)
            texto = self.msgs["chamado_aberto"].format(protocolo=protocolo, tema=tema)
            self.memoria.limpar_media()
        else:  # responder / responder_com_duvida
            texto = dados["resposta"]
            if acao == "responder_com_duvida":
                texto = self.msgs["com_duvida"].format(tema=dados["tema"]) + texto
            if dados.get("tecnica"):
                self.memoria.definir_problema(intencao)
            if intencao == "agradecimento":
                self.memoria.limpar_media()
        return texto, protocolo

    def _consultar(self, protocolo):
        chamado = chamados.consultar_chamado(protocolo, banco=self.banco)
        if not chamado:
            return self.msgs["chamado_nao_encontrado"].format(protocolo=protocolo)
        return self.msgs["chamado_encontrado"].format(**chamado)

    def explicar(self, acao, intencao, confianca):
        """Explica em linguagem simples por que o Bit tomou a decisão (interpretabilidade)."""
        tema = self.intencoes.get(intencao, {}).get("tema", "nenhum")
        def virgula(numero):
            return f"{numero:.2f}".replace(".", ",")
        conf, alto, baixo = virgula(confianca), virgula(LIMIAR_ALTO), virgula(LIMIAR_BAIXO)
        explicacoes = {
            "bloquear_dado": "A mensagem parecia ter um dado sensível, então foi descartada antes de qualquer análise.",
            "consultar_chamado": "Encontrei um número de protocolo na mensagem e consultei o chamado.",
            "nao_entendi": f"O assunto mais parecido foi '{tema}', mas a confiança ({conf}) ficou abaixo do mínimo ({baixo}). Preferi admitir que não sei a chutar.",
            "acalmar": "Não identifiquei um problema técnico e a mensagem tinha uma palavra ofensiva.",
            "escalar": f"Identifiquei '{tema}' (confiança {conf}). Segurança é escalada na hora, mesmo com dúvida.",
            "perguntar_problema": "Você disse que não resolveu, mas eu ainda não sabia qual era o problema.",
            "abrir_chamado": "Abri um chamado para uma pessoa do suporte assumir.",
            "responder_com_duvida": f"Identifiquei '{tema}', mas com confiança média ({conf}). Respondi avisando que posso ter entendido errado.",
            "responder": f"Identifiquei '{tema}' com confiança {conf} (acima de {alto}).",
        }
        return explicacoes[acao]

    # ---------- fluxo completo ----------
    def responder(self, texto):
        percepcao = self.perceber(texto)
        intencao, confianca = self.entender(percepcao)
        acao = self.decidir(percepcao, intencao, confianca)

        if acao == "bloquear_dado":
            resposta, protocolo = self.msgs["dado_sensivel"].format(tipo=percepcao["dado_sensivel"]), None
        elif acao == "consultar_chamado":
            resposta, protocolo = self._consultar(percepcao["protocolo"]), percepcao["protocolo"]
        else:
            resposta, protocolo = self.executar(acao, intencao)

        # a mensagem com dado sensível nunca entra na memória
        if acao != "bloquear_dado":
            self.memoria.registrar("usuario", percepcao["original"])
        self.memoria.registrar("bit", resposta)

        return {
            "texto": resposta,
            "intencao": intencao,
            "confianca": round(confianca, 2),
            "acao": acao,
            "protocolo": protocolo,
            "explicacao": self.explicar(acao, intencao, confianca),
        }
