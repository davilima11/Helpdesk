# Ética, viés e responsabilidade social

Esta parte é a análise de impacto ético do Bit. Tentei não escrever só o que "a IA pode fazer de errado" em geral, e sim olhar para as decisões que eu mesmo tomei no projeto e o que cada uma causa.

## 1. Privacidade by design

O guia cita Lee, Goldberg e Kohane (2024): a proteção tem que nascer no design, e não ser um remendo depois. A LGPD (Lei nº 13.709/2018) também pede que só se colete o necessário para a finalidade. No Bit, isso virou decisões concretas:

| Princípio | O que fiz no Bit |
|---|---|
| Coleta mínima | O Bit não pergunta nome, matrícula, e-mail nem nada pessoal. O chamado guarda só o tema e uma frase de resumo |
| Bloqueio de dado sensível | Se a pessoa digita senha, código de verificação, CPF ou cartão, a mensagem é descartada antes de ser analisada, não entra na memória e some até da tela |
| Sem memória longa | Nada da conversa fica salvo depois que ela termina |
| Controle de acesso | O Bit não tem acesso a nenhum sistema da empresa, então não tem como vazar o que não vê |
| Uso secundário | O feedback ("Resolveu" / "Não resolveu") guarda só a intenção e o sim/não. Não dá para usar isso para avaliar funcionário, e não deve ser usado para outra coisa sem avisar |

A regra de nunca pedir senha tem um efeito a mais: ela também ensina. Golpe de engenharia social quase sempre começa com alguém "do suporte" pedindo senha. Quando o próprio suporte avisa que nunca pede, fica mais fácil a pessoa desconfiar.

Uma coisa que não fiz: criptografia. O banco SQLite do projeto é local e simulado. Numa empresa de verdade, o banco de chamados teria que ser criptografado e a identificação do usuário viria do login da rede, sem o Bit precisar perguntar nada.

## 2. Viés

Barcaui (2025), citado no guia, diz que o viés não é um bug acidental, mas a reprodução de um ambiente que já era injusto. Encontrei os três tipos no Bit.

### Viés de dados

A base de conhecimento foi escrita por mim, um estudante de Computação. Mesmo tentando escrever informal, meu jeito de descrever problema é o de quem conhece os termos. Quem mais precisa do Bit é quem escreve "o negócio da internet de casa não entra no sistema", e essa pessoa é a que tem mais chance de não ser entendida.

Isso apareceu nos testes. Das 24 frases de teste escritas como um usuário escreveria (nenhuma igual às da base), as duas que o Bit não entendeu foram justamente as mais coloquiais: "meus emails nao chegam" (confiança 0,30) e "travei a conta depois de errar a senha" (0,35, exatamente na borda).

### Viés de algoritmo

O limiar de confiança é um número que eu escolhi, e ele decide quem é atendido. Rodei o Bit com as 24 frases dentro do escopo e 12 fora do escopo (receita de bolo, resultado de jogo, "me conta uma piada") variando o limiar:

| Limiar | Frases válidas entendidas | Válidas rejeitadas | Fora do escopo rejeitadas |
|---|---|---|---|
| 0,25 | 24/24 | 0 | 5/12 |
| 0,30 | 23/24 | 1 | 6/12 |
| **0,35** | **22/24** | **2** | **9/12** |
| 0,40 | 22/24 | 2 | 11/12 |
| 0,45 | 21/24 | 3 | 12/12 |
| 0,50 | 20/24 | 4 | 12/12 |

Não existe limiar que acerte tudo. Subir o limiar deixa o Bit mais "seguro" (quase nunca responde besteira), mas cada ponto a mais rejeita alguém que tinha uma pergunta válida, e quem é rejeitado é sempre quem escreve de um jeito diferente da base.

Olhando só essa tabela, 0,40 parece melhor que 0,35: rejeita mais pergunta fora do escopo sem perder nenhuma válida a mais. Mesmo assim fiquei com 0,35, por dois motivos. A amostra é pequena (36 frases), e das frases válidas, duas ficaram entre 0,35 e 0,45 ("travei a conta..." com 0,35 e "em casa nao acesso nada da empresa" com 0,43). Ou seja, o jeito informal de escrever fica perto da borda, e um limiar maior deixa menos folga para frases que eu não testei. O segundo motivo é a faixa de dúvida: entre 0,35 e 0,55 o Bit responde, mas avisa que pode ter entendido errado. Quando uma pergunta fora do escopo passa (como "me conta uma piada", que ficou parecida com "senha"), a resposta já vem com "Acho que você está falando de senha. Se não for isso, me explica de outro jeito". Prefiro esse erro, com aviso, a deixar mais gente sem resposta.

Para ações que mexem em algo, a regra é outra. Na calibração, "quero marcar férias" ficou parecida com "abrir chamado", e o Bit chegou a abrir um chamado sem sentido. Corrigi: abrir chamado só com confiança alta (acima de 0,55). A exceção é segurança, que escala mesmo com dúvida.

### Viés de aplicação

O Bit foi pensado para o funcionário de escritório da empresa fictícia. Se fosse usado sem adaptação em outro contexto, ia falhar: o passo a passo da VPN, por exemplo, supõe o computador da empresa, e quem está em home office com o computador pessoal pode ter outro programa. Os nomes de rede, o portal e o ramal também são da Planalto. Levar o Bit para outra empresa exige reescrever a base, não só trocar o logo.

## 3. O que fiz para diminuir o viés (e o que isso custou)

- **n-gramas de caractere em vez de palavras**: "impresora" e "impressora" ficam quase iguais. O custo é que frases curtas e aleatórias às vezes ficam parecidas com alguma intenção.
- **Lista de abreviações e erros comuns** ("n", "pc", "net", "senah"): ajuda quem escreve rápido, mas é uma lista feita à mão e nunca vai estar completa.
- **Faixa de dúvida no limiar**: atende mais gente, ao custo de às vezes responder fora do assunto (com aviso).
- **Regra de negação**: o TF-IDF entendia "nada funcionou" como agradecimento, porque tem a palavra "funcionou". Coloquei uma regra para palavras como "nada", "não" e "ainda". É uma correção pontual, não resolve negação em geral.
- **Testes com frases informais e com erro** (ver [4-testes.md](4-testes.md)).

Eysenck e Eysenck (2023), citados no guia, dizem que IA sem auditoria de viés é IA sem responsabilidade. A tabela do limiar é a minha auditoria, pequena, mas feita com números e não com achismo.

## 4. Decisões olhadas pelos três frameworks éticos

O guia apresenta três formas de pensar (Córdova, 2025). Usei as três em decisões reais do projeto:

| Decisão | Consequencialista (menor dano) | Deontológico (regra que não se quebra) | Virtudes (integridade e transparência) |
|---|---|---|---|
| Nunca pedir senha | Evita vazamento e golpe | É regra absoluta, mesmo se o usuário quiser mandar | O Bit avisa por que apagou a mensagem |
| Escalar segurança com dúvida | Chamado urgente à toa custa menos que vírus ignorado | | Diz claramente o que a pessoa deve fazer |
| Limiar em 0,35 com faixa de dúvida | Mais gente atendida, erro com aviso | | Admite quando não tem certeza |
| Sem memória longa | Menos dado guardado, menos risco | Coleta mínima da LGPD | |

As decisões não se encaixam perfeitamente em um framework só, e isso bate com o que o guia diz: ética não é um checklist, é ir resolvendo as tensões caso a caso.

## 5. Responsabilidade social

O guia fala em licença social para operar (Córdova, 2025), com três pilares.

**Accountability (quem responde quando o Bit erra?).** O Bit é uma ferramenta do setor de TI, então quem responde é o setor de TI, não o "algoritmo". Por isso toda resposta tem a explicação da decisão e todo chamado mostra o que o Bit já tentou: se ele errar, dá para ver onde.

**Participação.** Até agora, só eu testei o Bit. Antes de colocar para uso de verdade, ele precisaria ser testado por pessoas que não são da área de TI, que são justamente as que escrevem de um jeito que eu não previ. Essa é a maior limitação do projeto e está no plano de testes.

**Remediação.** A pessoa sempre tem como contestar: o botão "Não resolveu" abre um chamado já com o assunto, sem ela precisar repetir tudo, e o ramal humano aparece na tela o tempo todo. Ninguém fica preso no chatbot.

## 6. Limitações que conheço

- A base foi escrita por uma pessoa só e nunca foi testada com usuários reais.
- Perguntas totalmente fora do assunto às vezes passam do limiar e recebem resposta com aviso de dúvida.
- O Bit não entende negação de verdade; só a regra pontual para não confundir reclamação com agradecimento.
- A empresa, os sistemas e os procedimentos são fictícios.

## Referências

- BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD).
- VALÉRIA, Kadidja. *Guia de Estudos A1: Criação de Agentes de IA e Ética Aplicada*. UDF Centro Universitário, 2026. Os autores Lee, Goldberg e Kohane (2024), Barcaui (2025), Eysenck e Eysenck (2023) e Córdova (2025) foram citados a partir desse guia.
