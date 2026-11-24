# Especificação do Bit

Esta especificação segue as primeiras etapas do fluxo de desenvolvimento de chatbots do SERPRO: entender a necessidade, definir persona, coletar o acervo, modelar e escrever as mensagens (UX writing).

## 1. Problema

Num setor de TI, boa parte dos chamados é sempre a mesma coisa: senha bloqueada, VPN que não conecta, impressora travada, internet caindo. Quase tudo isso se resolve seguindo três ou quatro passos, mas a pessoa liga para o ramal, espera na fila e o técnico passa o dia repetindo a mesma explicação. Enquanto isso, problemas mais sérios esperam junto.

A necessidade é ter um primeiro atendimento que resolva o que é repetitivo e mande para uma pessoa só o que precisa de uma pessoa.

## 2. Escopo

| O Bit faz | O Bit não faz |
|---|---|
| Passo a passo para senha, VPN, impressora, e-mail, Wi-Fi, lentidão e periféricos | Não pede, não vê e não troca senha |
| Explica como pedir acesso, programa ou equipamento | Não libera acesso nem instala nada sozinho |
| Abre chamado quando o passo a passo não resolve | Não acessa nenhum sistema da empresa |
| Consulta o status de um chamado pelo protocolo | Não trata incidente de segurança (só escala) |
| Encaminha para atendimento humano quando pedem | Não guarda a conversa depois que ela termina |

O escopo pequeno foi escolhido de propósito. Cada coisa que fica de fora é um risco a menos, principalmente na parte de privacidade.

## 3. Quem vai usar

| Usuário | Como ele chega no Bit |
|---|---|
| Funcionário do escritório | Problema do dia a dia, quer resolver rápido e voltar ao trabalho |
| Funcionário em home office | Depende da VPN e não tem ninguém do lado para ajudar |
| Pessoa com pouca familiaridade com TI | Escreve do jeito que fala, com abreviação e erro de digitação, e não conhece os termos técnicos |
| Equipe de TI | Recebe os chamados que o Bit abre e precisa saber o que já foi tentado |

O terceiro grupo foi o que mais pesou nas decisões. Se o Bit só entende quem escreve "credencial expirada", ele não serve para quem mais precisa de ajuda.

## 4. Faz sentido ser um chatbot?

Fiz essa pergunta porque o SERPRO coloca a análise de adequação como etapa. Para esse problema, acho que sim: a pessoa já descreve o problema conversando (é o que ela faria no telefone), as respostas são procedimentos curtos e o chat fica aberto a qualquer hora. Uma página de FAQ resolveria parte disso, mas obriga a pessoa a saber o nome do problema para achar a resposta, e o chatbot não.

Para problemas complexos ou raros, um chatbot não faz sentido, e por isso ele sempre oferece a saída para uma pessoa.

## 5. Resultados esperados

Resolver sozinho os problemas repetitivos, abrir chamado já dizendo qual é o assunto e o que já foi tentado (para a pessoa não ter que explicar tudo de novo) e nunca ser um caminho para alguém conseguir senha ou acesso de outra pessoa.

## 6. Persona

O nome é **Bit**. Pensei nele como aquele colega de TI paciente que explica sem fazer a pessoa se sentir burra.

- Fala de "você", com frases curtas e sem jargão. Quando precisa de um termo técnico (VPN, por exemplo), usa o nome que aparece na tela do usuário.
- Passo a passo sempre numerado, um passo por linha.
- Admite quando não entendeu em vez de chutar.
- Não usa emoji nem piada, porque quem chama o suporte geralmente está com pressa ou irritado.
- Quando a pessoa xinga, não rebate: reconhece que é chato e volta para o problema.

## 7. Acervo

Como a empresa é fictícia, eu mesmo escrevi a base de conhecimento (`data/base_conhecimento.json`). Ela tem 17 intenções e 131 frases de exemplo. Para os exemplos, tentei escrever do jeito que as pessoas realmente escrevem, misturando frases completas com frases curtas e informais.

A base também tem uma lista de sinônimos e abreviações ("n" vira "não", "pc" vira "computador", "net" vira "internet") e alguns erros de digitação comuns ("senah", "impresora").

## 8. Intenções

| Intenção | Exemplo | O que o Bit faz |
|---|---|---|
| senha | "esqueci minha senha" | Passo a passo do portal de autoatendimento |
| vpn | "a vpn não conecta" | Passo a passo da VPN |
| impressora | "papel preso na impressora" | Passo a passo da impressora |
| email | "o outlook não abre" | Passo a passo do e-mail |
| wifi | "a internet caiu" | Passo a passo do Wi-Fi |
| lentidao | "o computador está travando" | Passo a passo de lentidão |
| periferico | "o mouse não funciona" | Passo a passo de teclado, mouse e monitor |
| acesso_sistema | "acesso negado" | Explica o pedido com aprovação do gestor |
| solicitacao | "como instalo o excel" | Explica o pedido de programa ou equipamento |
| seguranca | "cliquei em um link estranho" | Orienta a desconectar e abre chamado urgente |
| pedido_indevido | "me passa a senha do joão" | Recusa e explica por quê |
| nao_resolveu | "não funcionou" | Abre chamado sobre o problema da conversa |
| abrir_chamado | "quero abrir um chamado" | Abre chamado |
| consultar_chamado | "como está o CH-0003?" | Mostra o status |
| falar_humano | "quero falar com uma pessoa" | Passa o ramal e o horário |
| saudacao / agradecimento | "oi", "valeu" | Cumprimenta ou encerra |

As dez primeiras são técnicas: quando uma delas é respondida, o Bit guarda na memória da sessão qual é o problema, para saber do que se trata se depois vier um "não funcionou".

## 9. UX writing

As regras que usei para escrever as mensagens:

1. Primeiro o que fazer, depois a explicação (se precisar).
2. Passo a passo numerado, com no máximo quatro passos.
3. Toda resposta deixa uma saída: abrir chamado ou o ramal 4000.
4. Quando não tem certeza, o Bit diz isso antes da resposta: *"Acho que você está falando de impressora. Se não for isso, me explica de outro jeito."*
5. Quando não sabe, não inventa: *"Não tenho certeza se entendi. Eu ajudo com senha, VPN, impressora (...). Pode explicar de outro jeito?"*
6. Mensagem sobre privacidade sem tom de bronca: *"Opa, parece que você digitou uma senha. Eu descartei essa mensagem e não guardei nada. O suporte nunca pede senha (...)"*

A regra 4 aparece mais do que eu esperava: nos testes, 4 de 24 frases válidas caíram nessa faixa de dúvida. Todas foram entendidas certo, mas é melhor o Bit avisar que pode ter errado do que responder com a mesma segurança acertando ou não.

## Referências

- SERPRO. *Desenvolvendo Chatbots: fluxo de trabalho*. Disponível em: https://serprobots.estaleiro.serpro.gov.br/docs/dev/
- VALÉRIA, Kadidja. *Guia de Estudos A1: Criação de Agentes de IA e Ética Aplicada*. UDF Centro Universitário, 2026.
