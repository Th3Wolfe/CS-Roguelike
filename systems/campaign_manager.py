"""Campaign manager: orchestrates stage progression and series flow."""
import random
from models.campaign import CampaignState, CampaignStage, HistoryEntry
from models.team import Team
from models.opponent import Opponent, generate_opponent
from systems.match_resolver import resolve_series, describe_result, SeriesDetail
from events.event_manager import EventManager


class CampaignManager:
    """Controls the flow of the Major campaign."""

    def __init__(self, team: Team, events_enabled: bool = False) -> None:
        self.team = team
        self.state = CampaignState()
        self.events_enabled = events_enabled
        self.event_manager = EventManager()
        self._used_event_ids: list[str] = []

    def get_pending_events(self) -> list:
        """Return 1-2 events to show before the next series."""
        events = self.event_manager.select_events_for_series(
            self.state.stage.value, self._used_event_ids
        )
        for e in events:
            self._used_event_ids.append(e.id)
        return events

    def apply_event_choice(self, event, choice_index: int) -> list[str]:
        choice = event.choices[choice_index]
        return self.event_manager.apply_choice(choice, self.team, event.id)

    def play_series(self) -> dict:
        """Play a series. Returns full result dict with series_detail."""
        opponent = generate_opponent(self.state.stage.value, self.state.total_series)
        detail: SeriesDetail = resolve_series(self.team, opponent)
        description = describe_result(detail, opponent.name)

        self._apply_post_series_effects(detail.team_won)

        entry = HistoryEntry(
            series_number=self.state.total_series + 1,
            stage=self.state.stage.value,
            opponent_name=opponent.name,
            result="win" if detail.team_won else "loss",
        )
        self.state.history.append(entry)
        self.state.total_series += 1
        self._advance_stage(detail.team_won)

        return {
            "won":            detail.team_won,
            "description":    description,
            "opponent":       opponent,
            "team_score":     detail.team_strength,
            "opp_score":      detail.opponent_strength,
            "win_probability":detail.win_probability,
            "series_detail":  detail.to_dict(),
            "stage_finished": self.state.is_finished(),
            "current_stage":  self.state.stage,
        }

    def _apply_post_series_effects(self, won: bool) -> None:
        """Apply morale, form, and dual-energy changes after a series."""
        self.team.tick_buffs()
        morale_change = 1.5 if won else -1.5
        form_change   = 0.6 if won else -0.6

        for p in self.team.players:
            p.status.morale += morale_change
            p.status.form    = max(-5.0, min(5.0, p.status.form + form_change))

            # Physical drain (every match is taxing)
            phys_drain = random.uniform(10.0, 18.0)
            # Mental drain (losses hurt harder)
            ment_drain = random.uniform(6.0, 12.0) + (0 if won else 7.0)

            # Trait modifiers
            if p.trait.name == "Workaholic":    phys_drain += 6.0
            if p.trait.name == "Tilta Fácil" and not won: ment_drain += 10.0
            if p.trait.name == "Veterano":      ment_drain -= 4.0
            if p.trait.name == "Piadista":      ment_drain -= 3.0
            if p.trait.name == "Inconsistente": ment_drain += random.uniform(-4, 4)

            p.status.physical = max(0.0, p.status.physical - phys_drain)
            p.status.mental   = max(0.0, p.status.mental   - ment_drain)

            # Small natural recovery between series
            p.status.rest(6.0)
            p.status.clamp()

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
        return {"state": self.state.to_dict(), "used_event_ids": self._used_event_ids, "events_enabled": self.events_enabled}

    def load_from_dict(self, data: dict) -> None:
        self.state = CampaignState.from_dict(data["state"])
        self._used_event_ids = data.get("used_event_ids", [])
        self.events_enabled = data.get("events_enabled", False)
