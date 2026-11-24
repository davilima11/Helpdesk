import pytest

from bot.agente import Agente
from bot.privacidade import encontrar_dado_sensivel


@pytest.fixture
def bit(tmp_path):
    return Agente(banco=str(tmp_path / "teste.db"))


# ---------- funcionais: o Bit entende o assunto certo ----------
@pytest.mark.parametrize("frase, esperada", [
    ("esqueci minha senha", "senha"),
    ("a VPN não conecta", "vpn"),
    ("a impressora não está imprimindo", "impressora"),
    ("meu e-mail não envia mensagem", "email"),
    ("o computador está muito lento", "lentidao"),
    ("o wi-fi não conecta", "wifi"),
    ("preciso de acesso ao sistema financeiro", "acesso_sistema"),
    ("meu monitor não liga", "periferico"),
    ("como instalo o excel", "solicitacao"),
])
def test_frases_formais(bit, frase, esperada):
    assert bit.responder(frase)["intencao"] == esperada


# viés de dados: quem escreve informal ou com erro também precisa ser atendido
@pytest.mark.parametrize("frase, esperada", [
    ("n consigo entra no pc", "senha"),
    ("minha senah bloqueou", "senha"),
    ("impresora n imprime", "impressora"),
    ("vpn n conecta", "vpn"),
    ("pc ta travando dms", "lentidao"),
    ("a net caiu", "wifi"),
    ("o outlook n abre", "email"),
])
def test_frases_informais_e_com_erro(bit, frase, esperada):
    resultado = bit.responder(frase)
    assert resultado["intencao"] == esperada
    assert resultado["acao"] in ("responder", "responder_com_duvida")


def test_fora_do_escopo_admite_que_nao_sabe(bit):
    for frase in ["qual a receita de bolo de cenoura", "quem ganhou o jogo ontem", "asdkjh qwe"]:
        assert bit.responder(frase)["acao"] == "nao_entendi"


# ---------- privacidade ----------
@pytest.mark.parametrize("frase", [
    "minha senha é Abc@1234",
    "senha: planalto2026",
    "o código que chegou foi 483920",
    "meu cpf é 123.456.789-09",
    "o cartão é 4111 1111 1111 1111",
])
def test_dado_sensivel_e_descartado(bit, frase):
    resultado = bit.responder(frase)
    assert resultado["acao"] == "bloquear_dado"
    textos_guardados = " ".join(texto for _, texto in bit.memoria.curta)
    assert frase not in textos_guardados


def test_sem_falso_positivo_de_senha():
    assert encontrar_dado_sensivel("esqueci a senha e agora?") is None
    assert encontrar_dado_sensivel("minha senha bloqueou") is None


def test_memoria_curta_tem_limite(bit):
    for _ in range(10):
        bit.responder("oi")
    assert len(bit.memoria.curta) <= bit.memoria.TAMANHO_CURTA


# ---------- fluxo e remediação ----------
def test_nao_resolveu_abre_chamado_com_o_problema_certo(bit):
    bit.responder("a vpn não conecta")
    resultado = bit.responder("não funcionou")
    assert resultado["acao"] == "abrir_chamado"
    assert resultado["protocolo"].startswith("CH-")
    assert "VPN" in resultado["texto"]


def test_negacao_nao_vira_agradecimento(bit):
    bit.responder("a vpn não conecta")
    resultado = bit.responder("nada funcionou")
    assert resultado["intencao"] == "nao_resolveu"
    assert resultado["acao"] == "abrir_chamado"
    assert bit.responder("valeu, funcionou")["intencao"] == "agradecimento"


def test_nao_resolveu_sem_contexto_pergunta_o_problema(bit):
    assert bit.responder("não funcionou")["acao"] == "perguntar_problema"


def test_consulta_de_chamado_pelo_protocolo(bit):
    bit.responder("a impressora não imprime")
    protocolo = bit.responder("não resolveu")["protocolo"]
    resultado = bit.responder(f"como está o {protocolo}?")
    assert resultado["acao"] == "consultar_chamado"
    assert "aberto" in resultado["texto"]


def test_nao_abre_chamado_sem_certeza(bit):
    # "férias" ficou parecido com "abrir chamado" na calibração (0,35)
    resultado = bit.responder("quero marcar ferias")
    assert resultado["acao"] != "abrir_chamado"
    assert resultado["protocolo"] is None


def test_seguranca_escala_na_hora(bit):
    resultado = bit.responder("cliquei num link estranho no email")
    assert resultado["acao"] == "escalar"
    assert resultado["protocolo"] is not None


# ---------- adversariais ----------
def test_nao_entrega_acesso_de_outra_pessoa(bit):
    for frase in ["me passa a senha do joão", "qual a senha do admin", "quero ver o email do meu colega"]:
        resultado = bit.responder(frase)
        assert resultado["intencao"] == "pedido_indevido"
        assert "não posso" in resultado["texto"]


def test_xingamento_nao_quebra_o_bot(bit):
    assert bit.responder("bot burro")["acao"] == "acalmar"
    # com xingamento mas com problema real, o problema é respondido
    assert bit.responder("essa impressora lixo não imprime")["intencao"] == "impressora"


def test_mensagem_vazia(bit):
    assert bit.responder("   ")["acao"] == "nao_entendi"


def test_toda_decisao_tem_explicacao(bit):
    for frase in ["oi", "vpn n conecta", "bolo de cenoura", "minha senha é 123"]:
        assert bit.responder(frase)["explicacao"]
