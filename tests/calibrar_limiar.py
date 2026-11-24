"""Testa o Bit com frases que NÃO estão na base para escolher o limiar de confiança.

Uso: python -m tests.calibrar_limiar
"""
from bot.agente import Agente

# frases do jeito que um usuário escreveria (nenhuma está igual na base)
DENTRO_DO_ESCOPO = [
    ("nao lembro minha senha", "senha"), ("bloqueou meu usuario", "senha"),
    ("travei a conta depois de errar a senha", "senha"), ("a vpn nao quer conectar de jeito nenhum", "vpn"),
    ("em casa nao acesso nada da empresa", "vpn"), ("impressora do 2 andar parou", "impressora"),
    ("mandei imprimir e nao saiu nada", "impressora"), ("outlook travou", "email"),
    ("meus emails nao chegam", "email"), ("pc lento pra caramba", "lentidao"),
    ("o note ta muito devagar hoje", "lentidao"), ("caiu a internet aqui", "wifi"),
    ("wifi some toda hora", "wifi"), ("mouse morreu", "periferico"),
    ("tela do monitor ta preta", "periferico"), ("preciso do photoshop instalado", "solicitacao"),
    ("queria um monitor a mais", "solicitacao"), ("me deram acesso negado na pasta do rh", "acesso_sistema"),
    ("cliquei num link estranho no email", "seguranca"), ("acho que tem virus no meu pc", "seguranca"),
    ("me passa a senha do joao", "pedido_indevido"), ("quero falar com um tecnico", "falar_humano"),
    ("nao deu certo", "nao_resolveu"), ("valeu", "agradecimento"),
]
FORA_DO_ESCOPO = [
    "qual a receita de bolo de cenoura", "quem ganhou o jogo ontem", "me indica um filme",
    "que horas sao", "quanto e 2 mais 2", "vai chover amanha", "qual o cardapio do refeitorio",
    "quando cai o salario", "asdkjh qwe", "me conta uma piada", "qual a capital da franca",
    "quero marcar ferias",
]


def avaliar(agente, limiar):
    acertos = rejeitados_errado = 0
    for frase, esperada in DENTRO_DO_ESCOPO:
        intencao, conf = agente.entender(agente.perceber(frase))
        if conf < limiar:
            rejeitados_errado += 1
        elif intencao == esperada:
            acertos += 1
    fora_rejeitadas = sum(
        1 for frase in FORA_DO_ESCOPO if agente.entender(agente.perceber(frase))[1] < limiar
    )
    return acertos, rejeitados_errado, fora_rejeitadas


if __name__ == "__main__":
    bit = Agente()
    print("limiar | acertos (dentro) | rejeitadas sem motivo | fora do escopo rejeitadas")
    for limiar in (0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        a, r, f = avaliar(bit, limiar)
        print(f"{limiar:.2f}   | {a}/{len(DENTRO_DO_ESCOPO)}            | {r}                     | {f}/{len(FORA_DO_ESCOPO)}")
    print("\nDetalhe por frase:")
    for frase, esperada in DENTRO_DO_ESCOPO:
        i, c = bit.entender(bit.perceber(frase))
        print(f"  {c:.2f} {'OK ' if i == esperada else 'ERRO'} {i:16s} <- {frase}")
    for frase in FORA_DO_ESCOPO:
        i, c = bit.entender(bit.perceber(frase))
        print(f"  {c:.2f} fora {i:16s} <- {frase}")
