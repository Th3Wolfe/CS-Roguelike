"""Player model with HLTV-style attributes and role system."""
from dataclasses import dataclass, field
from enum import Enum
from models.traits import Trait

# Scale factor: HLTV attributes (typically 6-10) are scaled down so team scores
# land in a range comparable with opponent strengths (opponents range 6-9.5)
ATTR_SCALE = 0.60


class PlayerRole(str, Enum):
    ENTRY   = "Entry Fragger"
    AWP     = "AWPer"
    LURK    = "Lurker"
    SUPPORT = "Support"
    IGL     = "IGL"

    def description(self) -> str:
        return {
            PlayerRole.ENTRY:   "Abre duelos, entra primeiro, cria pressão.",
            PlayerRole.AWP:     "Sniper principal. Controla distâncias e rotas.",
            PlayerRole.LURK:    "Flanqueia, cria confusão no momento certo.",
            PlayerRole.SUPPORT: "Smokes, flashes, trades. A cola do time.",
            PlayerRole.IGL:     "Líder in-game. Define estratégia e pace.",
        }[self]

    def key_stats(self) -> list[str]:
        return {
            PlayerRole.ENTRY:   ["kpr", "impact", "rating"],
            PlayerRole.AWP:     ["rating", "adr", "impact"],
            PlayerRole.LURK:    ["kpr", "kast", "rating"],
            PlayerRole.SUPPORT: ["kast", "rating", "kpr"],
            PlayerRole.IGL:     ["kast", "impact", "rating"],
        }[self]

    def score_weights(self) -> dict[str, float]:
        return {
            PlayerRole.ENTRY:   {"rating":1.5,"kpr":2.0,"impact":2.0,"kast":0.8,"adr":1.2},
            PlayerRole.AWP:     {"rating":2.0,"kpr":1.2,"impact":1.8,"kast":1.2,"adr":1.8},
            PlayerRole.LURK:    {"rating":1.8,"kpr":1.8,"impact":1.5,"kast":1.4,"adr":1.0},
            PlayerRole.SUPPORT: {"rating":1.5,"kpr":1.0,"impact":1.2,"kast":2.5,"adr":1.0},
            PlayerRole.IGL:     {"rating":1.5,"kpr":1.0,"impact":1.8,"kast":2.0,"adr":1.2},
        }[self]


@dataclass
class PlayerAttributes:
    """HLTV-style attributes (stored in raw HLTV scale, ~1-10)."""
    rating: float = 5.0
    kast:   float = 5.0
    impact: float = 5.0
    adr:    float = 5.0
    kpr:    float = 5.0

    def weighted_average(self, weights: dict[str, float] | None = None) -> float:
        """Weighted average in raw scale."""
        if weights is None:
            return (self.rating*2 + self.kast + self.impact + self.adr + self.kpr) / 6
        total_w = sum(weights.values())
        val = (self.rating * weights.get("rating",1)
             + self.kast   * weights.get("kast",1)
             + self.impact * weights.get("impact",1)
             + self.adr    * weights.get("adr",1)
             + self.kpr    * weights.get("kpr",1))
        return val / total_w

    def clamp(self) -> None:
        for attr in ("rating","kast","impact","adr","kpr"):
            setattr(self, attr, max(1.0, min(10.0, getattr(self, attr))))

    def to_dict(self) -> dict:
        return {k: round(getattr(self,k), 2) for k in ("rating","kast","impact","adr","kpr")}

    @staticmethod
    def from_dict(data: dict) -> "PlayerAttributes":
        return PlayerAttributes(**{k: data.get(k, 5.0) for k in ("rating","kast","impact","adr","kpr")})


@dataclass
class PlayerStatus:
    morale:   float = 0.0
    form:     float = 0.0
    physical: float = 100.0
    mental:   float = 100.0

    @property
    def energy(self) -> float:
        return (self.physical + self.mental) / 2

    def clamp(self) -> None:
        self.morale   = max(-5.0, min(5.0,   self.morale))
        self.form     = max(-5.0, min(5.0,   self.form))
        self.physical = max(0.0,  min(100.0, self.physical))
        self.mental   = max(0.0,  min(100.0, self.mental))

    def rest(self, amount: float = 15.0) -> None:
        self.physical = min(100.0, self.physical + amount)
        self.mental   = min(100.0, self.mental   + amount * 0.7)

    def to_dict(self) -> dict:
        return {k: round(getattr(self,k),2) for k in ("morale","form","physical","mental")}

    @staticmethod
    def from_dict(data: dict) -> "PlayerStatus":
        if "energy" in data and "physical" not in data:
            e = data["energy"]
            return PlayerStatus(morale=data.get("morale",0.0), form=data.get("form",0.0),
                                physical=e, mental=e)
        return PlayerStatus(**{k: data.get(k, d)
                               for k, d in [("morale",0.0),("form",0.0),("physical",100.0),("mental",100.0)]})


@dataclass
class Player:
    name:       str
    nickname:   str
    country:    str
    role:       PlayerRole
    attributes: PlayerAttributes
    status:     PlayerStatus
    trait:      Trait
    era:        str = "?"
    buffs:      list = field(default_factory=list)

    def effective_score(self) -> float:
        """Game-scale score contribution. Scaled so team scores land ~5.5–8.5."""
        weights    = self.role.score_weights()
        raw_avg    = self.attributes.weighted_average(weights)
        base       = raw_avg * ATTR_SCALE          # compress to game scale

        # Status modifiers (small, max ±0.6 combined)
        morale_mod = self.status.morale   * 0.06   # ±0.30 max
        form_mod   = self.status.form     * 0.06   # ±0.30 max
        phys_mod   = (self.status.physical - 60) / 200  # –0.30 → +0.20
        ment_mod   = (self.status.mental   - 60) / 150  # –0.40 → +0.27
        buff_total = sum(b.effect for b in self.buffs) * 0.1

        return base + morale_mod + form_mod + phys_mod + ment_mod + buff_total

    def to_dict(self) -> dict:
        return {
            "name": self.name, "nickname": self.nickname, "country": self.country,
            "era": self.era,
            "role": self.role.value,
            "attributes": self.attributes.to_dict(),
            "status":     self.status.to_dict(),
            "trait":      self.trait.name,
            "buffs":      [b.to_dict() for b in self.buffs],
        }

    @staticmethod
    def from_dict(data: dict) -> "Player":
        from models.traits import get_trait_by_name
        from models.buff import Buff
        role_val = data.get("role", PlayerRole.ENTRY.value)
        try:    role = PlayerRole(role_val)
        except: role = PlayerRole.ENTRY
        return Player(
            name=data.get("name",""), nickname=data.get("nickname",""),
            country=data.get("country","BR"), era=data.get("era","?"), role=role,
            attributes=PlayerAttributes.from_dict(data.get("attributes",{})),
            status=PlayerStatus.from_dict(data.get("status",{})),
            trait=get_trait_by_name(data.get("trait","Veterano")),
            buffs=[Buff.from_dict(b) for b in data.get("buffs",[])],
        )
