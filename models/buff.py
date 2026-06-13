"""Buff and debuff system for temporary modifiers."""
from dataclasses import dataclass


@dataclass
class Buff:
    """A temporary modifier applied to a player or team."""
    name: str
    duration: int       # Number of series remaining
    effect: float       # Numeric modifier (positive = buff, negative = debuff)
    origin: str         # Where this buff came from (event id, system, etc.)
    description: str = ""

    def tick(self) -> None:
        """Reduce duration by 1 after a series ends."""
        self.duration -= 1

    def is_expired(self) -> bool:
        """Check if this buff should be removed."""
        return self.duration <= 0

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "name": self.name,
            "duration": self.duration,
            "effect": self.effect,
            "origin": self.origin,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict) -> "Buff":
        """Deserialize from dict."""
        return Buff(
            name=data["name"],
            duration=data["duration"],
            effect=data["effect"],
            origin=data["origin"],
            description=data.get("description", ""),
        )
