"""Trait definitions for player personalities."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Trait:
    """A personality trait that influences player behavior and events."""
    name: str
    description: str
    passive_bonus: dict  # e.g. {"clutch": +1, "consistency": -1}

    def apply_passive(self, attributes: object) -> None:
        """Apply passive bonuses/penalties to a PlayerAttributes object."""
        for attr, value in self.passive_bonus.items():
            if hasattr(attributes, attr):
                current = getattr(attributes, attr)
                setattr(attributes, attr, current + value)


# --- Trait definitions ---

VETERAN = Trait(
    name="Veterano",
    description="Experiência acumulada em grandes palcos. Mais calmo sob pressão.",
    passive_bonus={"consistency": 1, "clutch": 1},
)

CLUTCHER = Trait(
    name="Clutcher",
    description="Nasce para momentos decisivos. Execução brilha quando o mapa está em jogo.",
    passive_bonus={"clutch": 2, "consistency": -1},
)

WORKAHOLIC = Trait(
    name="Workaholic",
    description="Treina até cair. Alto rendimento, mas desgasta rápido.",
    passive_bonus={"aim": 1, "tactics": 1},
)

TILTS_EASILY = Trait(
    name="Tilta Fácil",
    description="Pequenos erros viram uma bola de neve. Instável sob pressão.",
    passive_bonus={"consistency": -2, "clutch": -1},
)

HIGH_EGO = Trait(
    name="Ego Elevado",
    description="Confiante ao extremo. Pode ignorar estratégias do IGL.",
    passive_bonus={"aim": 1, "communication": -2},
)

PRODIGY = Trait(
    name="Prodígio",
    description="Talento bruto incomum. Cresce rápido, mas ainda imaturo.",
    passive_bonus={"aim": 2, "consistency": -1, "communication": -1},
)

BORN_IGL = Trait(
    name="IGL Nato",
    description="Liderança natural. Eleva o nível tático da equipe inteira.",
    passive_bonus={"tactics": 2, "communication": 2, "aim": -1},
)

JOKESTER = Trait(
    name="Piadista",
    description="Alivia a pressão com humor. Pode dispersar o foco em momentos críticos.",
    passive_bonus={"communication": 1, "consistency": -1},
)

INCONSISTENT = Trait(
    name="Inconsistente",
    description="Dias geniais alternados com dias terríveis. Imprevisível.",
    passive_bonus={"aim": 1, "consistency": -3},
)

STREAMER = Trait(
    name="Streamer",
    description="Joga para a audiência. Boa moral quando bem, péssima quando mal.",
    passive_bonus={"clutch": 1, "communication": 1, "consistency": -1},
)

ALL_TRAITS: list[Trait] = [
    VETERAN, CLUTCHER, WORKAHOLIC, TILTS_EASILY, HIGH_EGO,
    PRODIGY, BORN_IGL, JOKESTER, INCONSISTENT, STREAMER,
]


def get_trait_by_name(name: str) -> Trait:
    """Return a Trait by name, or VETERAN as default."""
    for t in ALL_TRAITS:
        if t.name == name:
            return t
    return VETERAN
