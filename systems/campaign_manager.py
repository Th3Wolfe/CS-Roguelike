from __future__ import annotations
"""Campaign manager — Major bracket simulation."""
import random
from typing import Optional, List
from models.campaign import CampaignState, CampaignStage, HistoryEntry
from models.team import Team
from models.opponent import Opponent, generate_opponent
from systems.match_resolver import resolve_series, describe_result, SeriesDetail


def _compute_rating(stats: dict) -> float:
    kd  = stats["kills"] / max(stats["deaths"], 1)
    kpr = stats["kills"] / max(stats["rounds"], 1)
    adr = stats["adr_total"] / max(stats["rounds"], 1)
    return round(kd/1.0*0.4 + kpr/0.68*0.35 + adr/80.0*0.25, 3)


def _sim_bo3(str_a: float, str_b: float) -> bool:
    """True if team A wins the BO3 series."""
    import math
    p = max(0.1, min(0.9, 1.0 / (1.0 + math.exp(-(str_a - str_b) * 0.8))))
    a = b = 0
    while a < 2 and b < 2:
        if random.random() < p: a += 1
        else: b += 1
    return a > b


# ── NPC team ─────────────────────────────────────────────────────────────────

class NpcTeam:
    def __init__(self, name: str, strength: float):
        self.name     = name
        self.strength = strength
        # Swiss S1
        self.s1_wins = 0; self.s1_losses = 0; self.s1_done = False
        self.s1_history: list = []   # [{wins_before, losses_before, opponent, result}]
        self.advanced_s1 = False
        # Swiss S2
        self.s2_wins = 0; self.s2_losses = 0; self.s2_done = False
        self.s2_history: list = []
        self.advanced_s2 = False

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in (
            "name","strength",
            "s1_wins","s1_losses","s1_done","s1_history","advanced_s1",
            "s2_wins","s2_losses","s2_done","s2_history","advanced_s2",
        )}

    @staticmethod
    def from_dict(d: dict) -> "NpcTeam":
        t = NpcTeam(d["name"], d["strength"])
        for k in ("s1_wins","s1_losses","s1_done","s1_history","advanced_s1",
                  "s2_wins","s2_losses","s2_done","s2_history","advanced_s2"):
            if k in d: setattr(t, k, d[k])
        return t


def _pair_round_matchups(npc_teams: list, stage: str, player_name: str,
                         player_wins: int, player_losses: int) -> list:
    """
    Build the pairing for the NEXT round (matchups only, no results yet).
    Pairs teams within the same record bucket — same logic as _run_swiss_round's
    grouping step, but stops short of simulating a winner.
    Returns a list of {a, b} pairs covering every team still active in this stage,
    including the player. Used so the bracket can reveal "who plays who" before
    results are simulated.
    """
    if stage == "stage1":
        get_wl  = lambda t: (t.s1_wins, t.s1_losses)
        is_done = lambda t: t.s1_done
    else:
        get_wl  = lambda t: (t.s2_wins, t.s2_losses) if t.advanced_s1 else (None, None)
        is_done = lambda t: t.s2_done

    if stage == "stage1":
        active = [t for t in npc_teams if not is_done(t)]
    else:
        active = [t for t in npc_teams if t.advanced_s1 and not is_done(t)]

    # Build a uniform list of "entrants" (name, record, strength), including the player
    entrants = [{"name": player_name, "record": (player_wins, player_losses), "strength": None}]
    for t in active:
        entrants.append({"name": t.name, "record": get_wl(t), "strength": t.strength})

    buckets: dict = {}
    for e in entrants:
        buckets.setdefault(e["record"], []).append(e)

    pairs = []
    for record, group in buckets.items():
        random.shuffle(group)
        i = 0
        while i + 1 < len(group):
            pairs.append({"a": group[i]["name"], "b": group[i+1]["name"], "record": record})
            i += 2
        # odd one out (bye) is simply left unpaired this round — handled by bye logic elsewhere

    return pairs


# ── Swiss engine ──────────────────────────────────────────────────────────────

def _run_swiss_round(npc_teams: list, stage: str, pairings: list, player_name: str):
    """
    Resolve one Swiss round for all NPCs using the ALREADY-REVEALED pairings
    (the same list shown to the player before they played their match).
    This guarantees the bracket UI's "who plays who" preview matches exactly
    what gets simulated — no re-shuffling happens here.

    `pairings`: list of {"a": name, "b": name, "record": (w,l)} covering every
    team (including the player, whose match was already resolved separately
    by play_series — we simply skip that pair here).
    """
    if stage == "stage1":
        is_done = lambda t: t.s1_done
        def record(t, won):
            if won: t.s1_wins += 1
            else:   t.s1_losses += 1
            if t.s1_wins >= 3 or t.s1_losses >= 3:
                t.s1_done = True; t.advanced_s1 = t.s1_wins >= 3
        def hist(t, w, l, opp, res):
            t.s1_history.append({"wins_before": w, "losses_before": l,
                                  "opponent": opp, "result": res})
    else:
        is_done = lambda t: t.s2_done
        def record(t, won):
            if won: t.s2_wins += 1
            else:   t.s2_losses += 1
            if t.s2_wins >= 3 or t.s2_losses >= 3:
                t.s2_done = True; t.advanced_s2 = t.s2_wins >= 3
        def hist(t, w, l, opp, res):
            t.s2_history.append({"wins_before": w, "losses_before": l,
                                  "opponent": opp, "result": res})

    by_name = {t.name: t for t in npc_teams}

    for pair in pairings:
        a_name, b_name = pair["a"], pair["b"]
        if a_name == player_name or b_name == player_name:
            continue  # player's match already resolved in play_series

        a, b = by_name.get(a_name), by_name.get(b_name)
        if not a or not b or is_done(a) or is_done(b):
            continue

        w, l = pair["record"]
        a_wins = _sim_bo3(a.strength, b.strength)
        winner, loser = (a, b) if a_wins else (b, a)
        record(winner, True);  hist(winner, w, l, loser.name, "win")
        record(loser,  False); hist(loser,  w, l, winner.name, "loss")



def _finish_swiss(npc_teams: list, stage: str) -> None:
    """
    Run rounds until all NPC teams in this stage are done.
    Uses same-record pairing when possible; falls back to cross-record
    pairing (adjacent ranks) when buckets are all singletons.
    """
    if stage == "stage1":
        get_wl  = lambda t: (t.s1_wins, t.s1_losses)
        is_done = lambda t: t.s1_done
        def record(t, won):
            if won: t.s1_wins += 1
            else:   t.s1_losses += 1
            if t.s1_wins >= 3 or t.s1_losses >= 3:
                t.s1_done = True; t.advanced_s1 = t.s1_wins >= 3
        def hist(t, w, l, opp, res):
            t.s1_history.append({"wins_before": w, "losses_before": l,
                                  "opponent": opp, "result": res})
    else:
        get_wl  = lambda t: (t.s2_wins, t.s2_losses)
        is_done = lambda t: t.s2_done
        def record(t, won):
            if won: t.s2_wins += 1
            else:   t.s2_losses += 1
            if t.s2_wins >= 3 or t.s2_losses >= 3:
                t.s2_done = True; t.advanced_s2 = t.s2_wins >= 3
        def hist(t, w, l, opp, res):
            t.s2_history.append({"wins_before": w, "losses_before": l,
                                  "opponent": opp, "result": res})

    for _ in range(20):  # safety limit
        if stage == "stage1":
            active = [t for t in npc_teams if not t.s1_done]
        else:
            active = [t for t in npc_teams if t.advanced_s1 and not t.s2_done]
        if not active:
            break
        if len(active) == 1:
            # Single team left — give them a bye win to finish (edge case)
            t = active[0]
            w, l = get_wl(t)
            record(t, True); hist(t, w, l, "BYE", "win")
            break

        # Group by record
        buckets: dict[tuple, list] = {}
        for t in active:
            key = get_wl(t)
            buckets.setdefault(key, []).append(t)

        # Try same-record pairing first
        paired_any = False
        unpaired: list = []
        for key in sorted(buckets.keys()):
            group = list(buckets[key])
            random.shuffle(group)
            i = 0
            while i + 1 < len(group):
                a, b = group[i], group[i+1]
                w, l = key
                a_wins = _sim_bo3(a.strength, b.strength)
                winner, loser = (a, b) if a_wins else (b, a)
                record(winner, True);  hist(winner, w, l, loser.name, "win")
                record(loser, False);  hist(loser,  w, l, winner.name, "loss")
                i += 2
                paired_any = True
            if len(group) % 2 == 1:
                unpaired.append(group[-1])

        # Cross-pair any leftover singletons (sorted by wins desc, losses asc)
        unpaired.sort(key=lambda t: (-get_wl(t)[0], get_wl(t)[1]))
        i = 0
        while i + 1 < len(unpaired):
            a, b = unpaired[i], unpaired[i+1]
            wa, la = get_wl(a); wb, lb = get_wl(b)
            a_wins = _sim_bo3(a.strength, b.strength)
            winner, loser = (a, b) if a_wins else (b, a)
            ww, wl = get_wl(winner); lw, ll = get_wl(loser)
            record(winner, True);  hist(winner, ww, wl, loser.name, "win")
            record(loser, False);  hist(loser,  lw, ll, winner.name, "loss")
            i += 2
            paired_any = True
        if len(unpaired) % 2 == 1:
            # True odd-one-out: bye win
            t = unpaired[-1]
            w, l = get_wl(t)
            record(t, True); hist(t, w, l, "BYE", "win")

        if not paired_any:
            break  # nothing could be paired, exit


def _enforce_swiss_capacity(npc_teams: list, stage: str, player_advanced: bool) -> None:
    """
    Guarantee the correct number of NPC qualifiers given that the player
    occupies one of the 8 advancement slots (Swiss math: exactly half of
    16 entrants reach 3 wins). If player_advanced, NPCs should produce
    exactly 7 advanced; otherwise exactly 8. Any mismatch (from edge cases
    in bye/cross-pairing) is corrected deterministically by re-ranking on
    wins (desc), losses (asc), then strength (desc) — mirroring real Swiss
    tiebreakers (match wins, then round/map differential).
    """
    target_adv = 7 if player_advanced else 8

    if stage == "stage1":
        all_teams = npc_teams
        get_w   = lambda t: t.s1_wins
        get_l   = lambda t: t.s1_losses
        get_adv = lambda t: t.advanced_s1
        set_adv = lambda t, v: setattr(t, "advanced_s1", v)
        set_done= lambda t, v: setattr(t, "s1_done", v)
    else:
        all_teams = [t for t in npc_teams if t.advanced_s1]
        get_w   = lambda t: t.s2_wins
        get_l   = lambda t: t.s2_losses
        get_adv = lambda t: t.advanced_s2
        set_adv = lambda t, v: setattr(t, "advanced_s2", v)
        set_done= lambda t, v: setattr(t, "s2_done", v)

    current_adv = [t for t in all_teams if get_adv(t)]
    if len(current_adv) == target_adv:
        return  # already correct

    # Rank ALL teams by (wins desc, losses asc, strength desc) — best record first
    ranked = sorted(all_teams, key=lambda t: (-get_w(t), get_l(t), -t.strength))

    if len(current_adv) > target_adv:
        # Too many advanced — demote the weakest advanced teams
        keep = set(id(t) for t in ranked[:target_adv])
        for t in current_adv:
            if id(t) not in keep:
                set_adv(t, False)
                set_done(t, True)
    else:
        # Too few advanced — promote the strongest non-advanced teams
        need = target_adv - len(current_adv)
        candidates = [t for t in ranked if not get_adv(t)]
        for t in candidates[:need]:
            set_adv(t, True)
            set_done(t, True)


# ── Playoff bracket ───────────────────────────────────────────────────────────

def _build_playoffs(qualifiers: list) -> dict:
    """
    Build a full 8-team single-elim bracket.
    qualifiers: list of {name, strength, is_player} sorted seed 1..8.

    Only QF matches are fully set here. SF and Final are left empty —
    they get filled in by _cascade_bracket as QF results come in.
    Player matches get winner=None so the real game can resolve them.
    """
    # Seed matchups: 1v8, 2v7, 3v6, 4v5
    seeds = [(0,7),(1,6),(2,5),(3,4)]
    bracket = {"qf": [], "sf": [], "final": None, "champion": None}

    qf_winners = []  # provisional QF winners (for building SF skeleton)
    for (ai, bi) in seeds:
        a, b = qualifiers[ai], qualifiers[bi]
        if a["is_player"] or b["is_player"]:
            bracket["qf"].append({
                "a": a["name"], "b": b["name"],
                "winner": None, "loser": None, "is_player_match": True,
                "a_str": a["strength"], "b_str": b["strength"]
            })
            # QF winner unknown until player plays — cascade will fill this in
            qf_winners.append(None)
        else:
            won = _sim_bo3(a["strength"], b["strength"])
            w, l = (a, b) if won else (b, a)
            bracket["qf"].append({
                "a": a["name"], "b": b["name"],
                "winner": w["name"], "loser": l["name"], "is_player_match": False,
                "a_str": a["strength"], "b_str": b["strength"]
            })
            qf_winners.append({"name": w["name"], "strength": w["strength"], "is_player": False})

    # Build SF skeleton: pair QF1w vs QF2w, QF3w vs QF4w
    # Only simulate a SF match if BOTH QF winners are already known NPC teams
    for i in range(0, 4, 2):
        wa, wb = qf_winners[i], qf_winners[i+1]
        if wa is not None and wb is not None:
            # Both QFs resolved (both NPC matches) — simulate immediately
            won = _sim_bo3(wa["strength"], wb["strength"])
            w, l = (wa, wb) if won else (wb, wa)
            bracket["sf"].append({
                "a": wa["name"], "b": wb["name"],
                "winner": w["name"], "loser": l["name"], "is_player_match": False,
                "a_str": wa["strength"], "b_str": wb["strength"]
            })
        else:
            # At least one QF involves the player — this SF is a player match (TBD)
            bracket["sf"].append({
                "a": wa["name"] if wa else "?", "b": wb["name"] if wb else "?",
                "winner": None, "loser": None, "is_player_match": True,
                "a_str": wa["strength"] if wa else 5.0,
                "b_str": wb["strength"] if wb else 5.0
            })

    # Cascade to build Final if both SFs are already resolved
    _cascade_bracket(bracket, "")
    return bracket


def _resolve_player_slot(bracket: dict, stage_key: str,
                         player_name: str, player_won: bool, opp_name: str) -> None:
    """Fill in the player's result in the bracket and cascade downstream."""
    key_map = {"playoffs_qf": "qf", "playoffs_sf": "sf", "playoffs_final": "final"}
    key = key_map.get(stage_key)
    if not key:
        return

    target = bracket.get(key)
    if target is None:
        return
    matches = [target] if isinstance(target, dict) else target

    player_match = next((m for m in matches if m.get("is_player_match")), None)
    if not player_match:
        return

    winner = player_name if player_won else opp_name
    loser  = opp_name   if player_won else player_name
    player_match["winner"] = winner
    player_match["loser"]  = loser
    player_match["is_player_match"] = False

    if key == "final":
        if player_won:
            bracket["champion"] = player_name
        return

    _cascade_bracket(bracket, player_name)


def _cascade_bracket(bracket: dict, player_name: str = "") -> None:
    """
    After any QF result changes, recompute what we can in SF and Final.
    Key rule: NEVER auto-simulate a match that the player will play
    (is_player_match=True). Only fill NPC-vs-NPC matches where both
    participants are confirmed NPC winners.
    """
    qf = bracket.get("qf", [])

    # Determine each QF winner (None if unresolved / player match pending)
    qf_winners = []
    for m in qf:
        if m.get("winner"):
            qf_winners.append({"name": m["winner"],
                                "strength": m["a_str"] if m["a"] == m["winner"] else m["b_str"],
                                "is_player": False})
        else:
            qf_winners.append(None)  # unresolved (player match or not yet played)

    # Rebuild SF
    new_sf = list(bracket.get("sf", []))
    while len(new_sf) < 2:
        new_sf.append({"a": "?", "b": "?", "winner": None, "loser": None,
                        "is_player_match": False, "a_str": 5.0, "b_str": 5.0})

    sf_winners = [None, None]

    for sf_idx, (qi_a, qi_b) in enumerate([(0, 1), (2, 3)]):
        wa = qf_winners[qi_a]
        wb = qf_winners[qi_b]
        existing = new_sf[sf_idx]

        # If SF already has a resolved, non-player result → keep it
        if existing.get("winner") and not existing.get("is_player_match"):
            sf_winners[sf_idx] = {
                "name": existing["winner"],
                "strength": existing["a_str"] if existing["a"] == existing["winner"] else existing["b_str"]
            }
            continue

        # If this SF is the player's match → keep is_player_match, update names if known
        if existing.get("is_player_match"):
            update = {}
            if wa: update["a"] = wa["name"]; update["a_str"] = wa["strength"]
            if wb: update["b"] = wb["name"]; update["b_str"] = wb["strength"]
            new_sf[sf_idx] = {**existing, **update}
            sf_winners[sf_idx] = None  # unknown until player plays
            continue

        # Both QFs resolved AND neither involves the player → simulate SF now
        if wa is not None and wb is not None:
            won = _sim_bo3(wa["strength"], wb["strength"])
            w, l = (wa, wb) if won else (wb, wa)
            new_sf[sf_idx] = {
                "a": wa["name"], "b": wb["name"],
                "winner": w["name"], "loser": l["name"], "is_player_match": False,
                "a_str": wa["strength"], "b_str": wb["strength"]
            }
            sf_winners[sf_idx] = {"name": w["name"], "strength": w["strength"]}
        else:
            # One or both QFs not yet resolved — SF stays unknown
            new_sf[sf_idx] = {
                **existing,
                "a": wa["name"] if wa else existing.get("a", "?"),
                "b": wb["name"] if wb else existing.get("b", "?"),
            }
            sf_winners[sf_idx] = None

    bracket["sf"] = new_sf

    # ── Rebuild Final ──────────────────────────────────────────────────────
    fw0, fw1 = sf_winners[0], sf_winners[1]
    existing_f = bracket.get("final") or {}

    # If Final already has a resolved non-player result → keep it
    if existing_f.get("winner") and not existing_f.get("is_player_match"):
        return

    # Either SF still pending
    if fw0 is None or fw1 is None:
        sf_data = bracket.get("sf", [{}, {}])
        pending_is_player = any(
            m.get("is_player_match") and not m.get("winner")
            for m in sf_data
        )
        bracket["final"] = {
            **existing_f,
            "a": fw0["name"] if fw0 else existing_f.get("a", "?"),
            "b": fw1["name"] if fw1 else existing_f.get("b", "?"),
            "a_str": fw0["strength"] if fw0 else existing_f.get("a_str", 5.0),
            "b_str": fw1["strength"] if fw1 else existing_f.get("b_str", 5.0),
            "is_player_match": pending_is_player or existing_f.get("is_player_match", False),
        }
        return

    # Both SF winners known — check if the player is one of them
    player_in_final = bool(player_name) and (fw0["name"] == player_name or fw1["name"] == player_name)

    if existing_f.get("is_player_match") or player_in_final:
        bracket["final"] = {
            **existing_f,
            "a": fw0["name"], "b": fw1["name"],
            "a_str": fw0["strength"], "b_str": fw1["strength"],
            "winner": existing_f.get("winner"),
            "loser":  existing_f.get("loser"),
            "is_player_match": not bool(existing_f.get("winner")),
        }
        return

    # Pure NPC Final — simulate
    won = _sim_bo3(fw0["strength"], fw1["strength"])
    w, l = (fw0, fw1) if won else (fw1, fw0)
    bracket["final"] = {
        "a": fw0["name"], "b": fw1["name"],
        "winner": w["name"], "loser": l["name"], "is_player_match": False,
        "a_str": fw0["strength"], "b_str": fw1["strength"]
    }
    bracket["champion"] = w["name"]


# ── CampaignManager ───────────────────────────────────────────────────────────

class CampaignManager:
    def __init__(self, team: Team, events_enabled: bool = False,
                 era_id: Optional[str] = None) -> None:
        self.team             = team
        self.state            = CampaignState()
        self.events_enabled   = events_enabled
        self._used_event_ids: List[str] = []
        self._stage_stats: dict = {}
        self.era_id           = era_id
        self._used_team_names: List[str] = [team.name]
        self.npc_teams: List[NpcTeam]    = []
        self._npc_team_data: dict        = {}  # name -> enriched team dict (players, country)
        self._bracket_initialized        = False
        self.playoff_bracket: dict       = {}
        self.pending_pairings: list      = []  # current round's matchups (revealed before results)

        from events.event_manager import EventManager
        self.event_manager = EventManager()

    # ── initialisation ───────────────────────────────────────────────────────

    def _init_bracket(self) -> None:
        if self._bracket_initialized:
            return
        self._bracket_initialized = True

        used = set(self._used_team_names)

        if self.era_id:
            from systems.team_factory import get_teams_for_era, enrich_team_players
            all_era = get_teams_for_era(self.era_id)
            for t in all_era:
                if t["name"] in used or len(self.npc_teams) >= 15:
                    continue
                enriched = enrich_team_players(t)
                avg_rtg  = sum(p["attributes"]["rating"] for p in enriched) / max(len(enriched), 1)
                strength = round(avg_rtg * 0.65 + random.uniform(-0.2, 0.2), 2)
                self.npc_teams.append(NpcTeam(t["name"], strength))
                self._npc_team_data[t["name"]] = {"players": enriched, "country": t.get("country", "?")}
                used.add(t["name"])

        from models.opponent import FALLBACK_NAMES
        pool = [n for n in FALLBACK_NAMES if n not in used]
        random.shuffle(pool)
        while len(self.npc_teams) < 15 and pool:
            name = pool.pop()
            self.npc_teams.append(NpcTeam(name, round(random.uniform(4.8, 6.2), 2)))
            self._npc_team_data[name] = {"players": [], "country": "?"}

        # Reveal Round 1 pairings immediately (everyone starts at 0-0)
        self._refresh_pending_pairings()

    def _refresh_pending_pairings(self) -> None:
        """Recompute the matchups for the CURRENT round so the bracket can show
        'who plays who' before any result is simulated."""
        stage = self.state.stage.value
        if stage == "stage1":
            pw, pl = self.state.stage1.wins, self.state.stage1.losses
        elif stage == "stage2":
            pw, pl = self.state.stage2.wins, self.state.stage2.losses
        else:
            self.pending_pairings = []
            return
        self.pending_pairings = _pair_round_matchups(
            self.npc_teams, stage, self.team.name, pw, pl)

    def _get_paired_opponent(self, stage: str) -> "Opponent":
        """Swiss stages: use the pre-revealed pending pairing."""
        pairing = next(
            (p for p in self.pending_pairings
             if p["a"] == self.team.name or p["b"] == self.team.name),
            None
        )
        opp_name = None
        if pairing:
            opp_name = pairing["b"] if pairing["a"] == self.team.name else pairing["a"]

        if opp_name:
            npc = next((t for t in self.npc_teams if t.name == opp_name), None)
            if npc:
                data = self._npc_team_data.get(opp_name, {})
                return Opponent(
                    name=npc.name,
                    strength=npc.strength,
                    synergy=round(random.uniform(0.5, 3.0), 2),
                    players=data.get("players", []),
                )

        return generate_opponent(
            stage, self.state.total_series,
            era_id=self.era_id, used_team_names=self._used_team_names)

    def _get_playoff_opponent(self, stage: str) -> "Opponent":
        """Playoffs: read opponent from the bracket's is_player_match slot."""
        key_map = {"playoffs_qf": "qf", "playoffs_sf": "sf", "playoffs_final": "final"}
        key = key_map.get(stage)
        pb = self.playoff_bracket
        opp_name = None
        if key:
            target = pb.get(key)
            matches = [target] if isinstance(target, dict) else (target or [])
            pm = next((m for m in matches if m.get("is_player_match")), None)
            if pm:
                opp_name = pm["b"] if pm["a"] == self.team.name else pm["a"]

        if opp_name and opp_name not in ("?", ""):
            npc = next((t for t in self.npc_teams if t.name == opp_name), None)
            if npc:
                data = self._npc_team_data.get(opp_name, {})
                return Opponent(
                    name=npc.name, strength=npc.strength,
                    synergy=round(random.uniform(0.5, 3.0), 2),
                    players=data.get("players", []),
                )
            return Opponent(name=opp_name, strength=6.0,
                            synergy=round(random.uniform(0.5, 2.0), 2), players=[])

        return generate_opponent(
            stage, self.state.total_series,
            era_id=self.era_id, used_team_names=self._used_team_names)

    # ── events ───────────────────────────────────────────────────────────────

    def get_pending_events(self) -> list:
        evs = self.event_manager.select_events_for_series(
            self.state.stage.value, self._used_event_ids)
        for e in evs:
            self._used_event_ids.append(e.id)
        return evs

    def apply_event_choice(self, event, choice_index: int):
        choice = event.choices[choice_index]
        return self.event_manager.apply_choice(choice, self.team, event.id)

    # ── core play loop ───────────────────────────────────────────────────────

    def play_series(self) -> dict:
        self._init_bracket()

        current_stage_pre = self.state.stage.value

        if current_stage_pre in ("stage1", "stage2"):
            opponent = self._get_paired_opponent(current_stage_pre)
        else:
            # Playoffs: pick opponent from the bracket's player_match slot
            opponent = self._get_playoff_opponent(current_stage_pre)

        if opponent.name not in self._used_team_names:
            self._used_team_names.append(opponent.name)

        detail: SeriesDetail = resolve_series(self.team, opponent)
        description = describe_result(detail, opponent.name)

        current_stage = self.state.stage.value
        player_won    = detail.team_won

        # Capture record BEFORE advancing (for HistoryEntry and Swiss pairing)
        if self.state.stage == CampaignStage.STAGE1:
            wins_before   = self.state.stage1.wins
            losses_before = self.state.stage1.losses
        elif self.state.stage == CampaignStage.STAGE2:
            wins_before   = self.state.stage2.wins
            losses_before = self.state.stage2.losses
        else:
            wins_before = losses_before = 0

        # ── Simulate NPC Swiss round in parallel ──────────────────────────
        # The player's opponent is an NPC; its result is the inverse of ours.
        # We register that result directly here (before _run_swiss_round which skips this pair).
        if current_stage in ("stage1", "stage2"):
            opp_npc = next((t for t in self.npc_teams if t.name == opponent.name), None)
            if opp_npc:
                opp_won = not player_won
                if current_stage == "stage1":
                    opp_wb = opp_npc.s1_wins
                    opp_lb = opp_npc.s1_losses
                    if opp_won: opp_npc.s1_wins += 1
                    else:       opp_npc.s1_losses += 1
                    opp_npc.s1_history.append({
                        "wins_before": opp_wb, "losses_before": opp_lb,
                        "opponent": self.team.name, "result": "win" if opp_won else "loss"
                    })
                    if opp_npc.s1_wins >= 3 or opp_npc.s1_losses >= 3:
                        opp_npc.s1_done    = True
                        opp_npc.advanced_s1 = opp_npc.s1_wins >= 3
                else:
                    opp_wb = opp_npc.s2_wins
                    opp_lb = opp_npc.s2_losses
                    if opp_won: opp_npc.s2_wins += 1
                    else:       opp_npc.s2_losses += 1
                    opp_npc.s2_history.append({
                        "wins_before": opp_wb, "losses_before": opp_lb,
                        "opponent": self.team.name, "result": "win" if opp_won else "loss"
                    })
                    if opp_npc.s2_wins >= 3 or opp_npc.s2_losses >= 3:
                        opp_npc.s2_done    = True
                        opp_npc.advanced_s2 = opp_npc.s2_wins >= 3

            # Now run the rest of the round using the pairings already revealed
            # in the bracket UI (guarantees what's shown matches what's simulated)
            _run_swiss_round(self.npc_teams, current_stage,
                             self.pending_pairings, self.team.name)

        self._accumulate_stats(detail, opponent)
        self._apply_post_series_effects(player_won)

        entry = HistoryEntry(
            series_number  = self.state.total_series + 1,
            stage          = current_stage,
            opponent_name  = opponent.name,
            result         = "win" if player_won else "loss",
            wins_before    = wins_before,
            losses_before  = losses_before,
        )
        self.state.history.append(entry)
        self.state.total_series += 1

        prev_stage = self.state.stage
        self._advance_stage(player_won)
        stage_changed = self.state.stage != prev_stage

        # ── Stage transitions ─────────────────────────────────────────────
        if stage_changed:
            if current_stage == "stage1":
                # Finish remaining NPC S1 rounds
                _finish_swiss(self.npc_teams, "stage1")
                # Player took 1 of the 8 advancement slots iff they advanced.
                player_advanced_s1 = (self.state.stage != CampaignStage.FINISHED_LOSS)
                _enforce_swiss_capacity(self.npc_teams, "stage1", player_advanced_s1)

            if self.state.stage == CampaignStage.PLAYOFFS_QF:
                # Finish NPC S2 rounds, then build full playoff bracket
                _finish_swiss(self.npc_teams, "stage2")
                _enforce_swiss_capacity(self.npc_teams, "stage2", True)
                self._build_playoff_bracket()

            if current_stage == "stage2" and self.state.stage == CampaignStage.FINISHED_LOSS:
                _finish_swiss(self.npc_teams, "stage2")
                _enforce_swiss_capacity(self.npc_teams, "stage2", False)
                self._build_playoff_bracket()

        # ── Update playoff bracket with player's result ───────────────────
        if current_stage.startswith("playoffs_"):
            _resolve_player_slot(self.playoff_bracket, current_stage,
                                 self.team.name, player_won, opponent.name)
            if current_stage == "playoffs_final" and player_won:
                self.playoff_bracket["champion"] = self.team.name

        # ── Reveal the next round's pairings (if still in a Swiss stage) ──
        self._refresh_pending_pairings()

        stage_mvp = None
        if stage_changed:
            stage_mvp = self._finalise_stage_mvp()
            self._stage_stats = {}

        return {
            "won":             player_won,
            "description":     description,
            "opponent":        opponent,
            "team_score":      detail.team_strength,
            "opp_score":       detail.opponent_strength,
            "win_probability": detail.win_probability,
            "series_detail":   detail.to_dict(),
            "stage_finished":  self.state.is_finished(),
            "current_stage":   self.state.stage,
            "stage_mvp":       stage_mvp,
        }

    def _build_playoff_bracket(self) -> None:
        """Seed and simulate full 8-team playoff bracket."""
        player_str = round(self.team.team_score(), 2)
        qualifiers = [{"name": self.team.name, "strength": player_str, "is_player": True}]
        for t in self.npc_teams:
            if t.advanced_s2:
                qualifiers.append({"name": t.name, "strength": t.strength, "is_player": False})

        # Sort by strength for seeding
        qualifiers.sort(key=lambda x: x["strength"], reverse=True)

        # Safety net: should never trigger now that _enforce_swiss_capacity
        # guarantees exactly 8 qualifiers, but guards against corrupted saves.
        while len(qualifiers) < 8:
            qualifiers.append({"name": f"A definir #{len(qualifiers)+1}",
                                "strength": 5.0, "is_player": False})
        qualifiers = qualifiers[:8]

        self.playoff_bracket = _build_playoffs(qualifiers)

    # ── stat accumulation ────────────────────────────────────────────────────

    def _accumulate_stats(self, detail: SeriesDetail, opponent: Opponent) -> None:
        for ps in detail.player_stats:
            s = self._stage_stats.setdefault(ps.nickname, {
                "nickname": ps.nickname, "team": self.team.name,
                "role": ps.role, "kills": 0, "deaths": 0,
                "assists": 0, "adr_total": 0.0, "rounds": 0,
            })
            s["kills"] += ps.kills; s["deaths"] += ps.deaths
            s["assists"] += ps.assists; s["adr_total"] += ps.adr_total
            s["rounds"] += ps.rounds

        for os_ in detail.opponent_player_stats:
            s = self._stage_stats.setdefault(os_["nickname"], {
                "nickname": os_["nickname"], "team": opponent.name,
                "role": os_.get("role", "?"), "kills": 0, "deaths": 0,
                "assists": 0, "adr_total": 0.0, "rounds": 0,
            })
            s["kills"] += os_["kills"]; s["deaths"] += os_["deaths"]
            s["assists"] += os_.get("assists", 0)
            s["adr_total"] += os_.get("adr", 75) * os_["rounds"]
            s["rounds"] += os_["rounds"]

    def _finalise_stage_mvp(self) -> Optional[dict]:
        if not self._stage_stats:
            return None
        best   = max(self._stage_stats.values(), key=_compute_rating)
        rating = _compute_rating(best)
        return {
            "nickname": best["nickname"], "team": best["team"], "role": best["role"],
            "kills": best["kills"], "deaths": best["deaths"],
            "kd":  round(best["kills"] / max(best["deaths"], 1), 2),
            "adr": round(best["adr_total"] / max(best["rounds"], 1), 1),
            "rating": rating, "rounds": best["rounds"],
        }

    # ── post-series effects ──────────────────────────────────────────────────

    def _apply_post_series_effects(self, won: bool) -> None:
        self.team.tick_buffs()
        for p in self.team.players:
            p.status.morale += 1.5 if won else -1.5
            p.status.form    = max(-5.0, min(5.0, p.status.form + (0.6 if won else -0.6)))
            phys = random.uniform(10.0, 18.0)
            ment = random.uniform(6.0, 12.0) + (0 if won else 7.0)
            if p.trait.name == "Workaholic":            phys += 6.0
            if p.trait.name == "Tilta Fácil" and not won: ment += 10.0
            if p.trait.name == "Veterano":              ment -= 4.0
            if p.trait.name == "Piadista":              ment -= 3.0
            if p.trait.name == "Inconsistente":         ment += random.uniform(-4, 4)
            p.status.physical = max(0.0, p.status.physical - phys)
            p.status.mental   = max(0.0, p.status.mental   - ment)
            p.status.rest(6.0)
            p.status.clamp()

    # ── stage progression ────────────────────────────────────────────────────

    def _advance_stage(self, won: bool) -> None:
        st = self.state.stage
        if st == CampaignStage.STAGE1:
            r = self.state.stage1; r.wins += won; r.losses += not won; r.series_played += 1
            if r.is_advanced():   self.state.stage = CampaignStage.STAGE2;        self._rest(22)
            elif r.is_eliminated(): self.state.stage = CampaignStage.FINISHED_LOSS
        elif st == CampaignStage.STAGE2:
            r = self.state.stage2; r.wins += won; r.losses += not won; r.series_played += 1
            if r.is_advanced():   self.state.stage = CampaignStage.PLAYOFFS_QF;   self._rest(28)
            elif r.is_eliminated(): self.state.stage = CampaignStage.FINISHED_LOSS
        elif st == CampaignStage.PLAYOFFS_QF:
            self.state.stage = CampaignStage.PLAYOFFS_SF if won else CampaignStage.FINISHED_LOSS
            if won: self._rest(18)
        elif st == CampaignStage.PLAYOFFS_SF:
            self.state.stage = CampaignStage.PLAYOFFS_FINAL if won else CampaignStage.FINISHED_LOSS
            if won: self._rest(18)
        elif st == CampaignStage.PLAYOFFS_FINAL:
            self.state.stage = CampaignStage.FINISHED_WIN if won else CampaignStage.FINISHED_LOSS

    def _rest(self, amount: float) -> None:
        for p in self.team.players:
            p.status.rest(amount); p.status.clamp()

    # ── API output ───────────────────────────────────────────────────────────

    def get_stage_status(self) -> str:
        st = self.state.stage
        if st == CampaignStage.STAGE1:
            r = self.state.stage1; return f"Stage 1 — {r.wins}W / {r.losses}L"
        if st == CampaignStage.STAGE2:
            r = self.state.stage2; return f"Stage 2 — {r.wins}W / {r.losses}L"
        return self.state.current_stage_label()

    def get_bracket_state(self) -> dict:
        return {
            "npc_teams":        [t.to_dict() for t in self.npc_teams],
            "playoff_bracket":  self.playoff_bracket,
            "player_name":      self.team.name,
            "pending_pairings": self.pending_pairings,
        }

    def to_dict(self) -> dict:
        return {
            "state":               self.state.to_dict(),
            "used_event_ids":      self._used_event_ids,
            "events_enabled":      self.events_enabled,
            "stage_stats":         self._stage_stats,
            "era_id":              self.era_id,
            "used_team_names":     self._used_team_names,
            "npc_teams":           [t.to_dict() for t in self.npc_teams],
            "npc_team_data":       self._npc_team_data,
            "playoff_bracket":     self.playoff_bracket,
            "bracket_initialized": self._bracket_initialized,
            "pending_pairings":    self.pending_pairings,
        }

    def load_from_dict(self, data: dict) -> None:
        self.state                = CampaignState.from_dict(data["state"])
        self._used_event_ids      = data.get("used_event_ids", [])
        self.events_enabled       = data.get("events_enabled", False)
        self._stage_stats         = data.get("stage_stats", {})
        self.era_id               = data.get("era_id")
        self._used_team_names     = data.get("used_team_names", [])
        self.npc_teams            = [NpcTeam.from_dict(d) for d in data.get("npc_teams", [])]
        self._npc_team_data       = data.get("npc_team_data", {})
        self.playoff_bracket      = data.get("playoff_bracket", {})
        self._bracket_initialized = data.get("bracket_initialized", False)
        self.pending_pairings     = data.get("pending_pairings", [])
