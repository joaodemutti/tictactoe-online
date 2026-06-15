# Apresentação — Tic-Tac-Toe Online

## Contexto

Projeto acadêmico do **1º semestre de ADS**, matéria **Lógica de Programação**. É um **jogo da
velha multiplayer online, em tempo real**, com banco de dados, login e chat. O foco do trabalho é a
**lógica**: a forma de representar o tabuleiro e o algoritmo que decide vitória/empate.

Apresentação falada por **4 pessoas em ~13–14 min**. A **pessoa 1 (você)** abre e fecha (partes não
técnicas); **pessoas 2, 3 e 4** cobrem a parte técnica na ordem **Stack → Arquitetura →
Funcionalidades + Algoritmo** (funil do geral ao específico, terminando no algoritmo — o tema da
matéria — como clímax antes da conclusão).

> Este arquivo **é a apresentação**: para cada pessoa há o conteúdo do slide (tópicos) + o roteiro
> do que falar (`FALA:`) + o tempo. Os blocos `FALA:` são um guia, não precisa decorar.

## Divisão e tempo

| # | Quem | Parte | Slides | Tempo |
|---|------|-------|--------|-------|
| 1 | **Você** | Abertura: Introdução · Escopo · Tema · Roteiro | 1–2 | ~2,0 min |
| 2 | Pessoa 2 | Stack & Tecnologias (+ pastas e libs) | 3–4 | ~2,0 min |
| 3 | Pessoa 3 | Arquitetura (diagrama) + Banco (DER) | 5–6 | ~3,0 min |
| 4 | Pessoa 4 | **Funcionalidades + Algoritmo ★** | 7–10 | ~4,0 min |
| 1 | **Você** | Fechamento: Demonstração ao vivo + Conclusão | 11–12 | ~3,0 min |
| | | **Total** | **12 slides** | **~14 min** |

---

## PESSOA 1 (VOCÊ) — Abertura (~2 min)

**[SLIDE 1 — Capa]**
- Título: **Tic-Tac-Toe Online — Jogo da Velha Multiplayer em Tempo Real**
- Nomes dos 4 integrantes · Disciplina: Lógica de Programação · ADS – 1º semestre

**[SLIDE 2 — Introdução / Tema / Roteiro]**
- O que é: jogo da velha jogado por 2 pessoas pela internet, ao vivo
- Tema central: **representação do tabuleiro e o algoritmo que decide o jogo**
- Escopo: login → ver quem está online → convidar → jogar em tempo real → chat
- **Roteiro de hoje** (quem fala o quê): Tecnologias · Arquitetura+Banco · Funcionalidades+Algoritmo · Demonstração

FALA:
> Boa noite, sou o João integrante de um grupo composto por 4 pessoas, sendo eles Kauan, Lucas e Victor.
> Antes de começar, adotamos uma apresentação dinâmica e interativa então queria disponibilizar o QRCode e Link do nosso projeto em produção que estará no canto superior direito em todos os slides, eu icentivo vocês acessarem pq assim nos ajuda a testar e criar a primeira experiência de uso do nosso sistema em produção, e assim a gente até se diverte um pouco.
> Bom nosso tema/problema abordado foi a solução do algoritmo do jogo da velha. Por mas que pareça um tema simples nossa solução foi a proposta de um projeto com escopo MVP que é uma sigla que significa Minimo Projeto Viavel, esse termo na TI é uma forma de fazer a entrega de um produto que não remete sua forma final contendo espaços para melhorias e funcionalidades futuras.
> Com isso desenvolvemos um jogo que possibilita disputar com seus amigos em tempo real.
> A seguir o Kauan vai abordar a Stack e Tecnologias Utilizadas, depois o Lucas vai relatar nossa arquitetura do sistema, finalizando com o Victor explicando as funcionalidades com enfase na solução do algoritmo do jogo da velha utilizando matrizes em python.
> Kauan, pode seguir por favor.

---

## PESSOA 2 — Stack & Tecnologias (~2 min)

> Objetivo: **só citar/listar** as tecnologias e a organização do código.

**[SLIDE 3 — Stack]**
- **Back-end:** Python · **FastAPI** · Uvicorn · WebSockets
- **Banco de dados:** **PostgreSQL** · SQLAlchemy (ORM async) + · Alembic (migrações)
- **Autenticação:** JWT em cookie . (hash de senha)
- **Front-end:** **Jinja2** (HTML) . **JavaScript puro (sem framework)**

FALA:
> Boa noite, sou Kauan e nossa Stack adotada para projetar o sistema foi a seguinte:
> A linguagem de programação principal foi Python com o framework FastApi incluindo rotas WebSocket
> Para o banco de dados foi utilzado o Postgres com as bibliotecas Python SQLAlchemy e Alembic
> A autenticação StateLess é baseada em JWT (Json Web Token) com hash de senha
> e para o front a biblioteca Python Jinja2 para os templates HTML CSS e JS
> Agora passo a palvara para o Lucas


## PESSOA 3 — Arquitetura + Banco (~3 min)

> Objetivo: mostrar **como o sistema é organizado** (diagrama) e a **estrutura do banco** (DER).
> Deixar o "como uma jogada funciona" para a Pessoa 4.


**[SLIDE 5 — Diagrama de arquitetura]** (banco à esquerda · servidor no meio · navegador à direita)
```
   ┌──────────────┐        ┌───────────────────────────┐         ┌────────────────────┐
   │  PostgreSQL  │◄─ SQL ─►│   SERVIDOR — FastAPI      │         │     NAVEGADOR      │
   │   (banco)    │ Alchemy │   (Python)                │◄─ Jinja2/HTML ─┤  (cliente)         │
   │              │(asyncpg)│  rotas · API · serviços   │   (páginas)    │  HTML · Tailwind   │
   │  5 tabelas   │         │  game/logic.py · WebSocket│◄─ API (JSON) ──►│  JS puro · GSAP    │
   │              │         │                           │◄─ WebSocket ──►│  hub.js · match.js │
   └──────────────┘        └───────────────────────────┘  (tempo real)  └────────────────────┘
       (esquerda)                    (meio)                                   (direita)
```
- O cliente conversa com o servidor por **3 canais**: páginas **Jinja2/HTML**, **API (JSON)** e **WebSocket** (tempo real)

FALA:
> Boa noite, sou o Lucas e nesse slide podemos visualizar a arquitetura funcional do nosso sistema.
> Como podemos ver ela possui 3 camadas, a princpal camada oquestradora é o servidor FastAPI em Python centralizada no diagrama
> Nas laterais são os extremos do sistema, o Banco de Dados a esquerda e o Browser do cliente a direita
> Também podemos ver os meios de comunição entre elas, reparem que possuímos 3 tipos de rotas entre o servidor e cliente, qualquer dúvida explicamos os detalhes ao finalizar a apresentação
> A seguir vamos análisar o Modelo Entidade Relacionamento do Banco de dados.

**[SLIDE 6 — Banco de dados (DER)]**
```
  users ──<  match_players  >── matches        (N:N — 2 jogadores por partida, papel X/O)
  users ──<  moves          >── matches        (cada jogada: quem, qual partida, posição 0–8)
  users ──<  messages       >── users          (chat: remetente → destinatário)

  matches guarda o ESTADO do jogo: status · board (vetor de 9) · turno atual · vencedor

  Legenda:  A ──< B  =  um A tem vários B (1:N)        A ──< J >── B  =  relação N:N pela tabela J
```
- 5 tabelas: **users · matches · match_players · moves · messages**

FALA: 
> Como podemos ver possuimos 5 tabelas sendo elas os usuarios, as partidas, a relação entre jogador e cada partida, as jogadas de cada jogador e por último as mensagens enviadas por chat

**[SLIDE 4 — Organização do código + bibliotecas]**
```
app/
  main.py        → inicia o app e conecta as rotas
  models.py      → as tabelas do banco (SQLAlchemy)
  auth.py        → login: JWT + senha (bcrypt)
  routes/        → páginas e API HTTP (auth, hub, match, messages)
  ws/            → tempo real (manager, hub, match, chat)
  services/      → regras de negócio (game_service, ...)
  game/logic.py  → ★ o algoritmo do jogo (tema principal)
static/js/       → JavaScript do navegador (hub.js, match.js)
templates/       → páginas HTML (Jinja2)
```
- Libs principais: FastAPI, SQLAlchemy, websockets, python-jose (JWT), passlib/bcrypt, Jinja2, GSAP

> Por fim, esse é o slide da nossa organização de pastas adotada no sistema
> Agora o Victor vai finalizar abordando as funcionalidades do sistema com enfase na solução do algoritmo do jogo da velha.

---

## PESSOA 4 — Funcionalidades + Algoritmo ★ (~4 min)

> **Tema principal.** Começa rápido pelas funcionalidades + o fluxo de uma jogada, e concentra o
> tempo no algoritmo de `game/logic.py` e na validação.

**[SLIDE 7 — Funcionalidades + como uma jogada acontece]**
- O que o sistema faz: login · ver **jogadores online** ao vivo · **convidar** · escolher **X/O** · **jogar em tempo real** · detectar **vitória/empate** · **chat**
- Caminho de uma jogada:
  1. Jogador **clica** numa casa → navegador envia a posição pelo WebSocket
  2. Servidor **valida** (é a vez dele? casa vazia?) → aplica
  3. `game/logic.py` checa **vitória/empate** → salva no banco
  4. Servidor **transmite pros dois** jogadores → ambos **desenham** X/O (GSAP)
- **Quem decide é sempre o servidor** — o navegador só desenha

**[SLIDE 8 — A ideia central: o tabuleiro é um vetor de 9]**
```
índices:      0 | 1 | 2        cada casa guarda:  "X"  ·  "O"  ·  None (vazia)
            -----------
              3 | 4 | 5        Ex.: ["X", None,"O",
            -----------               None,"X", None,
              6 | 7 | 8               "O", None,"X"]   → diagonal 0-4-8 = X venceu
```
- Decisão-chave: **uma lista de 9 posições (0 a 8)** em vez de uma matriz 3×3 → simplifica tudo

FALA:
> Boa noite, sou o Victor e as nossas funcionalidades desenvolvidas no sistema foram um fluxo simples de cadastro e login, um dashboard servindo como hub para jogadores onlines, um chat integrado para comunicação entre eles e a tela de partida entre jogadores com escolha de quem vai ser o X ou o Circulo, que define quem começa.
> Nosso sistema funciona integralmente em tempo real com uso do protocolo WebSocket estabelecendo comunicação entre Servidor e Cliente

**[SLIDE 9 — O algoritmo de vitória (`game/logic.py`)]**
```python
board = [
  "X",  "O",  "O",  # 0, 1, 2
  None, "X",  None, # 3, 4, 5
  None, None, "X"   # 6, 7, 8
]

_WIN_LINES = [
    (0,1,2), (3,4,5), (6,7,8),   # 3 linhas
    (0,3,6), (1,4,7), (2,5,8),   # 3 colunas
    (0,4,8), (2,4,6),            # 2 diagonais
]

def check_winner(board):
    for a, b, c in _WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]      # devolve "X" ou "O"
    return None

def is_draw(board):
    return all(cell is not None for cell in board)
```

FALA:
> Agora aprofundando no tema principal do projeto, esse slide mostra a solução do algoritmo em python com matrizes do jogo da velha.
> Já pensaram como verificar quem venceu ou se deu empate nesse jogo?
> Ná prática é fácil, formamos uma sequência de 3 símbolos iguais, porém, na implementação dessa validação precisamos verificar cada possibilidade de vitória.
> Podemos visualizar isso sendo realizado nos elementos desse código
> Em primeiro lugar temos a representação do tabuleiro em uma lista e suas posições de jogada
> depois cada combinação de vitória possível entre as posições preenchidas
> depois são as funções que verificam cada combinação com o estado atual do tabuleiro ou se deu empate
---

## PESSOA 1 (VOCÊ) — Fechamento (~3 min)

> A demonstração ao vivo vem aqui. A **conclusão você ainda vai escrever** — abaixo ficam só os
> espaços e algumas sugestões de tópicos que você pode usar.

**[SLIDE 11 — Demonstração ao vivo]**
- Obrigado
- nomes do integrantes

---

## Dicas de ensaio
- **Cronometrar** 1 ensaio completo. Se passar de 15 min, corte falas dos slides **4 e 6** (são os
  mais enxugáveis). O slide do **algoritmo (9) não** deve ser cortado.
- **Transições**: cada pessoa termina passando a palavra nominalmente pra próxima (já está nas
  falas) — evita silêncio entre os trechos.
- **No slide 9**, a Pessoa 4 deve **apontar pra `_WIN_LINES` e pra linha do `if`** enquanto fala — é
  o momento-chave.
- **Demonstração**: testar a abertura em 2 abas **antes** da apresentação; ter o GIF/vídeo como
  plano B.

## Como validar a apresentação
1. **Confere com o código?** Cada afirmação técnica saiu de: `app/game/logic.py` (algoritmo),
   `app/services/game_service.py` (validação/turno/trava), `app/ws/` (tempo real), `app/routes/`
   (páginas + API JSON), `app/models.py` (5 tabelas), `requirements.txt` (libs).
2. **Tempo**: ensaio cronometrado deve cair em **10–15 min** (alvo ~14).
3. **Demo**: rodar localmente (`uvicorn app.main:app --reload`), abrir `localhost:8000` em duas abas
   e confirmar que a partida sincroniza antes de apresentar ao vivo.
