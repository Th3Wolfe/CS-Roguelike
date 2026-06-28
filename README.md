# CS Major Manager (CS-Roguelike)

Um simulador roguelike de gestão de equipes de Counter-Strike. Monte um time com jogadores de diferentes eras do competitivo, dispute uma campanha inteira de Major — fase de grupos (formato Swiss), playoffs single-elimination e veto de mapas BO3 — até erguer o troféu ou ser eliminado.

Construído em Python (Flask) no back-end com uma interface web single-page em HTML/JS puro.

---

## Funcionalidades

### Time e jogadores
- **Draft de equipe** — monte seu line-up escolhendo jogadores reais (ou candidatos gerados) de diferentes eras da cena competitiva: 2015, 2018, 2021, 2023, 2025.
- **Atributos no estilo HLTV** — rating, ADR, KAST, impacto e KPR, com cinco papéis (IGL, AWP, Entry, Support, Lurker). Cada papel tem pesos diferentes para o cálculo de score.
- **Status dos jogadores** — quatro variáveis de condição: moral, form, físico e mental. Variam a cada série jogada e afetam o score efetivo do jogador.
- **Sistema de traços (traits)** — 10 personalidades distintas que aplicam bônus/penalidades passivos. Ver tabela completa abaixo.
- **Proficiência de mapas** — escolha 2 mapas de domínio total (+6pp de win rate) e 3 de domínio parcial (neutro) antes da campanha. Os 2 mapas restantes do pool aplicam penalidade de -10pp.

### Campanha
- **Formato Swiss** — Stage 1 e Stage 2 com 16 times cada (incluindo o jogador), pareamento por recorde (W-L), avançando com 3 vitórias ou eliminado com 3 derrotas.
- **Bracket completo** — todos os 15 times NPC têm Swiss simulado em paralelo. O bracket mostra os confrontos do round atual antes de você jogar, exatamente como será resolvido — sem re-embaralhamento depois.
- **Playoffs single-elimination** — 8 times qualificados, seedados por força, com confrontos 1v8, 2v7, 3v6, 4v5. SF e Final são simulados automaticamente para os duelos NPC-NPC; o jogador enfrenta o adversário do seu lado do bracket.
- **Dificuldade elástica** — se o seu time estiver muito acima da força esperada para o estágio, o adversário recebe um boost de catch-up. Os adversários também ganham bônus de momentum conforme a campanha avança, espelhando a evolução natural do seu time.

### Mecânicas de jogo
- **Veto de mapas BO3** — sequência completa (ban/ban/pick/pick/ban/ban/decider) com coin flip. O adversário tem um perfil persistente de mapa: mapas preferidos, mapas que detesta e preferência de lado (CT/T), gerado deterministicamente pelo nome do time — o mesmo adversário sempre joga da mesma forma.
- **Sistema de táticas** — para cada half de cada mapa, escolha uma tática de CT ou T. Sistema rock/paper/scissors com modificadores de até ±0.07–0.08 na win rate por round. A IA adversária adapta a tática conforme o estágio (aleatória no Stage 1, reativa no Stage 2, 80% de chance de contra-tática nos playoffs).
- **Simulação MR12** — cada mapa é jogado nos formatos CS2 reais: 12 rounds por half, OT com 6 rounds (MR3), CT/T bias por mapa baseado em dados pro 2025-2026.
- **Scoreboard por série** — kills, deaths, assists, KD, ADR e KPR simulados individualmente para cada jogador do seu time e do adversário (usando atributos reais quando o adversário tem jogadores reais).
- **MVP de estágio** — ao terminar cada estágio (Stage 1, Stage 2, Playoffs), o MVP é calculado com base em rating agregado (KD × 0.4 + KPR/0.68 × 0.35 + ADR/80 × 0.25) de todos os jogadores de ambos os lados.

### Progressão e efeitos
- **Fadiga e recuperação** — cada série consome físico (10–18 pts) e mental (6–12 pts, +7 em derrota). Entre estágios, o time descansa automaticamente (22 pts no intervalo S1→S2, 28 pts no intervalo S2→Playoffs, 18 pts entre rounds de playoffs).
- **Efeitos de traço pós-série** — Workaholic perde mais físico; Tilta Fácil perde mais mental em derrotas; Veterano e Piadista resistem melhor ao desgaste mental.
- **Sistema de buffs** — efeitos temporários (por jogador ou por time) com duração em séries, gerados por eventos. Decaem a cada série e são removidos quando expiram. A sinergia do time decai 10% por série para evitar snowball de eventos.
- **Eventos narrativos** — sistema opt-in de eventos (drama interno, lesões, polêmicas, boas notícias) que alteram atributos, moral, sinergia e buffs. Divididos em três categorias: performance, relações e outros. Até 2 eventos por série; sem repetição dentro de uma mesma campanha.

### Utilitários
- **Save/Load** — salve e carregue o progresso da campanha em qualquer momento.
- **Códigos de compartilhamento** — gere e decodifique um código compacto que representa o seu time.
- **Atualização de base de dados via API** — script auxiliar para atualizar a era "2025" com dados ao vivo da CS API.

---

## Traços de personalidade

| Traço | Bônus/Penalidade | Efeito na campanha |
|-------|------------------|--------------------|
| Veterano | consistência +1, clutch +1 | Resiste melhor ao desgaste mental |
| Clutcher | clutch +2, consistência -1 | — |
| Workaholic | aim +1, tactics +1 | Perde mais físico por série |
| Tilta Fácil | consistência -2, clutch -1 | Perde muito mais mental em derrotas |
| Ego Elevado | aim +1, comunicação -2 | — |
| Prodígio | aim +2, consistência -1, comunicação -1 | — |
| IGL Nato | tactics +2, comunicação +2, aim -1 | — |
| Piadista | comunicação +1, consistência -1 | Resiste melhor ao desgaste mental |
| Inconsistente | aim +1, consistência -3 | Variação aleatória de ±4 no mental por série |
| Streamer | clutch +1, comunicação +1, consistência -1 | — |

---

## Sistema de táticas

Cada half de cada mapa tem uma escolha tática independente. As táticas formam um sistema de pedra/papel/tesoura com modificadores de win rate por round (±0.07–0.08).

**Lado CT**

| Tática | Vence contra | Perde para |
|--------|-------------|------------|
| 🔫 Agressivo | Slow Default | Fast Rush |
| 🛡️ Passivo / Hold | Fast Rush | Slow Default |
| 🔄 Retake | Slow Default | Anti-eco |

**Lado T**

| Tática | Vence contra | Perde para |
|--------|-------------|------------|
| ⚡ Fast Rush / Execute | CT Agressivo | CT Passivo |
| 🐢 Slow Default | CT Retake | Fast Rush |
| 💰 Anti-eco / Push | CT Passivo | CT Retake |

**Adaptação da IA adversária por estágio:**
- Stage 1: aleatória
- Stage 2: 60% de chance de contra-tática se perdeu o half anterior
- Playoffs: 80% de chance de contra-tática após derrota; 60% mesmo sem perder

---

## Pool de mapas (ativo em junho 2026)

| Mapa | CT bias (pro) | Observação |
|------|:---:|---|
| Anubis | 44.5% | Fortemente T-sided |
| Ancient | 50% | Equilibrado |
| Dust2 | 51% | Levemente CT |
| Mirage | 52% | Levemente CT |
| Inferno | 52% | Levemente CT |
| Nuke | 53% | CT-sided |
| Overpass | 55% | Fortemente CT-sided |

**Proficiência:**
- **Domínio total** (2 mapas): +6pp na win rate por round
- **Domínio parcial** (3 mapas): neutro
- **Sem proficiência** (2 mapas restantes): -10pp na win rate por round

---

## Arquitetura

```
cs_roguelike_v9/
├── app.py                     # Servidor Flask e rotas da API REST
├── models/                    # Entidades de domínio (dataclasses)
│   ├── player.py              #   Jogador, atributos, papéis, status, score efetivo
│   ├── team.py                #   Time, sinergia, buffs, score total
│   ├── traits.py              #   10 traços de personalidade
│   ├── buff.py                #   Buffs temporários com duração por série
│   ├── campaign.py            #   Estágios (Swiss + Playoffs), histórico, StageRecord
│   ├── opponent.py            #   Times adversários (reais ou gerados), strength scaling
│   ├── event.py               #   Eventos narrativos e escolhas
│   └── map_config.py          #   Pool de mapas do CS2, CT bias por mapa, proficiência
├── systems/                   # Lógica de jogo
│   ├── team_factory.py        #   Geração de times/candidatos por era, share codes
│   ├── campaign_manager.py    #   Swiss engine, bracket, dificuldade elástica, MVP, fatiga
│   ├── match_resolver.py      #   Simulação MR12 por round, scoreboard por jogador
│   ├── veto_engine.py         #   Engine de veto BO3, perfis de mapa dos adversários
│   ├── tactics.py             #   Sistema de táticas CT/T (rock/paper/scissors)
│   └── save_system.py         #   Persistência de partidas salvas em JSON
├── events/
│   └── event_manager.py       #   Seleção e aplicação de eventos narrativos
├── data/                      # Bases de dados em JSON
│   ├── players_database.json  #   Jogadores por era (2015, 2018, 2021, 2023, 2025)
│   ├── events_performance.json#   Eventos de performance individual
│   ├── events_relations.json  #   Eventos de relacionamento e sinergia
│   └── events_other.json      #   Demais eventos narrativos
├── ui/
│   └── index.html             #   Front-end single-page (HTML/CSS/JS)
├── saves/                     # Partidas salvas (gerado em runtime)
├── update_db_from_csapi.py    # Script para atualizar era 2025 via API externa
├── requirements.txt
└── Procfile                   # Deploy Heroku/Gunicorn
```

---

## Pré-requisitos

- Python 3.10+
- pip

## Instalação

```bash
git clone <url-do-repositorio>
cd cs_roguelike_v9
pip install -r requirements.txt
```

## Executando localmente

```bash
python app.py
```

O servidor inicia em `http://localhost:5000`. Para produção:

```bash
gunicorn app:app
```

---

## Como jogar

1. **Draft** — escolha uma era e monte seu time, papel por papel. Você pode sortear um time inteiro de uma era ou escolher jogador a jogador.
2. **Proficiência de mapas** — selecione 2 mapas de domínio total e 3 de domínio parcial do pool atual (7 mapas).
3. **Veto** — antes de cada série, dispute o veto de mapas: ban/ban/pick/pick/ban/ban/decider. O adversário tem um perfil persistente de preferências.
4. **Táticas** — escolha uma tática de CT e uma de T para cada half de cada mapa. Consulte o perfil do adversário para antecipar a estratégia dele.
5. **Jogue a série** — o resultado é resolvido com simulação MR12 round a round, incluindo OT se necessário.
6. **Eventos** (se habilitados) — responda a eventos narrativos entre as séries. Suas escolhas afetam atributos, moral, sinergia e buffs.
7. **Acompanhe o bracket** — o bracket completo do Swiss e dos playoffs é revelado antes de você jogar cada round.
8. **Avance na campanha** — Stage 1 → Stage 2 → Quartas → Semi → Grande Final.

---

## API REST

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/eras` | Eras disponíveis para draft |
| POST | `/api/draft_team` | Sorteia um time real de uma era |
| POST | `/api/draft_candidates` | Lista candidatos para um papel específico |
| POST | `/api/new_game` | Inicia nova campanha (aceita `events_enabled`, `era_id`, `full_maps`, `half_maps`) |
| GET | `/api/map_pool` | Pool de mapas ativo e CT bias por mapa |
| POST | `/api/set_map_proficiency` | Define proficiência de mapas (2 full + 3 half) |
| POST | `/api/start_veto` | Inicia veto — expõe o perfil de mapa do adversário |
| POST | `/api/veto_action` | Executa ação de veto (`ban`, `pick`, `side`) |
| GET | `/api/tactics_info` | Táticas disponíveis + táticas pré-geradas do adversário por mapa/half |
| GET | `/api/state` | Estado completo (time, campanha, bracket, share code) |
| GET | `/api/get_events` | Eventos narrativos pendentes para a série |
| POST | `/api/apply_choice` | Aplica escolha de evento |
| POST | `/api/play_series` | Resolve a série (aceita `tactics` no body) |
| GET | `/api/history` | Histórico completo de séries |
| POST | `/api/save` | Salva partida atual em disco |
| GET | `/api/saves` | Lista partidas salvas |
| POST | `/api/load` | Carrega partida salva |
| POST | `/api/share_decode` | Decodifica código de compartilhamento de time |

### Iniciando uma partida com eventos

```json
POST /api/new_game
{
  "team_name": "FURIA",
  "player_picks": [...],
  "era_id": "2023",
  "events_enabled": true,
  "full_maps": ["Mirage", "Inferno"],
  "half_maps": ["Nuke", "Ancient", "Dust2"]
}
```

### Enviando táticas em `/api/play_series`

Chaves são os índices dos mapas (0, 1, 2). As táticas do adversário devem vir de `/api/tactics_info`.

```json
{
  "tactics": {
    "0": { "team_h1": "passive", "team_h2": "retake",  "enemy_h1": "fast_rush", "enemy_h2": "slow_default" },
    "1": { "team_h1": "aggressive", "team_h2": "passive", "enemy_h1": "anti_eco", "enemy_h2": "fast_rush" }
  }
}
```

### Resposta de `/api/play_series`

Inclui, além do resultado da série:
- `series_detail.maps` — scoreline de cada mapa (half1, half2, OT, lados)
- `series_detail.player_stats` — kills/deaths/assists/KD/ADR/KPR por jogador
- `series_detail.opponent_player_stats` — idem para o adversário
- `result.stage_mvp` — MVP calculado ao final de cada estágio (null durante o estágio)
- `bracket` — estado atualizado do Swiss e do bracket de playoffs

---

## Atualizando a base de jogadores

A era "2025" pode ser atualizada com dados ao vivo da [CS API](https://api.csapi.de) (gratuita, sem chave):

```bash
pip install requests
python update_db_from_csapi.py             # atualiza data/players_database.json
python update_db_from_csapi.py --dry-run   # mostra o que seria alterado, sem salvar
python update_db_from_csapi.py --debug     # inspeciona a estrutura retornada pela API
```

---

## Stack técnica

- **Back-end:** Python 3.10+, Flask, sessões server-side em memória (dict por UUID de sessão)
- **Front-end:** HTML/CSS/JS puro (single-page, sem build step)
- **Persistência:** JSON em disco (`data/`, `saves/`)
- **Deploy:** Gunicorn + Procfile (compatível com Heroku e similares)

---

## Aviso

Este é um projeto não oficial, criado por fãs, sem qualquer vínculo com a Valve, ESL ou outras organizadoras de torneios de Counter-Strike. Nomes de times e jogadores reais são usados apenas para fins de simulação e entretenimento.
