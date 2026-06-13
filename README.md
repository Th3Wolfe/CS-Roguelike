# CS Major Manager — Roguelike v2

Jogo de gerenciamento roguelike ambientado num Major de Counter-Strike.

## O que há de novo na v2

### Atributos estilo HLTV
Os jogadores agora têm os mesmos 5 atributos usados pelo HLTV.org:
- **Rating** — Rating 2.0 geral (peso dobrado no cálculo de score)
- **KAST** — Kill/Assist/Survive/Trade %
- **Impact** — Rating de impacto (multi-kills, duelos de abertura)
- **ADR** — Average Damage per Round
- **KPR** — Kills per Round

### Base de jogadores real (140+ pros)
O banco de dados inclui jogadores reais do cenário mundial: s1mple, ZywOo, NiKo, ropz, dev1ce, FalleN, coldzera, KSCERATO, arT e muitos outros, com atributos baseados nas suas stats reais no HLTV.

### Draft de jogadores
Antes de cada run você escolhe os 5 jogadores do seu time num draft de 20 candidatos aleatórios do pool. Analise os atributos e traits antes de confirmar.

### Sistema de energia repensado
Agora existem **dois eixos de energia** separados:
- **Físico (0–100):** cansaço corporal, viagens, horas de jogo
- **Mental (0–100):** tilt, foco, burnout, pressão

Ambos drenam durante a campanha com taxas diferentes por situação e trait. Vitórias preservam mais o mental. Workaholics se desgastam mais fisicamente. Veteranos resistem melhor ao drain mental. Entre stages, o time descansa e recupera energia.

### Placar animado mapa a mapa
Ao jogar uma série, um overlay mostra o placar de cada mapa sendo atualizado **round a round** em tempo real, como o jogo 7-a-0. Você vê os rounds sendo contados, os pontos subindo, e o resultado de cada mapa antes do próximo começar.

## Como rodar

```bash
pip install flask
python app.py
# Acesse http://localhost:5000
```

## Estrutura

```
cs_roguelike/
├── app.py                        # Servidor Flask + API
├── models/
│   ├── player.py                 # Player com atributos HLTV
│   ├── team.py                   # Team + sinergia
│   ├── traits.py                 # 10 traits de personalidade
│   ├── buff.py                   # Sistema de buffs/debuffs
│   ├── opponent.py               # Adversários procedurais
│   └── campaign.py               # Estado da campanha
├── systems/
│   ├── campaign_manager.py       # Orquestra o fluxo do Major
│   ├── match_resolver.py         # Simula séries mapa a mapa
│   ├── team_factory.py           # Geração de times + draft
│   └── save_system.py            # Save/Load JSON
├── events/
│   └── event_manager.py          # Gerencia eventos
├── data/
│   ├── players_database.json     # 140+ pros com stats HLTV
│   ├── events_performance.json
│   ├── events_relations.json
│   └── events_other.json
└── ui/
    └── index.html                # Interface completa (SPA)
```

## Estrutura do Major

- **Stage 1:** Swiss format — 0-0, avança com 3W, elimina com 3L
- **Stage 2:** Mesmo formato
- **Playoffs:** Quartas → Semifinal → Grande Final (eliminação direta)

