"""Interface do Bit em Streamlit. Para rodar: streamlit run app.py"""
import streamlit as st

from bot import chamados
from bot.agente import Agente

st.set_page_config(page_title="Bit - Suporte de TI")


def iniciar_conversa():
    st.session_state.agente = Agente()
    st.session_state.historico = [
        {"autor": "assistant", "texto": st.session_state.agente.msgs["inicial"], "info": None}
    ]


def enviar(texto_usuario):
    agente = st.session_state.agente
    resultado = agente.responder(texto_usuario)
    # se tinha dado sensível, nem na tela a mensagem original continua
    if resultado["acao"] == "bloquear_dado":
        texto_usuario = "[mensagem apagada: tinha um dado sensível]"
    st.session_state.historico.append({"autor": "user", "texto": texto_usuario, "info": None})
    st.session_state.historico.append({"autor": "assistant", "texto": resultado["texto"], "info": resultado})


if "agente" not in st.session_state:
    iniciar_conversa()

with st.sidebar:
    st.header("Sobre o Bit")
    st.write("Assistente de suporte de TI de primeiro nível da Distribuidora Planalto (empresa fictícia).")
    st.write("**Eu ajudo com:** senha, VPN, impressora, e-mail, Wi-Fi, computador lento, "
             "teclado/mouse/monitor, acesso a sistemas e pedidos de programa ou equipamento.")
    st.warning("O suporte **nunca** pede sua senha, código de verificação ou dados de cartão.")
    st.caption("A conversa não fica salva. Quando você fecha a página ou limpa a conversa, tudo é apagado. "
               "Chamados guardam só o assunto, nunca o que você digitou.")
    if st.button("Limpar conversa"):
        iniciar_conversa()
        st.rerun()
    st.caption("Atendimento humano: ramal 4000, seg a sex, 8h às 18h.")

st.title("Bit - Suporte de TI")

for mensagem in st.session_state.historico:
    with st.chat_message(mensagem["autor"]):
        st.write(mensagem["texto"])
        if mensagem["info"]:
            with st.expander("Por que o Bit respondeu isso?"):
                st.write(mensagem["info"]["explicacao"])

# botões de feedback só na última resposta com passo a passo (remediação)
ultima = st.session_state.historico[-1]
if ultima["info"] and ultima["info"]["acao"] in ("responder", "responder_com_duvida") \
        and st.session_state.agente.intencoes[ultima["info"]["intencao"]].get("tecnica"):
    col1, col2 = st.columns(2)
    if col1.button("Resolveu", use_container_width=True):
        chamados.registrar_feedback(ultima["info"]["intencao"], True)
        enviar("deu certo, obrigado")
        st.rerun()
    if col2.button("Não resolveu", use_container_width=True):
        chamados.registrar_feedback(ultima["info"]["intencao"], False)
        enviar("não resolveu")
        st.rerun()

pergunta = st.chat_input("Descreva o problema com suas palavras...")
if pergunta:
    enviar(pergunta)
    st.rerun()
