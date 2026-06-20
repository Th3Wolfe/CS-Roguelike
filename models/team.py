"""Team model."""
from dataclasses import dataclass, field
from models.player import Player
from models.buff import Buff


@dataclass
class Team:
    """Represents the player's team in the Major."""
    name: str
    players: list  # list[Player], 5 players
    synergy: float = 0.0  # -10 to +10
    team_buffs: list = field(default_factory=list)  # list[Buff]
    full_maps: list  = field(default_factory=list)   # 3 maps: full proficiency
    half_maps: list  = field(default_factory=list)   # 2 maps: half proficiency

    def clamp_synergy(self) -> None:
        """Clamp synergy to valid range."""
        self.synergy = max(-10.0, min(10.0, self.synergy))

    def average_score(self) -> float:
        """Calculate the average effective score of all players."""
        if not self.players:
            return 0.0
        return sum(p.effective_score() for p in self.players) / len(self.players)

    def team_score(self) -> float:
        """Calculate the total team score used for match resolution."""
        team_buff_total = sum(b.effect for b in self.team_buffs)
        return self.average_score() + self.synergy * 0.5 + team_buff_total

    def tick_buffs(self) -> None:
        """Tick all buffs (players and team) and remove expired ones."""
        for player in self.players:
            for buff in player.buffs:
                buff.tick()
            player.buffs = [b for b in player.buffs if not b.is_expired()]
        for buff in self.team_buffs:
            buff.tick()
        self.team_buffs = [b for b in self.team_buffs if not b.is_expired()]

    def all_buffs(self) -> list:
        """Return all active buffs (team + per-player)."""
        result = list(self.team_buffs)
        for p in self.players:
            result.extend(p.buffs)
        return result

    def to_dict(self) -> dict:
        """Serialize team to dict."""
        return {
            "name":       self.name,
            "synergy":    self.synergy,
            "players":    [p.to_dict() for p in self.players],
            "team_buffs": [b.to_dict() for b in self.team_buffs],
            "full_maps":  self.full_maps,
            "half_maps":  self.half_maps,
        }

    @staticmethod
    def from_dict(data: dict) -> "Team":
        """Deserialize team from dict."""
        from models.player import Player
        players    = [Player.from_dict(p) for p in data["players"]]
        team_buffs = [Buff.from_dict(b) for b in data.get("team_buffs", [])]
        return Team(
            name=data["name"],
            players=players,
            synergy=data.get("synergy", 0.0),
            team_buffs=team_buffs,
            full_maps=data.get("full_maps", []),
            half_maps=data.get("half_maps", []),
        )
