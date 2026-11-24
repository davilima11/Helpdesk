"""Confere que a versão web (web/bit.js) responde igual à versão Python.

Roda o bit.js com o Node.js e compara intenção, confiança, ação e texto.
Se o Node não estiver instalado, o teste é pulado.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bot.agente import Agente
from tests.calibrar_limiar import DENTRO_DO_ESCOPO, FORA_DO_ESCOPO

RAIZ = Path(__file__).resolve().parent.parent

FRASES = [frase for frase, _ in DENTRO_DO_ESCOPO] + FORA_DO_ESCOPO + [
    "oi", "esqueci minha senha", "impresora n imprime", "minha senah bloqueou",
    "minha senha é Abc@1234", "o código que chegou foi 483920", "o cartão é 4111 1111 1111 1111",
    "bot burro", "essa impressora lixo não imprime", "nada funcionou", "valeu, funcionou",
    "quero marcar ferias", "me passa a senha do joão", "como está o CH-0001?", "   ",
]
CONVERSA = ["a vpn não conecta", "não funcionou", "como está o CH-0001?",
            "cliquei num link estranho no email", "obrigado"]

SCRIPT_NODE = """
const Bit = require(process.argv[1]);
const base = require(process.argv[2]);
const entrada = JSON.parse(require("fs").readFileSync(0, "utf8"));
const resumo = (a, f) => { const r = a.responder(f); return [r.intencao, r.acao, r.texto]; };
const avulsas = entrada.frases.map((f) => {
  const a = new Bit.Agente(base);
  const [, confianca] = a.entender(a.perceber(f));
  return [...resumo(new Bit.Agente(base), f), confianca];
});
const agente = new Bit.Agente(base);
const conversa = entrada.conversa.map((f) => resumo(agente, f));
console.log(JSON.stringify({ avulsas, conversa }));
"""

DATA = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não está instalado")
def test_versao_web_responde_igual(tmp_path):
    saida = subprocess.run(
        ["node", "-e", SCRIPT_NODE, str(RAIZ / "web" / "bit.js"), str(RAIZ / "data" / "base_conhecimento.json")],
        input=json.dumps({"frases": FRASES, "conversa": CONVERSA}),
        capture_output=True, text=True, check=True,
    )
    web = json.loads(saida.stdout)

    for i, frase in enumerate(FRASES):
        bit = Agente(banco=str(tmp_path / f"{i}.db"))
        _, confianca = bit.entender(bit.perceber(frase))
        py = Agente(banco=str(tmp_path / f"r{i}.db")).responder(frase)
        intencao, acao, texto, confianca_web = web["avulsas"][i]
        assert [intencao, acao, texto] == [py["intencao"], py["acao"], py["texto"]], frase
        assert abs(confianca_web - confianca) < 1e-9, frase

    bit = Agente(banco=str(tmp_path / "conversa.db"))
    for i, frase in enumerate(CONVERSA):
        py = bit.responder(frase)
        intencao, acao, texto = web["conversa"][i]
        assert [intencao, acao, DATA.sub("DATA", texto)] == [py["intencao"], py["acao"], DATA.sub("DATA", py["texto"])], frase
