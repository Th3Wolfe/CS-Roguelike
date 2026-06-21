"""CS2 BO3 map veto engine.

Bo3 sequence (7 maps):
  Step 0: Team A bans
  Step 1: Team B bans
  Step 2: Team A picks   → picker's opponent chooses side
  Step 3: Team B picks   → picker's opponent chooses side
  Step 4: Team A bans
  Step 5: Team B bans
  Step 6: Decider (1 remaining) → coin flip for side

Who goes first is determined by a coin flip stored in the state.
"""
from __future__ import annotations
import random
from models.map_config import CS2_MAP_POOL, MAP_CT_BIAS, get_proficiency


def _build_sequence(player_goes_first: bool) -> list[tuple[str, str]]:
    if player_goes_first:
        return [
            ("player",   "ban"),
            ("opponent", "ban"),
            ("player",   "pick"),
            ("opponent", "pick"),
            ("player",   "ban"),
            ("opponent", "ban"),
            ("decider",  "decider"),
        ]
    else:
        return [
            ("opponent", "ban"),
            ("player",   "ban"),
            ("opponent", "pick"),
            ("player",   "pick"),
            ("opponent", "ban"),
            ("player",   "ban"),
            ("decider",  "decider"),
        ]


def generate_opponent_map_profile(opp_name: str, opp_strength: float) -> dict:
    """
    Generate a realistic, varied map preference profile for an opponent.

    Each opponent gets:
    - `preferred`: 2-3 maps they love (will pick/protect)
    - `disliked`:  2-3 maps they hate (will ban early)
    - `side_pref`: "ct", "t", or "any" — which side they prefer to start

    The profile is seeded from the opponent's name so it's consistent
    across the same campaign (same opponent always has the same style),
    but different from every other opponent.
    """
    rng = random.Random(hash(opp_name) & 0xFFFFFFFF)
    pool = list(CS2_MAP_POOL)
    rng.shuffle(pool)

    # 2-3 preferred maps
    n_pref = rng.randint(2, 3)
    preferred = pool[:n_pref]

    # 2-3 disliked maps (non-overlapping with preferred)
    remaining = pool[n_pref:]
    rng.shuffle(remaining)
    n_dis = rng.randint(2, 3)
    disliked = remaining[:n_dis]

    # Side preference: stronger teams lean CT (higher skill → exploit CT positions)
    if opp_strength >= 6.5:
        side_pref = rng.choice(["ct", "ct", "any"])
    elif opp_strength <= 4.5:
        side_pref = rng.choice(["t", "t", "any"])
    else:
        side_pref = rng.choice(["ct", "t", "any"])

    return {
        "preferred": preferred,
        "disliked":  disliked,
        "side_pref": side_pref,
    }


class VetoState:
    def __init__(self,
                 player_full_maps: list[str],
                 player_half_maps: list[str],
                 opponent_name: str,
                 opponent_strength: float,
                 opponent_profile: dict | None = None):
        self.player_full_maps  = player_full_maps
        self.player_half_maps  = player_half_maps
        self.opponent_name     = opponent_name
        self.opponent_strength = opponent_strength

        # Opponent's own map profile (persistent, based on team identity)
        self.opp_profile = opponent_profile or generate_opponent_map_profile(
            opponent_name, opponent_strength)

        # Coin flip
        self.player_goes_first = random.choice([True, False])
        self.sequence = _build_sequence(self.player_goes_first)

        self.remaining_maps: list[str] = list(CS2_MAP_POOL)
        self.bans:  list[str] = []
        self.picks: list[dict] = []
        self.step:  int = 0
        self.done:  bool = False

        self.pending_side_for: str | None = None
        self.pending_pick_map: str | None = None

    # ── Opponent AI ──────────────────────────────────────────────────────────

    def _opponent_ban(self) -> str:
        """
        Opponent ban logic — balanced between:
        1. Removing player's best maps (anti-player)
        2. Protecting their own preferred maps (self-interest)
        3. Removing their own disliked maps (comfort)

        Each consideration has a weighted chance, with some randomness
        so the same opponent doesn't always act identically.
        """
        avail = self.remaining_maps

        # Score each map as a ban candidate
        ban_scores: dict[str, float] = {}
        for m in avail:
            score = 0.0
            # Anti-player: ban maps where player has full proficiency
            if m in self.player_full_maps:
                score += 3.0
            elif m in self.player_half_maps:
                score += 1.2

            # Self-interest: protect own preferred maps (avoid banning them)
            if m in self.opp_profile["preferred"]:
                score -= 4.0  # strongly avoid banning own favorites

            # Comfort: remove own disliked maps
            if m in self.opp_profile["disliked"]:
                score += 2.0

            # Slight noise so identical situations still vary
            score += random.gauss(0, 0.4)
            ban_scores[m] = score

        best = max(ban_scores, key=ban_scores.__getitem__)
        self.bans.append(best)
        self.remaining_maps.remove(best)
        return best

    def _opponent_pick(self) -> str:
        """
        Opponent pick logic — they want their own best maps,
        secondarily maps where player has no proficiency.
        """
        avail = self.remaining_maps

        pick_scores: dict[str, float] = {}
        for m in avail:
            score = 0.0
            # Primary: pick own preferred maps
            if m in self.opp_profile["preferred"]:
                score += 4.0
            # Secondary: avoid player's full maps
            if m in self.player_full_maps:
                score -= 2.5
            elif m in self.player_half_maps:
                score -= 0.8
            # Avoid their own disliked maps
            if m in self.opp_profile["disliked"]:
                score -= 2.0
            # Side-preference bonus: prefer maps that suit their style
            ct_bias = MAP_CT_BIAS.get(m, 0.5)
            if self.opp_profile["side_pref"] == "ct" and ct_bias > 0.51:
                score += 1.5
            elif self.opp_profile["side_pref"] == "t" and ct_bias < 0.49:
                score += 1.5

            score += random.gauss(0, 0.3)
            pick_scores[m] = score

        best = max(pick_scores, key=pick_scores.__getitem__)
        self.pending_pick_map = best
        self.remaining_maps.remove(best)
        return best

    def opponent_choose_side(self) -> dict:
        """Opponent chooses side for a map the player picked."""
        m = self.pending_pick_map
        ct_bias = MAP_CT_BIAS.get(m, 0.5)
        side_pref = self.opp_profile["side_pref"]

        if side_pref == "ct":
            # Prefers CT — take it if even mildly CT-sided or balanced
            opp_side = "ct" if ct_bias >= 0.48 else "t"
        elif side_pref == "t":
            opp_side = "t" if ct_bias <= 0.52 else "ct"
        else:
            # No preference — take whichever side is statistically better for them
            opp_side = "ct" if ct_bias > 0.50 else "t"

        team_side = "t" if opp_side == "ct" else "ct"
        self.picks.append({
            "map": m, "picker": "player",
            "team_side": team_side, "opp_side": opp_side,
        })
        self.pending_side_for = None
        self.pending_pick_map = None
        return self._maybe_advance_opponent()

    # ── Action methods ───────────────────────────────────────────────────────

    def current_actor(self) -> str:
        if self.done or self.step >= len(self.sequence):
            return "done"
        return self.sequence[self.step][0]

    def current_action(self) -> str:
        if self.done or self.step >= len(self.sequence):
            return "done"
        return self.sequence[self.step][1]

    def needs_side_choice(self) -> bool:
        return self.pending_side_for is not None

    def player_ban(self, map_name: str) -> dict:
        assert self.current_actor() == "player" and self.current_action() == "ban"
        assert map_name in self.remaining_maps
        self.bans.append(map_name)
        self.remaining_maps.remove(map_name)
        self.step += 1
        return self._maybe_advance_opponent()

    def player_pick(self, map_name: str) -> dict:
        assert self.current_actor() == "player" and self.current_action() == "pick"
        assert map_name in self.remaining_maps
        self.remaining_maps.remove(map_name)
        self.pending_pick_map = map_name
        self.pending_side_for = "opponent"
        self.step += 1
        return {"waiting_side": True, "map": map_name, "side_chooser": "opponent"}

    def player_choose_side(self, side: str) -> dict:
        assert self.pending_side_for == "player"
        assert side in ("ct", "t")
        m = self.pending_pick_map
        opp_side = "t" if side == "ct" else "ct"
        self.picks.append({
            "map": m, "picker": "opponent",
            "team_side": side, "opp_side": opp_side,
        })
        self.pending_side_for = None
        self.pending_pick_map = None
        return self._maybe_advance_opponent()

    def _maybe_advance_opponent(self) -> dict:
        events = []
        while not self.done and not self.needs_side_choice():
            actor  = self.current_actor()
            action = self.current_action()

            if actor == "player":
                break

            if actor == "decider":
                self._finalize_decider()
                break

            if actor == "opponent":
                if action == "ban":
                    m = self._opponent_ban()
                    events.append({"actor": "opponent", "action": "ban", "map": m})
                    self.step += 1
                elif action == "pick":
                    m = self._opponent_pick()
                    events.append({"actor": "opponent", "action": "pick", "map": m})
                    self.step += 1
                    self.pending_side_for = "player"
                    break

        return {"events": events, "state": self.to_dict()}

    def _finalize_decider(self) -> None:
        assert len(self.remaining_maps) == 1
        m = self.remaining_maps[0]
        self.remaining_maps.remove(m)
        team_side = random.choice(["ct", "t"])
        opp_side  = "t" if team_side == "ct" else "ct"
        self.picks.append({
            "map": m, "picker": "decider",
            "team_side": team_side, "opp_side": opp_side,
        })
        self.done = True

    # ── Finalize ─────────────────────────────────────────────────────────────

    def build_veto_maps(self) -> list[dict]:
        result = []
        for pick in self.picks:
            prof = get_proficiency(pick["map"], self.player_full_maps, self.player_half_maps)
            result.append({
                "map":         pick["map"],
                "proficiency": prof,
                "team_side":   pick["team_side"],
                "picker":      pick["picker"],
            })
        return result

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "player_goes_first": self.player_goes_first,
            "remaining_maps":    self.remaining_maps,
            "bans":              self.bans,
            "picks":             self.picks,
            "step":              self.step,
            "done":              self.done,
            "current_actor":     self.current_actor(),
            "current_action":    self.current_action(),
            "needs_side_choice": self.needs_side_choice(),
            "pending_side_for":  self.pending_side_for,
            "pending_pick_map":  self.pending_pick_map,
            "sequence":          [{"actor": a, "action": b} for a, b in self.sequence],
            "opp_profile":       self.opp_profile,
        }

    @staticmethod
    def from_dict(d: dict, player_full: list, player_half: list,
                  opp_name: str, opp_str: float) -> "VetoState":
        v = VetoState.__new__(VetoState)
        v.player_full_maps  = player_full
        v.player_half_maps  = player_half
        v.opponent_name     = opp_name
        v.opponent_strength = opp_str
        v.opp_profile       = d.get("opp_profile") or generate_opponent_map_profile(opp_name, opp_str)
        v.player_goes_first = d["player_goes_first"]
        v.sequence          = [(s["actor"], s["action"]) for s in d["sequence"]]
        v.remaining_maps    = d["remaining_maps"]
        v.bans              = d["bans"]
        v.picks             = d["picks"]
        v.step              = d["step"]
        v.done              = d["done"]
        v.pending_side_for  = d.get("pending_side_for")
        v.pending_pick_map  = d.get("pending_pick_map")
        return v
