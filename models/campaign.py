"""Campaign state model using enums."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CampaignStage(str, Enum):
    STAGE1 = "stage1"
    STAGE2 = "stage2"
    PLAYOFFS_QF = "playoffs_qf"
    PLAYOFFS_SF = "playoffs_sf"
    PLAYOFFS_FINAL = "playoffs_final"
    FINISHED_WIN = "finished_win"
    FINISHED_LOSS = "finished_loss"


class SeriesResult(str, Enum):
    WIN = "win"
    LOSS = "loss"


@dataclass
class StageRecord:
    """Win/loss record for a group stage."""
    wins: int = 0
    losses: int = 0
    series_played: int = 0

    def is_advanced(self) -> bool:
        return self.wins >= 3

    def is_eliminated(self) -> bool:
        return self.losses >= 3

    def to_dict(self) -> dict:
        return {"wins": self.wins, "losses": self.losses, "series_played": self.series_played}

    @staticmethod
    def from_dict(data: dict) -> "StageRecord":
        return StageRecord(**data)


@dataclass
class HistoryEntry:
    """A single entry in the match/event history."""
    series_number: int
    stage: str
    opponent_name: str
    result: str  # "win" or "loss"
    events_triggered: list = field(default_factory=list)
    choices_made: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "series_number": self.series_number,
            "stage": self.stage,
            "opponent_name": self.opponent_name,
            "result": self.result,
            "events_triggered": self.events_triggered,
            "choices_made": self.choices_made,
        }

    @staticmethod
    def from_dict(data: dict) -> "HistoryEntry":
        return HistoryEntry(**data)


@dataclass
class CampaignState:
    """Full state of the current Major campaign."""
    stage: CampaignStage = CampaignStage.STAGE1
    stage1: StageRecord = field(default_factory=StageRecord)
    stage2: StageRecord = field(default_factory=StageRecord)
    playoffs_results: list = field(default_factory=list)  # list of SeriesResult
    history: list = field(default_factory=list)  # list of HistoryEntry
    total_series: int = 0

    def current_stage_label(self) -> str:
        labels = {
            CampaignStage.STAGE1: "Stage 1",
            CampaignStage.STAGE2: "Stage 2",
            CampaignStage.PLAYOFFS_QF: "Playoffs – Quartas de Final",
            CampaignStage.PLAYOFFS_SF: "Playoffs – Semifinal",
            CampaignStage.PLAYOFFS_FINAL: "Playoffs – Grande Final",
            CampaignStage.FINISHED_WIN: "🏆 Campeão!",
            CampaignStage.FINISHED_LOSS: "Eliminado",
        }
        return labels.get(self.stage, self.stage.value)

    def is_finished(self) -> bool:
        return self.stage in (CampaignStage.FINISHED_WIN, CampaignStage.FINISHED_LOSS)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "stage1": self.stage1.to_dict(),
            "stage2": self.stage2.to_dict(),
            "playoffs_results": self.playoffs_results,
            "history": [h.to_dict() for h in self.history],
            "total_series": self.total_series,
        }

    @staticmethod
    def from_dict(data: dict) -> "CampaignState":
        return CampaignState(
            stage=CampaignStage(data["stage"]),
            stage1=StageRecord.from_dict(data["stage1"]),
            stage2=StageRecord.from_dict(data["stage2"]),
            playoffs_results=data.get("playoffs_results", []),
            history=[HistoryEntry.from_dict(h) for h in data.get("history", [])],
            total_series=data.get("total_series", 0),
        )
