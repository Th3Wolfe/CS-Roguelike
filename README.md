# CS Major Manager (CS-Roguelike)

Um simulador roguelike de gestão de equipes de Counter-Strike. Monte um time com jogadores de diferentes eras do competitivo, dispute uma campanha inteira de Major — fase de grupos, playoffs, veto de mapas BO3 e eventos narrativos com escolhas que afetam o desempenho do time — até erguer o troféu ou ser eliminado.

Construído em Python (Flask) no back-end com uma interface web single-page em HTML/JS puro.

## Funcionalidades

- **Draft de equipe** — monte seu line-up escolhendo jogadores reais (ou candidatos gerados) de diferentes eras da cena competitiva (2015, 2018, 2021, 2023, 2025).
- **Atributos no estilo HLTV** — rating, ADR, KAST, impacto, clutch, consistência e mais, com cinco papéis (IGL, AWP, Entry, Support, Lurker).
- **Sistema de traços (traits)** — personalidades como Veterano, Clutcher, Prodígio ou Ego Elevado, que aplicam bônus/penalidades passivos aos atributos.
- **Proficiência de mapas** — defina 3 mapas de domínio total e 2 de domínio parcial antes da campanha.
- **Veto de mapas BO3** — engine completa de veto (ban/ban/pick/pick/ban/ban/decider) com coin flip e escolha de lado, replicando o formato competitivo real.
- **Campanha estruturada** — fase de grupos seguida de playoffs (quartas, semis, final), com bracket e histórico de resultados.
- **Eventos narrativos** — escolhas de evento (drama interno, lesões, polêmicas, boas notícias) que alteram sinergia, atributos e buffs do time.
- **Sistema de buffs** — efeitos temporários, por jogador ou por time, que decaem a cada rodada.
- **Save/Load** — salve e carregue o progresso da campanha em qualquer momento.
- **Códigos de compartilhamento** — gere e decodifique um código compacto que representa o seu time, para compartilhar com outras pessoas.
- **Atualização de base de dados via API** — script auxiliar para atualizar a era "2025" com dados ao vivo da CS API.

## Arquitetura

```
cs_roguelike_v6/
├── app.py                     # Servidor Flask e rotas da API REST
├── models/                    # Entidades de domínio (dataclasses)
│   ├── player.py              #   Jogador, atributos, papéis, status
│   ├── team.py                #   Time, sinergia, buffs, score
│   ├── traits.py              #   Traços de personalidade
│   ├── buff.py                #   Buffs temporários
│   ├── campaign.py            #   Estágios, histórico, resultados de série
│   ├── opponent.py            #   Times adversários
│   ├── event.py               #   Eventos narrativos e escolhas
│   └── map_config.py          #   Pool de mapas do CS2, bias CT/T
├── systems/                   # Lógica de jogo
│   ├── team_factory.py        #   Geração de times/candidatos por era, share codes
│   ├── campaign_manager.py    #   Orquestra grupos, playoffs e bracket
│   ├── match_resolver.py      #   Resolução de partidas BO3
│   ├── veto_engine.py         #   Engine de veto de mapas
│   └── save_system.py         #   Persistência de partidas salvas
├── events/
│   └── event_manager.py       #   Seleção e aplicação de eventos narrativos
├── data/                      # Bases de dados em JSON (jogadores, eventos)
├── ui/
│   └── index.html             #   Front-end single-page (HTML/CSS/JS)
├── saves/                     # Partidas salvas (gerado em runtime)
├── update_db_from_csapi.py    # Script para atualizar a era 2025 via API externa
├── requirements.txt
└── Procfile                   # Deploy em plataformas estilo Heroku
```

## Pré-requisitos

- Python 3.10+
- pip

## Instalação

```bash
git clone <url-do-repositorio>
cd cs_roguelike_v6
pip install -r requirements.txt
```

## Executando localmente

```bash
python app.py
```

O servidor inicia em `http://localhost:5000`. Abra esse endereço no navegador para acessar a interface.

Para produção (usado pelo `Procfile`):

```bash
gunicorn app:app
```

## Como jogar

1. **Draft** — escolha uma era e monte seu time, jogador por jogador, por papel.
2. **Proficiência de mapas** — selecione 3 mapas de domínio total e 2 de domínio parcial.
3. **Veto** — antes de cada série, dispute o veto de mapas contra o adversário (ban/pick/side).
4. **Eventos** (opcional) — responda a eventos narrativos que surgem entre as séries.
5. **Jogue a série** — o resultado é resolvido com base no score do time, atributos e fator aleatório.
6. **Avance na campanha** — vença a fase de grupos e os playoffs para conquistar o Major.
7. **Salve/Carregue** a qualquer momento, ou gere um código de compartilhamento do seu time.

## API

O back-end expõe uma API REST consumida pela interface web. Principais endpoints:

| Método | Rota                        | Descrição                                          |
|--------|------------------------------|-----------------------------------------------------|
| GET    | `/api/eras`                  | Lista as eras disponíveis para draft                |
| POST   | `/api/draft_team`            | Sorteia um time real de uma era                     |
| POST   | `/api/draft_candidates`      | Lista candidatos para um papel                      |
| POST   | `/api/new_game`              | Inicia uma nova campanha                            |
| GET    | `/api/map_pool`              | Retorna o pool de mapas ativo do CS2                |
| POST   | `/api/set_map_proficiency`   | Define mapas de proficiência total/parcial          |
| POST   | `/api/start_veto`            | Inicia o veto de mapas da próxima série             |
| POST   | `/api/veto_action`           | Executa uma ação de veto (ban/pick/side)            |
| GET    | `/api/state`                 | Estado atual do time e da campanha                  |
| GET    | `/api/get_events`            | Eventos narrativos pendentes                        |
| POST   | `/api/apply_choice`          | Aplica a escolha de um evento                       |
| POST   | `/api/play_series`           | Resolve a próxima série                             |
| GET    | `/api/history`               | Histórico de séries jogadas                         |
| POST   | `/api/save`                  | Salva a partida atual                               |
| GET    | `/api/saves`                 | Lista partidas salvas                                |
| POST   | `/api/load`                  | Carrega uma partida salva                            |
| POST   | `/api/share_decode`          | Decodifica um código de compartilhamento de time     |

## Atualizando a base de jogadores

A era "2025" pode ser atualizada com dados ao vivo da [CS API](https://api.csapi.de) (gratuita, sem necessidade de chave):

```bash
pip install requests
python update_db_from_csapi.py             # atualiza data/players_database.json
python update_db_from_csapi.py --dry-run   # mostra o que seria alterado, sem salvar
python update_db_from_csapi.py --debug     # inspeciona a estrutura retornada pela API
```

## Stack técnica

- **Back-end:** Python, Flask, sessões server-side em memória
- **Front-end:** HTML/CSS/JS puro (single-page, sem build step)
- **Persistência:** JSON em disco (`data/`, `saves/`)
- **Deploy:** Gunicorn + Procfile (compatível com Heroku e similares)

## Aviso

Este é um projeto não oficial, criado por fãs, sem qualquer vínculo com a Valve, ESL ou outras organizadoras de torneios de Counter-Strike. Nomes de times e jogadores reais são usados apenas para fins de simulação e entretenimento.
