"""Event model for in-game events."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EffectEntry:
    """A single effect from an event choice."""
    target: str        # "team", "player_random", "player_igl", "player_all"
    attribute: str     # "morale", "form", "energy", "synergy", "aim", etc.
    value: float
    is_temporary: bool = False
    duration: int = 0  # series, if temporary

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "attribute": self.attribute,
            "value": self.value,
            "is_temporary": self.is_temporary,
            "duration": self.duration,
        }

    @staticmethod
    def from_dict(data: dict) -> "EffectEntry":
        return EffectEntry(**data)


@dataclass
class EventChoice:
    """One of the three choices presented in an event."""
    text: str
    immediate_effects: list = field(default_factory=list)   # list[EffectEntry]
    temporary_effects: list = field(default_factory=list)   # list[EffectEntry] (buffs)
    hidden_effects: list = field(default_factory=list)      # list[EffectEntry]

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "immediate_effects": [e.to_dict() for e in self.immediate_effects],
            "temporary_effects": [e.to_dict() for e in self.temporary_effects],
            "hidden_effects": [e.to_dict() for e in self.hidden_effects],
        }

    @staticmethod
    def from_dict(data: dict) -> "EventChoice":
        return EventChoice(
            text=data["text"],
            immediate_effects=[EffectEntry.from_dict(e) for e in data.get("immediate_effects", [])],
            temporary_effects=[EffectEntry.from_dict(e) for e in data.get("temporary_effects", [])],
            hidden_effects=[EffectEntry.from_dict(e) for e in data.get("hidden_effects", [])],
        )


@dataclass
class GameEvent:
    """A complete event with description and three choices."""
    id: str
    name: str
    description: str
    context: str       # Category: performance, relations, etc.
    choices: list      # list[EventChoice], exactly 3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "context": self.context,
            "choices": [c.to_dict() for c in self.choices],
        }

    @staticmethod
    def from_dict(data: dict) -> "GameEvent":
        return GameEvent(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            context=data["context"],
            choices=[EventChoice.from_dict(c) for c in data["choices"]],
        )
