"""
Tactics system — rock/paper/scissors style for CT and T sides.

CT Tactics:
  - "aggressive":  Aggressive CT (counters passive T, loses to fast rush)
  - "passive":     Default Hold CT (counters fast rush, loses to slow default)
  - "retake":      Retake-based CT (counters slow default, loses to aggressive T)

T Tactics:
  - "fast_rush":   Fast Rush / Execute (counters aggressive CT, loses to passive/default hold)
  - "slow_default": Slow Default / Mid control (counters retake CT, loses to fast rush)
  - "anti_eco":    Anti-eco / Aggressive push (counters passive CT, loses to retake CT)

Matchup table: outcome modifier for the T side
(winner of the matchup gets +0.08, loser gets -0.08 to their base win prob)
"""
import random

CT_TACTICS = {
    "aggressive": {
        "label": "🔫 Agressivo",
        "desc":  "Pushes e peeks agressivos. Bom contra rushs lentos, ruim contra executes rápidos.",
    },
    "passive": {
        "label": "🛡️ Passivo / Hold",
        "desc":  "Hold padrão nas posições. Bom contra rushes rápidos, ruim contra defaults lentos.",
    },
    "retake": {
        "label": "🔄 Retake",
        "desc":  "Joga para retake e informação. Bom contra defaults lentos, ruim contra agressividade T.",
    },
}

T_TACTICS = {
    "fast_rush": {
        "label": "⚡ Fast Rush / Execute",
        "desc":  "Execute rápido num bombsite. Bom contra CT agressivo, ruim contra hold passivo.",
    },
    "slow_default": {
        "label": "🐢 Slow Default",
        "desc":  "Default lento com controle de mid. Bom contra retake CT, ruim contra rushes.",
    },
    "anti_eco": {
        "label": "💰 Anti-eco / Push",
        "desc":  "Push agressivo forçando eco inimigo. Bom contra hold passivo, ruim contra retake.",
    },
}

# Matchup modifiers: (ct_tactic, t_tactic) -> modifier for TEAM (positive = team advantage)
# If team is CT: positive = CT wins
# If team is T: positive = T wins  (apply inverted)
# Matrix: CT perspective (team playing CT)
CT_MATCHUP_MOD = {
    # (ct_tactic, t_tactic): mod for CT
    ("aggressive", "fast_rush"):   -0.07,  # Fast rush beats aggressive CT
    ("aggressive", "slow_default"):+0.07,  # Aggressive CT beats slow default
    ("aggressive", "anti_eco"):    +0.03,  # Even-ish, slight CT advantage
    ("passive",    "fast_rush"):   +0.08,  # Passive hold beats fast rush
    ("passive",    "slow_default"):-0.07,  # Slow default beats passive
    ("passive",    "anti_eco"):    -0.05,  # Anti-eco beats passive
    ("retake",     "fast_rush"):   -0.04,  # Fast rush ok vs retake
    ("retake",     "slow_default"):+0.08,  # Retake beats slow default
    ("retake",     "anti_eco"):    +0.06,  # Retake beats anti-eco push
}


def get_tactic_modifier(team_side: str, team_tactic: str, enemy_tactic: str) -> float:
    """
    Returns a win probability modifier for the team based on tactic matchup.
    team_side: 'ct' or 't'
    team_tactic: key from CT_TACTICS or T_TACTICS depending on side
    enemy_tactic: key from the opposite side's tactics
    """
    if team_side == "ct":
        ct_tac = team_tactic
        t_tac  = enemy_tactic
    else:
        ct_tac = enemy_tactic
        t_tac  = team_tactic

    mod = CT_MATCHUP_MOD.get((ct_tac, t_tac), 0.0)

    if team_side == "t":
        mod = -mod  # invert: CT advantage becomes T disadvantage

    return mod


# ── AI tactic selection ────────────────────────────────────────────────────────
# Stage 1 (qualifier): nearly random, slight bias toward non-worst
# Stage 2: some pattern recognition
# Playoffs: smarter adaptation

def enemy_choose_tactic(side: str, stage: str, player_tactic: str | None = None,
                         prev_half_result: str | None = None) -> str:
    """
    AI chooses a tactic for the enemy team.
    side: 'ct' or 't'
    stage: 'stage1' | 'stage2' | 'playoffs_qf' | 'playoffs_sf' | 'playoffs_final'
    player_tactic: what the player used last half (None if unknown)
    prev_half_result: 'win' | 'loss' | None
    """
    options = list(CT_TACTICS.keys()) if side == "ct" else list(T_TACTICS.keys())

    if stage == "stage1":
        # Mostly random — early stages, enemies are not smart
        return random.choice(options)

    if stage == "stage2":
        # Some basic adaptation: if enemy lost last half, avoid same tactic
        if prev_half_result == "loss" and player_tactic:
            # Try to counter the player's tactic with 60% chance
            if random.random() < 0.6:
                counter = _counter_tactic(side, player_tactic)
                if counter:
                    return counter
        return random.choice(options)

    # Playoffs: smarter
    if player_tactic and prev_half_result == "loss":
        # 80% chance to counter
        if random.random() < 0.80:
            counter = _counter_tactic(side, player_tactic)
            if counter:
                return counter

    if player_tactic:
        # 60% chance to counter even if not losing
        if random.random() < 0.60:
            counter = _counter_tactic(side, player_tactic)
            if counter:
                return counter

    return random.choice(options)


def _counter_tactic(enemy_side: str, player_tactic: str) -> str | None:
    """
    Find the tactic that counters the player's tactic.
    enemy_side is the side the ENEMY is playing.
    player_tactic is what the player is using (opposite side).
    """
    if enemy_side == "ct":
        # Player is T, enemy is CT — counter player's T tactic
        counters = {
            "fast_rush":   "passive",
            "slow_default":"retake",
            "anti_eco":    "aggressive",
        }
    else:
        # Player is CT, enemy is T — counter player's CT tactic
        counters = {
            "aggressive":  "fast_rush",
            "passive":     "anti_eco",
            "retake":      "slow_default",
        }
    return counters.get(player_tactic)


ENEMY_PAUSE_LINES = [
    "O adversário pediu pause técnico. 'Our strats are leaked bro'",
    "Pause do inimigo. 'Who called that rush?! No me maten!'",
    "Timeout tático do adversário. Provavelmente discutindo bombsite padrão.",
    "Adversário pausou. Suspeita-se de tilted IGL.",
    "Pause do outro time. 'We need to talk about your crosshair placement'",
    "Time adversário parou. 'ESEA match em 5 minutos, gente'",
    "Pause técnico do inimigo. 'Who's lurking mid?! Everyone stop!'",
    "O adversário pediu tempo. Clássico 'just one more round' sendo discutido.",
    "Pause inimigo. 'ok ok ok, new strat: everyone B. Wait, no, A. Wait...'",
    "Timeout do adversário. 'Have you tried turning your sens down?'",
]
