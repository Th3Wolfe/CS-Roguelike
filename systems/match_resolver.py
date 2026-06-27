from __future__ import annotations
"""Match resolution — CS2 MR12 format with real side bias and map proficiency."""
import random
import math
from dataclasses import dataclass, field
from models.team import Team
from models.opponent import Opponent
from models.map_config import (
    CS2_MAP_POOL, MAP_CT_BIAS, PROF_MODIFIER, PROF_NONE,
    get_proficiency,
)

CS_MAPS = CS2_MAP_POOL  # backward-compat alias

ROUNDS_TO_WIN      = 13
OT_ROUNDS_WIN      = 4
OT_ROUNDS_PER_SIDE = 3


@dataclass
class PlayerMatchStats:
    nickname:  str
    role:      str
    kills:     int   = 0
    deaths:    int   = 0
    assists:   int   = 0
    adr_total: float = 0.0   # sum of damage over all rounds
    rounds:    int   = 0     # total rounds played in this series

    @property
    def kd(self) -> float:
        return round(self.kills / max(self.deaths, 1), 2)

    @property
    def adr(self) -> float:
        return round(self.adr_total / max(self.rounds, 1), 1)

    @property
    def kpr(self) -> float:
        return round(self.kills / max(self.rounds, 1), 2)

    def to_dict(self) -> dict:
        return {
            "nickname": self.nickname,
            "role":     self.role,
            "kills":    self.kills,
            "deaths":   self.deaths,
            "assists":  self.assists,
            "kd":       self.kd,
            "adr":      self.adr,
            "kpr":      self.kpr,
            "rounds":   self.rounds,
        }


@dataclass
class MapResult:
    map_name:        str
    team_score:      int
    opponent_score:  int
    winner:          str    # "team" | "opponent"
    went_ot:         bool   = False
    team_start_side: str    = "ct"  # team's side in first half
    team_half1:      int    = 0
    opp_half1:       int    = 0
    team_half2:      int    = 0
    opp_half2:       int    = 0
    team_ot:         int    = 0
    opp_ot:          int    = 0

    def to_dict(self) -> dict:
        return {
            "map_name":        self.map_name,
            "team_score":      self.team_score,
            "opponent_score":  self.opponent_score,
            "winner":          self.winner,
            "went_ot":         self.went_ot,
            "team_start_side": self.team_start_side,
            "team_half1":      self.team_half1,
            "opp_half1":       self.opp_half1,
            "team_half2":      self.team_half2,
            "opp_half2":       self.opp_half2,
            "team_ot":         self.team_ot,
            "opp_ot":          self.opp_ot,
        }


@dataclass
class SeriesDetail:
    maps:                   List[MapResult] = field(default_factory=list)
    team_maps_won:          int   = 0
    opponent_maps_won:      int   = 0
    team_won:               bool  = False
    team_strength:          float = 0.0
    opponent_strength:      float = 0.0
    win_probability:        float = 0.5
    player_stats:           list  = field(default_factory=list)
    opponent_player_stats:  list  = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "maps": [
                {
                    "map_name":        m.map_name,
                    "team_score":      m.team_score,
                    "opponent_score":  m.opponent_score,
                    "winner":          m.winner,
                    "went_ot":         m.went_ot,
                    "team_start_side": m.team_start_side,
                    "team_half1":      m.team_half1,
                    "opp_half1":       m.opp_half1,
                    "team_half2":      m.team_half2,
                    "opp_half2":       m.opp_half2,
                    "team_ot":         m.team_ot,
                    "opp_ot":          m.opp_ot,
                }
                for m in self.maps
            ],
            "team_maps_won":         self.team_maps_won,
            "opponent_maps_won":     self.opponent_maps_won,
            "team_won":              self.team_won,
            "team_strength":         round(self.team_strength, 2),
            "opponent_strength":     round(self.opponent_strength, 2),
            "win_probability":       round(self.win_probability, 3),
            "player_stats":          [s.to_dict() for s in self.player_stats],
            "opponent_player_stats": self.opponent_player_stats,
        }


def score_to_win_probability(team_score: float, opp_score: float) -> float:
    diff = team_score - opp_score
    raw  = 1.0 / (1.0 + math.exp(-diff * 0.75))
    return max(0.04, min(0.96, raw))


def _simulate_map(ts: float, os_: float,
                  map_name: str = "",
                  team_proficiency: str = "half",
                  team_start_side: str = "ct",
                  team_tactic_h1: str | None = None,
                  team_tactic_h2: str | None = None,
                  enemy_tactic_h1: str | None = None,
                  enemy_tactic_h2: str | None = None) -> MapResult:
    """
    Simulate a CS2 map with MR12 rules, real CT/T side bias and map proficiency.

    Half 1: team plays `team_start_side`, opponent plays the other side.
    Half 2: sides swap.
    CT bias from MAP_CT_BIAS adjusts per-round win probability each half.
    Proficiency modifier adjusts team's overall strength on this map.
    """
    from models.map_config import MAP_CT_BIAS, PROF_MODIFIER
    from systems.tactics import get_tactic_modifier
    ct_bias = MAP_CT_BIAS.get(map_name, 0.50)

    # Base win probability from team strength difference.
    # Noise scales with the strength gap so a dominant team can still drop a
    # map occasionally — fixed noise became irrelevant once gaps grew large.
    gap = abs(ts - os_)
    noise_std = 0.6 + min(gap * 0.20, 1.0)
    noise = random.gauss(0, noise_std)
    base_p = max(0.10, min(0.90, 1.0 / (1.0 + math.exp(-(ts - os_ + noise) * 0.55))))

    # Proficiency modifier shifts win probability
    prof_mod = PROF_MODIFIER.get(team_proficiency, 0.0)
    base_p = max(0.08, min(0.92, base_p + prof_mod))

    # Tactic modifiers per half
    # H1: team starts on team_start_side
    # H2: team switches to the other side
    team_side_h1 = team_start_side
    team_side_h2 = "t" if team_start_side == "ct" else "ct"

    tac_mod_h1 = 0.0
    tac_mod_h2 = 0.0

    if team_tactic_h1 and enemy_tactic_h1:
        tac_mod_h1 = get_tactic_modifier(team_side_h1, team_tactic_h1, enemy_tactic_h1)
    if team_tactic_h2 and enemy_tactic_h2:
        tac_mod_h2 = get_tactic_modifier(team_side_h2, team_tactic_h2, enemy_tactic_h2)

    def side_p(team_side: str, tac_mod: float = 0.0) -> float:
        """Win prob for team on this side, factoring map CT/T bias and tactic."""
        if team_side == "ct":
            side_adj = (ct_bias - 0.5) * 1.4
        else:
            side_adj = (0.5 - ct_bias) * 1.4
        return max(0.08, min(0.92, base_p + side_adj + tac_mod))

    def play_half(team_side: str, max_rounds: int = 12, tac_mod: float = 0.0) -> tuple[int, int]:
        """Play up to max_rounds for this half. Returns (team_rounds, opp_rounds)."""
        p = side_p(team_side, tac_mod)
        t = o = 0
        while t + o < max_rounds:
            if random.random() < p:
                t += 1
            else:
                o += 1
        return t, o

    # Half 1: play all 12 rounds
    opp_start = "t" if team_start_side == "ct" else "ct"
    h1_t, h1_o = play_half(team_start_side, tac_mod=tac_mod_h1)

    t_r = h1_t
    o_r = h1_o

    # Half 2: sides swap. Play round-by-round, stopping as soon as either
    # team reaches ROUNDS_TO_WIN (13) in total, or a 12-12 tie triggers OT.
    p_h2 = side_p(opp_start, tac_mod_h2)
    h2_t = h2_o = 0
    while h2_t + h2_o < 12:
        if t_r >= ROUNDS_TO_WIN or o_r >= ROUNDS_TO_WIN:
            break
        if random.random() < p_h2:
            t_r += 1
            h2_t += 1
        else:
            o_r += 1
            h2_o += 1
        # Check for 12-12 tie immediately after each round
        if t_r == 12 and o_r == 12:
            break

    went_ot = False
    team_ot = 0
    opp_ot  = 0
    if t_r == 12 and o_r == 12:
        went_ot = True
        ot_side = team_start_side
        while True:
            ot_t = ot_o = 0
            p1 = side_p(ot_side)
            for _ in range(OT_ROUNDS_PER_SIDE):
                if ot_t >= OT_ROUNDS_WIN or ot_o >= OT_ROUNDS_WIN:
                    break
                if random.random() < p1:
                    ot_t += 1
                else:
                    ot_o += 1
            p2 = side_p("t" if ot_side == "ct" else "ct")
            for _ in range(OT_ROUNDS_PER_SIDE):
                if ot_t >= OT_ROUNDS_WIN or ot_o >= OT_ROUNDS_WIN:
                    break
                if random.random() < p2:
                    ot_t += 1
                else:
                    ot_o += 1
            t_r     += ot_t
            o_r     += ot_o
            team_ot += ot_t
            opp_ot  += ot_o
            if t_r != o_r:
                break
            ot_side = "t" if ot_side == "ct" else "ct"

    winner = "team" if t_r > o_r else "opponent"
    return MapResult(
        map_name=map_name, team_score=t_r, opponent_score=o_r,
        winner=winner, went_ot=went_ot, team_start_side=team_start_side,
        team_half1=h1_t, opp_half1=h1_o,
        team_half2=h2_t, opp_half2=h2_o,
        team_ot=team_ot, opp_ot=opp_ot,
    )


def _simulate_player_stats(
    players: list,
    maps: List[MapResult],
) -> List[PlayerMatchStats]:
    """
    Simulate kills round by round for each map.

    Per round:
    - The winning team kills all 5 opponents (guaranteed 5 kills on that side)
    - The losing team also gets some kills before being eliminated (random 0-4)
    - Kills within each team are distributed by weighted kpr attribute
    - Deaths on a round = number of kills the opponent scored that round
    - ADR is simulated per round based on the adr attribute
    """
    stats = [PlayerMatchStats(nickname=p.nickname, role=p.role.value) for p in players]

    for m in maps:
        total_rounds = m.team_score + m.opponent_score

        # Expected total kills per team:
        # winner gets ~2.5 kills/round, loser ~1.2 kills/round
        total_team_kills  = int(round(m.team_score * 2.5 + m.opponent_score * 1.2))
        total_team_deaths = int(round(m.opponent_score * 2.5 + m.team_score * 1.2))

        # Kill share: kpr² amplifies differences between players + proportional noise
        # This means an Entry with kpr=8 gets ~4x the weight of a Support with kpr=4
        kpr_weights = [
            max(0.01, (p.attributes.kpr ** 2) * (1.0 + random.gauss(0, 0.18)))
            for p in players
        ]
        total_kw = sum(kpr_weights)
        shares   = [w / total_kw for w in kpr_weights]

        # Death share: inversely proportional to kpr (fraggier players die less per kill)
        # Also add role noise — entry fraggers die more even with high kpr
        death_weights = [
            max(0.01, (1.0 / max(p.attributes.kpr, 0.5)) * (1.0 + random.gauss(0, 0.15)))
            for p in players
        ]
        total_dw     = sum(death_weights)
        death_shares = [w / total_dw for w in death_weights]

        map_kills  = _alloc(total_team_kills,  shares)
        map_deaths = _alloc(total_team_deaths, death_shares)

        # ADR: use adr attribute scaled to realistic range, with per-map noise
        map_damage = [
            max(0.0, (40.0 + p.attributes.adr * 7.0 + random.gauss(0, 10.0))) * total_rounds
            for p in players
        ]

        for i in range(5):
            assists = max(0, int(map_kills[i] * random.uniform(0.12, 0.22)))
            stats[i].kills     += map_kills[i]
            stats[i].deaths    += map_deaths[i]
            stats[i].assists   += assists
            stats[i].adr_total += map_damage[i]
            stats[i].rounds    += total_rounds

    return stats


def _alloc(total: int, shares: List[float]) -> List[int]:
    """Distribute `total` kills among players by share, keeping the sum exact."""
    raw    = [total * s for s in shares]
    result = [int(x) for x in raw]
    remainder = total - sum(result)
    # Give leftover to players with largest fractional parts
    fracs = sorted(range(len(raw)), key=lambda i: raw[i] - result[i], reverse=True)
    for i in fracs[:remainder]:
        result[i] += 1
    return result


def _simulate_opponent_player_stats(opponent_name: str, opp_strength: float, maps: List[MapResult]) -> List[dict]:
    """
    Generate plausible round-by-round stats for 5 fictional opponent players.
    Opponent won the rounds they won (opponent_score) and lost the rest.
    """
    ROLES = ["IGL", "AWPer", "Entry Fragger", "Support", "Lurker"]
    # Opponent kpr proxy from strength (stronger = higher kpr)
    base_kprs = [max(0.05, 0.55 + opp_strength * 0.04 + random.gauss(0, 0.08)) for _ in range(5)]
    total_kpr = sum(base_kprs)
    shares = [k / total_kpr for k in base_kprs]
    death_weights = [max(0.05, 1.0 / max(k, 0.1)) for k in base_kprs]
    total_dw = sum(death_weights)
    death_shares = [w / total_dw for w in death_weights]

    all_kills  = [0] * 5
    all_deaths = [0] * 5
    all_adr    = [0.0] * 5
    all_rounds = 0

    for m in maps:
        # From the opponent's perspective: they won opp_score rounds
        opp_rounds_won = m.opponent_score
        total_rounds   = m.team_score + m.opponent_score
        all_rounds    += total_rounds

        for _ in range(total_rounds):
            opp_won = random.random() < (opp_rounds_won / max(total_rounds, 1))
            our_kills = random.choices([1,2,3,4,5], weights=[5,25,35,25,10])[0] if opp_won else random.choices([0,1,2,3,4], weights=[20,35,28,12,5])[0]
            our_deaths = random.choices([0,1,2,3,4], weights=[20,35,28,12,5])[0] if opp_won else random.choices([1,2,3,4,5], weights=[5,25,35,25,10])[0]

            rem_k = our_kills
            for i in range(4):
                k = max(0, min(rem_k, round(our_kills * shares[i] + random.gauss(0, 0.4))))
                all_kills[i] += k; rem_k -= k
            all_kills[4] += max(0, rem_k)

            rem_d = our_deaths
            for i in range(4):
                d = max(0, min(rem_d, round(our_deaths * death_shares[i] + random.gauss(0, 0.3))))
                all_deaths[i] += d; rem_d -= d
            all_deaths[4] += max(0, rem_d)

        base_adr = 40.0 + opp_strength * 7.0
        for i in range(5):
            all_adr[i] += (base_adr + random.gauss(0, 12.0)) * total_rounds

    result = []
    for i, role in enumerate(ROLES):
        kd  = round(all_kills[i] / max(all_deaths[i], 1), 2)
        adr = round(all_adr[i] / max(all_rounds, 1), 1)
        kpr_val = round(all_kills[i] / max(all_rounds, 1), 2)
        result.append({
            "nickname":  f"{opponent_name.split()[0]}#{i+1}",
            "team":      opponent_name,
            "role":      role,
            "kills":     all_kills[i],
            "deaths":    all_deaths[i],
            "assists":   max(0, int(all_kills[i] * random.uniform(0.12, 0.22))),
            "kd":        kd,
            "adr":       adr,
            "kpr":       kpr_val,
            "rounds":    all_rounds,
        })
    return result


def _simulate_opponent_stats_real(opp_players: List[dict], maps: List[MapResult]) -> List[dict]:
    """
    Simulate kill stats for real opponent players using their actual kpr/adr attributes.
    opp_players is a list of enriched dicts from team_factory.enrich_team_players().
    """
    n = len(opp_players)
    totals = [{"kills":0,"deaths":0,"assists":0,"adr_total":0.0,"rounds":0} for _ in range(n)]

    kpr_vals = [p["attributes"]["kpr"] for p in opp_players]
    adr_vals = [p["attributes"]["adr"]  for p in opp_players]

    for m in maps:
        # From opponent perspective: they won opp_score rounds
        opp_rounds_won = m.opponent_score
        total_rounds   = m.team_score + m.opponent_score

        total_opp_kills  = int(round(opp_rounds_won * 2.5 + m.team_score * 1.2))
        total_opp_deaths = int(round(m.team_score   * 2.5 + opp_rounds_won * 1.2))

        kpr_w = [max(0.01, (v ** 2) * (1.0 + random.gauss(0, 0.18))) for v in kpr_vals]
        kw_sum = sum(kpr_w)
        shares = [w / kw_sum for w in kpr_w]

        dw = [max(0.01, (1.0 / max(v, 0.5)) * (1.0 + random.gauss(0, 0.15))) for v in kpr_vals]
        dw_sum = sum(dw)
        death_shares = [w / dw_sum for w in dw]

        map_kills  = _alloc(total_opp_kills,  shares)
        map_deaths = _alloc(total_opp_deaths, death_shares)

        for i in range(n):
            adr_per_round = max(0.0, (40.0 + adr_vals[i] * 7.0 + random.gauss(0, 10.0)))
            totals[i]["kills"]     += map_kills[i]
            totals[i]["deaths"]    += map_deaths[i]
            totals[i]["assists"]   += max(0, int(map_kills[i] * random.uniform(0.12, 0.22)))
            totals[i]["adr_total"] += adr_per_round * total_rounds
            totals[i]["rounds"]    += total_rounds

    result = []
    for i, p in enumerate(opp_players):
        t = totals[i]
        kd  = round(t["kills"] / max(t["deaths"], 1), 2)
        adr = round(t["adr_total"] / max(t["rounds"], 1), 1)
        kpr = round(t["kills"] / max(t["rounds"], 1), 2)
        result.append({
            "nickname": p["nickname"],
            "team":     p.get("team", "?"),
            "role":     p.get("role", "?"),
            "kills":    t["kills"],
            "deaths":   t["deaths"],
            "assists":  t["assists"],
            "kd":       kd,
            "adr":      adr,
            "kpr":      kpr,
            "rounds":   t["rounds"],
        })
    return result


def resolve_series(team: Team, opponent: Opponent,
                   veto_maps: list | None = None,
                   tactics: dict | None = None) -> SeriesDetail:
    """
    Resolve a BO3 series with CS2 MR12 rules.

    veto_maps: list of dicts from the map veto phase, each containing:
        {"map": str, "proficiency": str, "team_side": str}
    If None (legacy / NPC-only matches), picks 3 random maps with half proficiency.
    """
    ts  = round(team.team_score(), 2)
    os_ = round(opponent.total_score(), 2)
    prob = score_to_win_probability(ts, os_)
    detail = SeriesDetail(team_strength=ts, opponent_strength=os_, win_probability=prob)

    # Build the map list to play
    if veto_maps:
        maps_to_play = veto_maps
    else:
        # Fallback: random 3 maps, neutral proficiency, random sides
        sample = random.sample(CS_MAPS, 3)
        maps_to_play = [
            {"map": m, "proficiency": "half",
             "team_side": random.choice(["ct", "t"])}
            for m in sample
        ]

    for entry in maps_to_play:
        if detail.team_maps_won == 2 or detail.opponent_maps_won == 2:
            break
        # Tactics for this map (indexed by map position)
        map_idx = len(detail.maps)
        map_tactics = (tactics or {}).get(map_idx, {})
        result = _simulate_map(
            ts, os_,
            map_name=entry["map"],
            team_proficiency=entry.get("proficiency", "half"),
            team_start_side=entry.get("team_side", "ct"),
            team_tactic_h1=map_tactics.get("team_h1"),
            team_tactic_h2=map_tactics.get("team_h2"),
            enemy_tactic_h1=map_tactics.get("enemy_h1"),
            enemy_tactic_h2=map_tactics.get("enemy_h2"),
        )
        detail.maps.append(result)
        if result.winner == "team":
            detail.team_maps_won += 1
        else:
            detail.opponent_maps_won += 1

    detail.team_won = detail.team_maps_won > detail.opponent_maps_won

    # Simulate player stats for team players
    detail.player_stats = _simulate_player_stats(team.players, detail.maps)

    # Opponent stats — use real players if available, else generate fictional ones
    if opponent.players:
        detail.opponent_player_stats = _simulate_opponent_stats_real(
            opponent.players, detail.maps
        )
    else:
        detail.opponent_player_stats = _simulate_opponent_player_stats(
            opponent.name, opponent.strength, detail.maps
        )

    return detail


def describe_result(detail: SeriesDetail, opponent_name: str) -> str:
    result  = "VITÓRIA" if detail.team_won else "DERROTA"
    ms      = f"{detail.team_maps_won}-{detail.opponent_maps_won}"
    diff    = abs(detail.team_strength - detail.opponent_strength)
    quality = ("muito disputada" if diff < 0.5 else
               "disputada"       if diff < 1.5 else
               "confortável"     if diff < 3   else "dominante")
    pct     = int(detail.win_probability * 100)
    fav     = "favorito" if detail.win_probability > 0.5 else "azarão"
    ot_maps = sum(1 for m in detail.maps if m.went_ot)
    ot_note = f" ({ot_maps} mapa(s) em OT)" if ot_maps else ""
    return (f"{result} {quality} contra {opponent_name} ({ms}){ot_note}. "
            f"Eram {fav} ({pct}% de chance).")
