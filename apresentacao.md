# Apresentação — Jogo da Velha Online

## PESSOA 1 (VOCÊ) — Abertura (~2 min)

**[SLIDE 1 — Capa]**

CLAUDE PRECISO DISPNIBILIZAR O QR CODE E  O LINK NO PRIMEIRO OU SEGUNDO SLIDE

COLOQUE O QRCODE E LINK NO CANTO SUPERIOR EM TODOS OS SLIDES SEM ATRAPALHAR A DISPOSIÇÃO DO CONTEÚDO

LINK: https://jogodavelha-online.com.br

QRCODE: TEXT PURO DO LINK
...

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
- **Back-end:** Python · **FastAPI** · WebSockets
- **Banco de dados:** **PostgreSQL** · SQLAlchemy (ORM async) + · Alembic (migrações)
- **Autenticação:** JWT em cookie . (hash de senha)
- **Front-end:** **Jinja2** (HTML,CSS,JS) . **JavaScript puro (sem framework)**

- Libs principais: FastAPI, SQLAlchemy, websockets, python-jose (JWT), passlib/bcrypt, Jinja2, GSAP

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


**[SLIDE 4 — Diagrama de arquitetura]** (banco à esquerda · servidor no meio · navegador à direita)

CLAUDE FAVOR FAZER O DIAGRAMA COM O MOTOR GRAFICO Q VC TIVER 
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
> Também podemos ver os meios de comunição entre elas, reparem que possuímos 3 tipos de rotas entre o servidor e cliente
> A seguir vamos análisar o Modelo Entidade Relacionamento do Banco de dados.

**[SLIDE 5 — Banco de dados (DER)]**

CLAUDE FAVOR FAZER O DER COM MOTOR GRAFICO Q VC TIVER DISPONIVEL

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

**[SLIDE 7 — Organização do código + bibliotecas]**

CLAUDE AQUI DEVE SER UM BLOCO DE CÓDIGO ``` E NAO TEXTO PURO

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

> Por fim, esse é o slide da nossa organização de pastas adotada no sistema
> Agora o Victor vai finalizar abordando as funcionalidades do sistema com enfase na solução do algoritmo do jogo da velha.

---

## PESSOA 4 — Funcionalidades + Algoritmo ★ (~4 min)

> **Tema principal.** Começa rápido pelas funcionalidades + o fluxo de uma jogada, e concentra o
> tempo no algoritmo de `game/logic.py` e na validação.

**[SLIDE 7 — Funcionalidades]**

CLAUDE COLOQUE PRINT DA TELA DO TABULEIRO DO JOGO QUE VOU ANEXAR NO CHAT NESSE SLIDE

FALA:
> Boa noite, sou o Victor e as nossas funcionalidades desenvolvidas no sistema foram um fluxo simples de cadastro e login, um dashboard servindo como hub para jogadores onlines, um chat integrado para comunicação entre eles e a tela de partida entre jogadores com escolha de quem vai ser o X ou o Circulo, que define quem começa.
> Nosso sistema funciona integralmente em tempo real com uso do protocolo WebSocket estabelecendo comunicação entre Servidor e Cliente

**[SLIDE 9 — O algoritmo de vitória (`game/logic.py`)]**

CLAUDE ESSE SLIDE TEMQ SER O BLOCO DE CODIGO EM PYTHON ```python

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
- Obrigado (CALUDE MELHORE ESSA FRASE)
- nomes do integrantes

---


