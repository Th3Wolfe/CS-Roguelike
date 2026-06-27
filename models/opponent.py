from __future__ import annotations
"""Opponent model — uses real teams from the era when available."""
from dataclasses import dataclass, field
import random

_used: List[str] = []

FALLBACK_NAMES = [
    "Outsiders","Monte","Apeks","GamerLegion","Eternal Fire",
    "ThunderTalk","Lynn Vision","TYLOO","Rare Atom","The MongolZ",
    "paiN Gaming","Imperial","9z Team","MIBR","Cloud9",
    "BIG","OG","NIP","Mouz","Fnatic",
]

def _pick_fallback_name() -> str:
    global _used
    avail = [n for n in FALLBACK_NAMES if n not in _used]
    if not avail:
        _used = []; avail = FALLBACK_NAMES[:]
    n = random.choice(avail); _used.append(n); return n


@dataclass
class Opponent:
    name:     str
    strength: float
    synergy:  float
    players:  list = field(default_factory=list)  # list of enriched player dicts (real or empty)

    def total_score(self) -> float:
        return self.strength + self.synergy * 0.3

    def to_dict(self) -> dict:
        return {
            "name":     self.name,
            "strength": self.strength,
            "synergy":  self.synergy,
            "players":  self.players,
        }

    @staticmethod
    def from_dict(data: dict) -> "Opponent":
        return Opponent(
            name=data["name"], strength=data["strength"],
            synergy=data["synergy"], players=data.get("players", []),
        )


def generate_opponent(stage: str, match_index: int,
                      era_id: Optional[str] = None,
                      used_team_names: List[str] | None = None) -> "Opponent":
    """
    Generate an opponent, preferring a real team from the era.
    Falls back to a random name + stats if no era or teams available.
    """
    ranges = {
        "stage1":         (4.8, 6.2),
        "stage2":         (5.2, 6.6),
        "playoffs_qf":    (6.2, 7.4),
        "playoffs_sf":    (6.8, 7.9),
        "playoffs_final": (7.2, 8.4),
    }
    lo, hi = ranges.get(stage, (5.2, 6.5))
    base_strength = random.uniform(lo, hi) + min(match_index * 0.10, 0.9)
    synergy = random.uniform(0.5, 3.0)

    # Try to use a real team from the era
    if era_id:
        try:
            from systems.team_factory import build_opponent_team
            team = build_opponent_team(era_id, exclude_team_names=used_team_names or [])
            if team:
                # Use team's real strength (blended with stage calibration)
                real_strength = round((team["strength"] + base_strength) / 2, 2)
                return Opponent(
                    name=team["name"],
                    strength=real_strength,
                    synergy=round(synergy, 2),
                    players=team["players"],
                )
        except Exception:
            pass

    return Opponent(
        name=_pick_fallback_name(),
        strength=round(base_strength, 2),
        synergy=round(synergy, 2),
        players=[],
    )
