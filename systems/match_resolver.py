"""Match resolution — CS2 MR12 format (first to 13, OT at 12-12 in MR3 blocks)."""
import random
import math
from dataclasses import dataclass, field
from models.team import Team
from models.opponent import Opponent

CS_MAPS = [
    "Mirage", "Inferno", "Dust2", "Overpass", "Nuke",
    "Ancient", "Anubis", "Vertigo", "Train",
]

# MR12: first to 13 rounds wins; max regulation = 24 rounds (12 per half)
ROUNDS_TO_WIN = 13
MAX_REG_ROUNDS = 24  # 12 + 12
# Overtime: MR3 blocks (3 per side = 6 rounds), first to 4 in block wins; repeats if tied
OT_ROUNDS_PER_SIDE = 3
OT_ROUNDS_WIN = 4


@dataclass
class MapResult:
    map_name:       str
    team_score:     int
    opponent_score: int
    winner:         str   # "team" | "opponent"
    went_ot:        bool = False


@dataclass
class SeriesDetail:
    maps:               list[MapResult] = field(default_factory=list)
    team_maps_won:      int   = 0
    opponent_maps_won:  int   = 0
    team_won:           bool  = False
    team_strength:      float = 0.0
    opponent_strength:  float = 0.0
    win_probability:    float = 0.5

    def to_dict(self) -> dict:
        return {
            "maps": [
                {
                    "map_name": m.map_name,
                    "team_score": m.team_score,
                    "opponent_score": m.opponent_score,
                    "winner": m.winner,
                    "went_ot": m.went_ot,
                }
                for m in self.maps
            ],
            "team_maps_won":     self.team_maps_won,
            "opponent_maps_won": self.opponent_maps_won,
            "team_won":          self.team_won,
            "team_strength":     round(self.team_strength, 2),
            "opponent_strength": round(self.opponent_strength, 2),
            "win_probability":   round(self.win_probability, 3),
        }


def score_to_win_probability(team_score: float, opp_score: float) -> float:
    diff = team_score - opp_score
    raw  = 1.0 / (1.0 + math.exp(-diff * 0.75))
    return max(0.04, min(0.96, raw))


def _simulate_map(ts: float, os_: float) -> MapResult:
    """Simulate a single CS2 map using MR12 rules.

    - Regulation: first to 13 wins (max 24 rounds)
    - Overtime at 12-12: MR3 blocks (6 rounds each), first to 4 in block wins
      If still tied, repeat OT blocks until someone wins.
    """
    # Per-map noise
    noise = random.gauss(0, 0.7)
    p = max(0.12, min(0.88, 1.0 / (1.0 + math.exp(-(ts - os_ + noise) * 0.55))))

    t_r = o_r = 0

    # ── Regulation (up to 24 rounds) ──
    while t_r < ROUNDS_TO_WIN and o_r < ROUNDS_TO_WIN:
        if random.random() < p:
            t_r += 1
        else:
            o_r += 1

    went_ot = False

    # ── Overtime (12-12) ──
    if t_r == 12 and o_r == 12:
        went_ot = True
        while True:
            ot_t = ot_o = 0
            for _ in range(OT_ROUNDS_PER_SIDE * 2):
                if random.random() < p:
                    ot_t += 1
                else:
                    ot_o += 1
            if ot_t != ot_o:  # Someone reaches 4 in block
                t_r += ot_t
                o_r += ot_o
                break
            # Still tied in this OT block — play another
            t_r += ot_t
            o_r += ot_o

    winner = "team" if t_r > o_r else "opponent"
    return MapResult(map_name="", team_score=t_r, opponent_score=o_r,
                     winner=winner, went_ot=went_ot)


def resolve_series(team: Team, opponent: Opponent) -> SeriesDetail:
    """Resolve a BO3 series with CS2 MR12 rules."""
    ts  = round(team.team_score(), 2)
    os_ = round(opponent.total_score(), 2)
    prob = score_to_win_probability(ts, os_)

    maps_pool = random.sample(CS_MAPS, 3)
    detail = SeriesDetail(team_strength=ts, opponent_strength=os_, win_probability=prob)

    for map_name in maps_pool:
        if detail.team_maps_won == 2 or detail.opponent_maps_won == 2:
            break
        result = _simulate_map(ts, os_)
        result.map_name = map_name
        detail.maps.append(result)
        if result.winner == "team":
            detail.team_maps_won += 1
        else:
            detail.opponent_maps_won += 1

    detail.team_won = detail.team_maps_won > detail.opponent_maps_won
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
