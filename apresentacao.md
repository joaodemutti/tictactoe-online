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
> "Boa tarde. Nosso projeto é um **Jogo da Velha Online**. A ideia parece simples — todo mundo
> conhece o jogo da velha — mas o nosso é **multiplayer e em tempo real**: dois jogadores em
> computadores diferentes entram no site, se convidam e jogam ao vivo, vendo a jogada do outro na
> hora.
>
> Como a matéria é Lógica de Programação, o **foco do trabalho é a lógica**: como representamos o
> tabuleiro no código e qual o **algoritmo que decide quem ganhou ou se deu velha**. Esse é o tema
> principal, e a Pessoa 4 vai entrar fundo nele.
>
> O escopo completo é: o jogador faz **login**, vê **quem está online**, **convida** alguém, os dois
> **escolhem X ou O**, **jogam em tempo real** e ainda podem **conversar por chat**.
>
> Pra apresentar, a gente se dividiu assim: o/a **[Pessoa 2]** vai falar das **tecnologias** que
> usamos; o/a **[Pessoa 3]** mostra a **arquitetura e o banco de dados**; o/a **[Pessoa 4]** explica
> as **funcionalidades e o algoritmo do jogo**, que é o coração do trabalho; e eu volto no final pra
> uma **demonstração** e a conclusão. Passo pro/pra **[Pessoa 2]**."

---

## PESSOA 2 — Stack & Tecnologias (~2 min)

> Objetivo: **só citar/listar** as tecnologias e a organização do código.

**[SLIDE 3 — Stack]**
- **Back-end:** Python · **FastAPI** · Uvicorn · WebSockets
- **Banco de dados:** **PostgreSQL** · SQLAlchemy (ORM async) + asyncpg · Alembic (migrações)
- **Autenticação:** JWT em cookie · bcrypt (hash de senha)
- **Front-end:** **Jinja2** (HTML) · Tailwind CSS · **GSAP + SVG** (animações) · **JavaScript puro (sem framework)**

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

FALA:
> "Eu vou listar as tecnologias. No **back-end** usamos **Python** com o framework **FastAPI**, e a
> comunicação em tempo real é feita por **WebSockets**.
>
> O **banco de dados** é **PostgreSQL**. A gente não escreve SQL na mão: usa o **SQLAlchemy**, que
> traduz objetos Python em tabelas, e o **Alembic** pra versionar a estrutura do banco.
>
> O **login** usa **JWT** — um token guardado num cookie — e a senha nunca é salva em texto: passa
> por **bcrypt**.
>
> No **front-end**, as páginas são montadas com **Jinja2**, o visual é **Tailwind**, e as animações
> do tabuleiro — o X e o O sendo desenhados — usam **GSAP com SVG**. E um ponto importante: o nosso
> **JavaScript é puro, escrito do zero, sem nenhum framework**.
>
> Sobre a **organização** (slide): separamos bem as responsabilidades — `routes/` são as páginas e a
> API, `ws/` é o tempo real, `services/` são as regras, e o **módulo** `game/logic.py` é o
> **algoritmo do jogo** — esse é o tema central, que a Pessoa 4 vai abrir. Passo pro/pra
> **[Pessoa 3]**."

---

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
> "Agora, como o sistema é organizado. Olhando o diagrama da esquerda pra direita: na **esquerda**
> fica o **banco PostgreSQL**; no **meio**, o **servidor FastAPI**, que tem as rotas, a API, os
> serviços com as regras e o tempo real; e na **direita**, o **navegador**, que é o que o jogador
> vê.
>
> O navegador conversa com o servidor por **três canais**: as **páginas HTML**, montadas pelo
> Jinja2; a **API**, que troca dados em **JSON** — por exemplo, pra buscar jogadores ou enviar um
> convite; e o **WebSocket**, que é um canal que fica **aberto o tempo todo** nos dois sentidos — é
> isso que dá o **tempo real**. E o servidor fala com o banco pelo **SQLAlchemy**.
>
> Sobre o **banco** (slide 6), são **5 tabelas**. A `users` são os jogadores. A `matches` guarda o
> **estado de cada partida** — inclusive o tabuleiro. Como uma partida tem **dois** jogadores, a
> gente usa a tabela `match_players` no meio, que também guarda o papel de cada um, X ou O. A
> `moves` registra **cada jogada** feita, e a `messages` guarda o **chat** entre os jogadores.
>
> Com essa estrutura no lugar, passo pro/pra **[Pessoa 4]**, que vai mostrar o que o sistema faz e,
> principalmente, **como o algoritmo funciona**."

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

**[SLIDE 9 — O algoritmo de vitória (`game/logic.py`)]**
```python
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

**[SLIDE 10 — As regras (validação no servidor)]**
- Antes de aceitar a jogada, o servidor confere: **é a vez?** · partida **ativa?** · casa **vazia?** · jogador tem **papel?**
- Só então: marca a casa → checa vitória/empate → **passa o turno** → salva
- **Trava no banco** evita problema se os dois clicarem ao mesmo tempo

FALA:
> "Eu vou falar do que o sistema faz e, principalmente, do **algoritmo**.
>
> Rápido nas **funcionalidades**: você se cadastra, vê **quem está online ao vivo**, **convida**
> alguém, escolhem **X ou O**, **jogam em tempo real**, o sistema detecta **vitória ou velha**, e dá
> pra **conversar no chat**. E o **caminho de uma jogada** é esse: eu clico numa casa, o servidor
> **valida** se é a minha vez e se a casa está vazia, o algoritmo confere se alguém ganhou, salva, e
> **transmite pros dois jogadores**. Importante: **quem decide é o servidor**, o navegador só
> desenha.
>
> Agora o coração (slide 8). A decisão principal é **como representar o tabuleiro**: em vez de uma
> matriz 3×3, usamos **uma lista de 9 posições, de 0 a 8**, onde cada casa guarda `X`, `O` ou vazio.
>
> Por que isso ajuda? Olhem o algoritmo (slide 9). Existem **só 8 jeitos de ganhar**: 3 linhas, 3
> colunas e 2 diagonais. A gente escreve essas 8 combinações como trios de índices nessa lista
> `_WIN_LINES`. A função `check_winner` **percorre as 8** e pergunta: *'a casa está preenchida e as
> três são iguais?'*. Se forem, devolve quem ganhou; senão, `None`. São **no máximo 8 verificações**
> — rápido e constante. O empate é direto: se as **9 casas estão preenchidas** e ninguém ganhou, deu
> velha.
>
> E pra ninguém trapacear, toda jogada passa por uma **validação no servidor** (slide 10): é a
> **vez** dele? a casa está **vazia**? Só então a jogada vale. Devolvo pro/pra **[Pessoa 1]**."

---

## PESSOA 1 (VOCÊ) — Fechamento (~3 min)

> A demonstração ao vivo vem aqui. A **conclusão você ainda vai escrever** — abaixo ficam só os
> espaços e algumas sugestões de tópicos que você pode usar.

**[SLIDE 11 — Demonstração ao vivo]**
- Abrir o jogo em **2 abas/janelas** e jogar uma partida rápida (~30–60s)
- Mostrar: convite → escolha de X/O → jogadas sincronizadas → vitória/velha → (chat, se der tempo)
- **Plano B:** GIF/vídeo curto gravado antes (caso a internet falhe)

**[SLIDE 12 — Conclusão]** *(a ser escrita por você)*
- Espaço reservado para o seu fechamento
- Tópicos opcionais que você pode incluir: hospedagem na nuvem · futuro (ex.: oponente de IA com
  algoritmo **Minimax**, revanche, ranking)

FALA (fechamento):
> "Pra fechar, deixa eu **mostrar o jogo funcionando**." → *(fazer a demonstração)*
>
> *(conclusão — a ser escrita por você)*

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
