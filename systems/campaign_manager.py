"""Campaign manager: orchestrates stage progression and series flow."""
import random
from models.campaign import CampaignState, CampaignStage, HistoryEntry
from models.team import Team
from models.opponent import Opponent, generate_opponent
from systems.match_resolver import resolve_series, describe_result, SeriesDetail, _simulate_opponent_player_stats
from events.event_manager import EventManager


def _compute_rating(stats: dict) -> float:
    """
    Simplified HLTV-style rating from accumulated K/D/KPR/ADR.
    Rating ≈ 0.0–2.0, average ~1.0
    """
    kd  = stats["kills"] / max(stats["deaths"], 1)
    kpr = stats["kills"] / max(stats["rounds"], 1)
    adr = stats["adr_total"] / max(stats["rounds"], 1)
    # Normalise each component to ~1.0 at average
    kd_n  = kd  / 1.0
    kpr_n = kpr / 0.68
    adr_n = adr / 80.0
    return round((kd_n * 0.4 + kpr_n * 0.35 + adr_n * 0.25), 3)


class CampaignManager:
    """Controls the flow of the Major campaign."""

    def __init__(self, team: Team, events_enabled: bool = False) -> None:
        self.team = team
        self.state = CampaignState()
        self.events_enabled = events_enabled
        self.event_manager = EventManager()
        self._used_event_ids: list[str] = []
        # Accumulated stats for current stage: nickname -> {kills,deaths,assists,adr_total,rounds,team,role}
        self._stage_stats: dict = {}
        self._last_stage_mvp: dict | None = None   # best player in just-finished stage

    # ── events ──────────────────────────────────────────────────────────────

    def get_pending_events(self) -> list:
        events = self.event_manager.select_events_for_series(
            self.state.stage.value, self._used_event_ids
        )
        for e in events:
            self._used_event_ids.append(e.id)
        return events

    def apply_event_choice(self, event, choice_index: int) -> list[str]:
        choice = event.choices[choice_index]
        return self.event_manager.apply_choice(choice, self.team, event.id)

    # ── core series flow ─────────────────────────────────────────────────────

    def play_series(self) -> dict:
        """Play a series. Returns full result dict with series_detail and stage MVP."""
        opponent = generate_opponent(self.state.stage.value, self.state.total_series)
        detail: SeriesDetail = resolve_series(self.team, opponent)
        description = describe_result(detail, opponent.name)

        # Accumulate player stats for the stage leaderboard
        self._accumulate_stats(detail, opponent)

        self._apply_post_series_effects(detail.team_won)

        entry = HistoryEntry(
            series_number=self.state.total_series + 1,
            stage=self.state.stage.value,
            opponent_name=opponent.name,
            result="win" if detail.team_won else "loss",
        )
        self.state.history.append(entry)
        self.state.total_series += 1

        prev_stage = self.state.stage
        self._advance_stage(detail.team_won)
        stage_changed = self.state.stage != prev_stage

        # If stage changed (advance or elimination), finalise MVP
        stage_mvp = None
        if stage_changed:
            stage_mvp = self._finalise_stage_mvp()
            self._stage_stats = {}   # reset for next stage

        return {
            "won":             detail.team_won,
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

    # ── stat accumulation ────────────────────────────────────────────────────

    def _accumulate_stats(self, detail: SeriesDetail, opponent: Opponent) -> None:
        # Team players
        for ps in detail.player_stats:
            key = ps.nickname
            if key not in self._stage_stats:
                self._stage_stats[key] = {
                    "nickname": ps.nickname, "team": self.team.name,
                    "role": ps.role, "kills": 0, "deaths": 0,
                    "assists": 0, "adr_total": 0.0, "rounds": 0,
                }
            s = self._stage_stats[key]
            s["kills"]     += ps.kills
            s["deaths"]    += ps.deaths
            s["assists"]   += ps.assists
            s["adr_total"] += ps.adr_total
            s["rounds"]    += ps.rounds

        # Opponent fictional players
        opp_stats = _simulate_opponent_player_stats(opponent.name, opponent.strength, detail.maps)
        for os_ in opp_stats:
            key = os_["nickname"]
            if key not in self._stage_stats:
                self._stage_stats[key] = {
                    "nickname": os_["nickname"], "team": os_["team"],
                    "role": os_["role"], "kills": 0, "deaths": 0,
                    "assists": 0, "adr_total": os_.get("adr", 75) * os_["rounds"],
                    "rounds": 0,
                }
            s = self._stage_stats[key]
            s["kills"]     += os_["kills"]
            s["deaths"]    += os_["deaths"]
            s["assists"]   += os_["assists"]
            s["adr_total"] += os_.get("adr", 75) * os_["rounds"]
            s["rounds"]    += os_["rounds"]

    def _finalise_stage_mvp(self) -> dict | None:
        """Return the player with the best rating across all teams in the stage."""
        if not self._stage_stats:
            return None
        best = max(self._stage_stats.values(), key=lambda s: _compute_rating(s))
        rating = _compute_rating(best)
        kd = round(best["kills"] / max(best["deaths"], 1), 2)
        adr = round(best["adr_total"] / max(best["rounds"], 1), 1)
        return {
            "nickname": best["nickname"],
            "team":     best["team"],
            "role":     best["role"],
            "kills":    best["kills"],
            "deaths":   best["deaths"],
            "kd":       kd,
            "adr":      adr,
            "rating":   rating,
            "rounds":   best["rounds"],
        }

    # ── post-series effects ──────────────────────────────────────────────────

    def _apply_post_series_effects(self, won: bool) -> None:
        self.team.tick_buffs()
        morale_change = 1.5 if won else -1.5
        form_change   = 0.6 if won else -0.6

        for p in self.team.players:
            p.status.morale += morale_change
            p.status.form    = max(-5.0, min(5.0, p.status.form + form_change))

            phys_drain = random.uniform(10.0, 18.0)
            ment_drain = random.uniform(6.0, 12.0) + (0 if won else 7.0)

            if p.trait.name == "Workaholic":    phys_drain += 6.0
            if p.trait.name == "Tilta Fácil" and not won: ment_drain += 10.0
            if p.trait.name == "Veterano":      ment_drain -= 4.0
            if p.trait.name == "Piadista":      ment_drain -= 3.0
            if p.trait.name == "Inconsistente": ment_drain += random.uniform(-4, 4)

            p.status.physical = max(0.0, p.status.physical - phys_drain)
            p.status.mental   = max(0.0, p.status.mental   - ment_drain)
            p.status.rest(6.0)
            p.status.clamp()

    # ── stage progression ────────────────────────────────────────────────────

    def _advance_stage(self, won: bool) -> None:
        stage = self.state.stage

        if stage == CampaignStage.STAGE1:
            rec = self.state.stage1
            rec.wins += won; rec.losses += not won; rec.series_played += 1
            if rec.is_advanced():
                self.state.stage = CampaignStage.STAGE2
                self._apply_stage_rest(22.0)
            elif rec.is_eliminated():
                self.state.stage = CampaignStage.FINISHED_LOSS

        elif stage == CampaignStage.STAGE2:
            rec = self.state.stage2
            rec.wins += won; rec.losses += not won; rec.series_played += 1
            if rec.is_advanced():
                self.state.stage = CampaignStage.PLAYOFFS_QF
                self._apply_stage_rest(28.0)
            elif rec.is_eliminated():
                self.state.stage = CampaignStage.FINISHED_LOSS

        elif stage == CampaignStage.PLAYOFFS_QF:
            self.state.stage = CampaignStage.PLAYOFFS_SF if won else CampaignStage.FINISHED_LOSS
            if won: self._apply_stage_rest(18.0)

        elif stage == CampaignStage.PLAYOFFS_SF:
            self.state.stage = CampaignStage.PLAYOFFS_FINAL if won else CampaignStage.FINISHED_LOSS
            if won: self._apply_stage_rest(18.0)

        elif stage == CampaignStage.PLAYOFFS_FINAL:
            self.state.stage = CampaignStage.FINISHED_WIN if won else CampaignStage.FINISHED_LOSS

    def _apply_stage_rest(self, amount: float) -> None:
        for p in self.team.players:
            p.status.rest(amount)
            p.status.clamp()

    # ── serialisation ────────────────────────────────────────────────────────

    def get_stage_status(self) -> str:
        stage = self.state.stage
        if stage == CampaignStage.STAGE1:
            r = self.state.stage1
            return f"Stage 1 — {r.wins}W / {r.losses}L"
        if stage == CampaignStage.STAGE2:
            r = self.state.stage2
            return f"Stage 2 — {r.wins}W / {r.losses}L"
        return self.state.current_stage_label()

    def to_dict(self) -> dict:
        return {
            "state":           self.state.to_dict(),
            "used_event_ids":  self._used_event_ids,
            "events_enabled":  self.events_enabled,
            "stage_stats":     self._stage_stats,
        }

    def load_from_dict(self, data: dict) -> None:
        self.state = CampaignState.from_dict(data["state"])
        self._used_event_ids = data.get("used_event_ids", [])
        self.events_enabled  = data.get("events_enabled", False)
        self._stage_stats    = data.get("stage_stats", {})
