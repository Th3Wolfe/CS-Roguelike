"""CS2 BO3 map veto engine.

Bo3 sequence (7 maps):
  Step 0: Team A bans
  Step 1: Team B bans
  Step 2: Team A picks   → picker's opponent chooses side
  Step 3: Team B picks   → picker's opponent chooses side
  Step 4: Team A bans
  Step 5: Team B bans
  Step 6: Decider (1 remaining) → coin flip for side

Who goes first (Team A) is determined by a coin flip stored in the state.
Player = Team A or B depending on coin flip result.
"""
from __future__ import annotations
import random
from models.map_config import (
    CS2_MAP_POOL, MAP_CT_BIAS,
    get_proficiency, PROF_FULL, PROF_HALF, PROF_NONE,
)

# Veto step definitions: (actor, action)
# actor: "player" or "opponent"
# action: "ban" or "pick"
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


class VetoState:
    def __init__(self, player_full_maps: list[str], player_half_maps: list[str],
                 opponent_name: str, opponent_strength: float):
        self.player_full_maps  = player_full_maps
        self.player_half_maps  = player_half_maps
        self.opponent_name     = opponent_name
        self.opponent_strength = opponent_strength

        # Coin flip — True means player goes first
        self.player_goes_first = random.choice([True, False])
        self.sequence = _build_sequence(self.player_goes_first)

        self.remaining_maps: list[str] = list(CS2_MAP_POOL)
        self.bans:  list[str] = []   # maps that were banned
        self.picks: list[dict] = []  # [{map, picker, team_side, opp_side}]
        self.step:  int = 0          # current step index (0..6)
        self.done:  bool = False

        # After pick, the opponent of the picker chooses side → pending side pick
        # This is tracked separately: "player_side" or "opponent_side" or None
        self.pending_side_for: str | None = None   # who must choose side next
        self.pending_pick_map: str | None = None   # the map just picked

        # Opponent's "preferred" maps (simple heuristic: strength-adjusted bias)
        self._opp_preferred = self._rank_maps_for_opponent()

    def _rank_maps_for_opponent(self) -> list[str]:
        """Rank maps by how well-suited they are for the opponent."""
        # Opponent prefers maps where CT bias is extreme (they can adapt either side)
        # and avoids maps the player is full-proficient on
        scored = []
        for m in CS2_MAP_POOL:
            bias = MAP_CT_BIAS.get(m, 0.5)
            extremeness = abs(bias - 0.5)
            player_prof_penalty = 0.3 if m in self.player_full_maps else 0.0
            scored.append((m, extremeness - player_prof_penalty + random.uniform(0, 0.1)))
        scored.sort(key=lambda x: -x[1])
        return [m for m, _ in scored]

    # ── Action methods ───────────────────────────────────────────────────────

    def current_actor(self) -> str:
        """Returns 'player', 'opponent', or 'decider'."""
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
        self.pending_side_for = "opponent"   # opponent of picker chooses side
        self.step += 1
        return {"waiting_side": True, "map": map_name, "side_chooser": "opponent"}

    def player_choose_side(self, side: str) -> dict:
        """Player chooses side for a map the opponent picked."""
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

    def opponent_choose_side(self) -> dict:
        """Opponent auto-chooses side for a map the player picked."""
        m = self.pending_pick_map
        ct_bias = MAP_CT_BIAS.get(m, 0.5)
        # Opponent picks side that favours them on this map
        opp_side = "ct" if ct_bias > 0.50 else "t"
        team_side = "t" if opp_side == "ct" else "ct"
        self.picks.append({
            "map": m, "picker": "player",
            "team_side": team_side, "opp_side": opp_side,
        })
        self.pending_side_for = None
        self.pending_pick_map = None
        return self._maybe_advance_opponent()

    def _maybe_advance_opponent(self) -> dict:
        """Auto-execute opponent steps until it's the player's turn or veto ends."""
        events = []
        while not self.done and not self.needs_side_choice():
            actor = self.current_actor()
            action = self.current_action()

            if actor == "player":
                break  # player must act

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
                    # Now player must choose side
                    self.pending_side_for = "player"
                    break

        return {"events": events, "state": self.to_dict()}

    def _opponent_ban(self) -> str:
        """Opponent bans: remove player's best full-proficiency map, or random."""
        for m in self.player_full_maps:
            if m in self.remaining_maps:
                self.bans.append(m)
                self.remaining_maps.remove(m)
                return m
        # No player full-maps left, ban random from remaining half maps or any
        for m in self.player_half_maps:
            if m in self.remaining_maps:
                self.bans.append(m)
                self.remaining_maps.remove(m)
                return m
        m = random.choice(self.remaining_maps)
        self.bans.append(m)
        self.remaining_maps.remove(m)
        return m

    def _opponent_pick(self) -> str:
        """Opponent picks: prefer maps where the player has no proficiency."""
        for m in self._opp_preferred:
            if m in self.remaining_maps and m not in self.player_full_maps:
                self.pending_pick_map = m
                self.remaining_maps.remove(m)
                return m
        m = self.remaining_maps[0]
        self.pending_pick_map = m
        self.remaining_maps.remove(m)
        return m

    def _finalize_decider(self) -> None:
        assert len(self.remaining_maps) == 1
        m = self.remaining_maps[0]
        self.remaining_maps.remove(m)
        ct_bias = MAP_CT_BIAS.get(m, 0.5)
        team_side = random.choice(["ct", "t"])
        opp_side = "t" if team_side == "ct" else "ct"
        self.picks.append({
            "map": m, "picker": "decider",
            "team_side": team_side, "opp_side": opp_side,
        })
        self.done = True

    # ── Finalize: build veto_maps for resolve_series ─────────────────────────

    def build_veto_maps(self) -> list[dict]:
        """Returns the list of maps to play, with proficiency and team side."""
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
            "sequence":          [{"actor": a, "action": b} for a,b in self.sequence],
        }

    @staticmethod
    def from_dict(d: dict, player_full: list, player_half: list,
                  opp_name: str, opp_str: float) -> "VetoState":
        v = VetoState.__new__(VetoState)
        v.player_full_maps  = player_full
        v.player_half_maps  = player_half
        v.opponent_name     = opp_name
        v.opponent_strength = opp_str
        v.player_goes_first = d["player_goes_first"]
        v.sequence = [(s["actor"], s["action"]) for s in d["sequence"]]
        v.remaining_maps    = d["remaining_maps"]
        v.bans              = d["bans"]
        v.picks             = d["picks"]
        v.step              = d["step"]
        v.done              = d["done"]
        v.pending_side_for  = d.get("pending_side_for")
        v.pending_pick_map  = d.get("pending_pick_map")
        v._opp_preferred    = v._rank_maps_for_opponent()
        return v
