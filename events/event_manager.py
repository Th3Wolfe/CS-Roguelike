"""Event manager: loads, selects, and applies events."""
import copy
import json
import os
import random
from models.event import GameEvent, EventChoice
from models.team import Team
from models.buff import Buff


EVENT_FILES = [
    "events_performance.json",
    "events_relations.json",
    "events_other.json",
]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class EventManager:
    """Loads events from JSON files and manages event selection and application."""

    def __init__(self) -> None:
        self._all_events: list[GameEvent] = []
        self._load_all_events()

    def _load_all_events(self) -> None:
        """Load all events from JSON files."""
        for filename in EVENT_FILES:
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw:
                self._all_events.append(GameEvent.from_dict(item))

    def select_events_for_series(self, stage: str, already_used: list[str]) -> list[GameEvent]:
        """Select up to 2 events for the current series (no duplicates in run)."""
        available = [e for e in self._all_events if e.id not in already_used]
        count = random.randint(1, 2)
        if len(available) < count:
            count = len(available)
        return random.sample(available, count) if available else []

    def apply_choice(self, choice: EventChoice, team: Team, event_id: str) -> list[str]:
        """Apply all effects of a chosen event option to the team.

        Returns a list of human-readable effect descriptions.
        """
        messages: list[str] = []
        all_effects = (
            choice.immediate_effects
            + choice.temporary_effects
            + choice.hidden_effects
        )
        for effect in all_effects:
            msgs = self._apply_effect(effect, team, event_id)
            messages.extend(msgs)
        return messages

    def _apply_effect(self, effect, team: Team, origin: str) -> list[str]:
        """Apply a single EffectEntry to the team and return description messages."""
        messages: list[str] = []
        target = effect.target
        attr = effect.attribute
        value = effect.value

        if effect.is_temporary:
            buff = Buff(
                name=f"{attr} temporário",
                duration=effect.duration,
                effect=value,
                origin=origin,
                description=f"{attr} {'+' if value > 0 else ''}{value} por {effect.duration} série(s)",
            )
            if target == "team":
                team.team_buffs.append(buff)
                messages.append(f"Time: buff {buff.description}")
            elif target in ("player_random", "player_igl"):
                player = self._select_player(team, target)
                if player:
                    player.buffs.append(copy.copy(buff))
                    messages.append(f"{player.nickname}: buff {buff.description}")
            elif target == "player_all":
                for p in team.players:
                    p.buffs.append(copy.copy(buff))
                messages.append(f"Todos: buff {buff.description}")
        else:
            if target == "team":
                self._set_team_attr(team, attr, value)
                messages.append(f"Time: {attr} {'+' if value > 0 else ''}{value:.1f}")
            elif target in ("player_random", "player_igl"):
                player = self._select_player(team, target)
                if player:
                    self._set_player_attr(player, attr, value)
                    messages.append(f"{player.nickname}: {attr} {'+' if value > 0 else ''}{value:.1f}")
            elif target == "player_all":
                for p in team.players:
                    self._set_player_attr(p, attr, value)
                messages.append(f"Todos: {attr} {'+' if value > 0 else ''}{value:.1f}")

        return messages

    def _select_player(self, team: Team, target: str):
        """Select a player based on target string."""
        if not team.players:
            return None
        if target == "player_igl":
            for p in team.players:
                if p.trait.name == "IGL Nato":
                    return p
            return random.choice(team.players)
        return random.choice(team.players)

    def _set_team_attr(self, team: Team, attr: str, value: float) -> None:
        """Apply an attribute change to the team."""
        if attr == "synergy":
            team.synergy += value
            team.clamp_synergy()

    def _set_player_attr(self, player, attr: str, value: float) -> None:
        """Apply an attribute change to a player, supporting HLTV and legacy attrs."""
        # Legacy skill attr names → map to HLTV equivalents
        legacy_map = {
            "aim": "kpr",
            "tactics": "impact",
            "consistency": "kast",
            "clutch": "impact",
            "communication": "kast",
        }
        # Status attributes
        status_attrs = {"morale", "form", "energy", "physical", "mental"}
        # HLTV skill attributes
        hltv_attrs = {"rating", "kast", "impact", "adr", "kpr"}

        if attr in status_attrs:
            if attr == "energy":
                # Legacy: apply to both physical and mental
                player.status.physical = min(100.0, max(0.0, player.status.physical + value))
                player.status.mental = min(100.0, max(0.0, player.status.mental + value))
            else:
                current = getattr(player.status, attr, 0.0)
                setattr(player.status, attr, current + value)
            player.status.clamp()
        elif attr in hltv_attrs:
            current = getattr(player.attributes, attr)
            setattr(player.attributes, attr, current + value)
            player.attributes.clamp()
        elif attr in legacy_map:
            # Map old attributes to HLTV equivalents
            mapped = legacy_map[attr]
            current = getattr(player.attributes, mapped)
            setattr(player.attributes, mapped, current + value * 0.3)  # Scaled down
            player.attributes.clamp()
