"""Opponent model – calibrated to match player team score range (~4.5–7.5)."""
from dataclasses import dataclass
import random

TEAM_NAMES = [
    "Natus Vincere","FaZe Clan","G2 Esports","Astralis","Team Vitality",
    "Team Spirit","Cloud9","Heroic","ENCE","Complexity",
    "BIG","OG","NIP","Mouz","Fnatic",
    "paiN Gaming","FURIA","Imperial","9z Team","MIBR",
    "Outsiders","Monte","Apeks","GamerLegion","Eternal Fire",
    "ThunderTalk","Lynn Vision","TYLOO","Rare Atom","The MongolZ",
]
_used: list[str] = []

def _pick_name() -> str:
    global _used
    avail = [n for n in TEAM_NAMES if n not in _used]
    if not avail: _used=[]; avail=TEAM_NAMES[:]
    n = random.choice(avail); _used.append(n); return n


@dataclass
class Opponent:
    name:     str
    strength: float
    synergy:  float

    def total_score(self) -> float:
        return self.strength + self.synergy * 0.3

    def to_dict(self) -> dict:
        return {"name":self.name,"strength":self.strength,"synergy":self.synergy}

    @staticmethod
    def from_dict(data: dict) -> "Opponent":
        return Opponent(**data)


def generate_opponent(stage: str, match_index: int) -> Opponent:
    """
    Opponent strength calibrated against team score range (median ~5.85, p75 ~6.4).
    Stage 1 should be roughly 50-65% winnable for a solid roster.
    Finals should be ~25-35% winnable.
    """
    ranges = {
        "stage1":         (4.8, 6.2),   # Below/near median — winnable but not trivial
        "stage2":         (5.2, 6.6),   # At/above median — tough
        "playoffs_qf":    (6.0, 7.1),   # Clearly above average team
        "playoffs_sf":    (6.4, 7.4),   # Top 4 caliber
        "playoffs_final": (6.8, 7.6),   # Best team in the tournament
    }
    lo, hi = ranges.get(stage, (5.2, 6.5))
    strength = random.uniform(lo, hi) + min(match_index * 0.08, 0.6)
    synergy  = random.uniform(0.5, 3.0)
    return Opponent(name=_pick_name(), strength=round(strength,2), synergy=round(synergy,2))
