"""Factory: draft pool by era+team, team generation, synergy, opponent rosters."""
import json, os, random, base64
from models.player import Player, PlayerAttributes, PlayerStatus, PlayerRole
from models.team import Team
from models.traits import ALL_TRAITS, get_trait_by_name

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "players_database.json")
_DB: dict = {}

TEAM_NAMES = [
    "FURIA","Loud","Imperial","paiN","MIBR","RED Canids","Sharks","BOOM",
    "Natus Vincere","G2","FaZe","Astralis","Vitality","Team Spirit","Cloud9",
    "Heroic","ENCE","Complexity","BIG","Mouz",
]

ROLE_ORDER = [PlayerRole.IGL, PlayerRole.AWP, PlayerRole.ENTRY, PlayerRole.SUPPORT, PlayerRole.LURK]

ROLE_WEIGHTS: dict[PlayerRole, dict[str, float]] = {
    PlayerRole.ENTRY:   {"kpr":3,"impact":3,"rating":2,"adr":1,"kast":1},
    PlayerRole.AWP:     {"rating":3,"adr":3,"impact":2,"kpr":1,"kast":1},
    PlayerRole.LURK:    {"kpr":3,"kast":2,"rating":2,"impact":2,"adr":1},
    PlayerRole.SUPPORT: {"kast":4,"rating":2,"impact":1,"kpr":1,"adr":2},
    PlayerRole.IGL:     {"kast":3,"impact":3,"rating":2,"kpr":1,"adr":1},
}


def _load_db() -> dict:
    global _DB
    if _DB:
        return _DB
    try:
        with open(_DB_PATH, "r", encoding="utf-8") as f:
            _DB = json.load(f)
    except Exception:
        _DB = {"eras": []}
    return _DB


def get_eras() -> list[dict]:
    db = _load_db()
    return [{"id": e["id"], "label": e["label"], "description": e["description"]}
            for e in db.get("eras", [])]


def get_teams_for_era(era_id: str) -> list[dict]:
    """Return all real teams for a given era, each with their 5 players."""
    db = _load_db()
    for era in db.get("eras", []):
        if era["id"] == era_id:
            return era.get("teams", [])
    return []


def get_random_team_for_era(era_id: str, exclude_team_names: list[str] = None) -> dict | None:
    """Pick a random real team from the era, excluding already-used teams."""
    teams = get_teams_for_era(era_id)
    exclude = exclude_team_names or []
    available = [t for t in teams if t["name"] not in exclude]
    if not available:
        available = teams  # fallback: repeat if all used
    return random.choice(available) if available else None


def _enrich(p: dict, role: PlayerRole) -> dict:
    """Add small jitter to stats and resolve role from role_hint."""
    jitter = lambda v: round(max(1.0, min(10.0, v + random.uniform(-0.3, 0.3))), 2)
    return {
        "name":      p["name"],
        "nickname":  p["nickname"],
        "era":       p.get("era", "?"),
        "country":   p.get("country", "??"),
        "role":      role.value,
        "role_hint": p.get("role_hint", role.value),
        "attributes": {k: jitter(p[k]) for k in ("rating","kast","impact","adr","kpr")},
        "trait":     p.get("trait", "Veterano"),
    }


def _role_from_hint(hint: str) -> PlayerRole:
    mapping = {
        "IGL": PlayerRole.IGL,
        "AWPer": PlayerRole.AWP,
        "Entry Fragger": PlayerRole.ENTRY,
        "Support": PlayerRole.SUPPORT,
        "Lurker": PlayerRole.LURK,
    }
    return mapping.get(hint, PlayerRole.ENTRY)


def enrich_team_players(team: dict) -> list[dict]:
    """Return enriched player dicts for a real team (with role resolved from role_hint)."""
    result = []
    for p in team.get("players", []):
        role = _role_from_hint(p.get("role_hint", "Entry Fragger"))
        result.append(_enrich(p, role))
    return result


def get_candidates_for_role(role: PlayerRole, era_id: str,
                            exclude_nicknames: list[str], n: int = 5) -> list[dict]:
    """Legacy: return n candidates for role from a specific era (flat pool)."""
    db = _load_db()
    all_players: list[dict] = []
    for era in db.get("eras", []):
        if era["id"] == era_id:
            for team in era.get("teams", []):
                all_players.extend(team.get("players", []))
            all_players.extend(era.get("players", []))
            break

    if not all_players:
        return _random_candidates(role, n)

    available = [p for p in all_players if p["nickname"] not in exclude_nicknames]
    role_match = [p for p in available if p.get("role_hint", "") == role.value]
    pool = role_match if len(role_match) >= n else available

    if not pool:
        return _random_candidates(role, n)

    scored = sorted(pool, key=lambda p: _role_score(p, role), reverse=True)
    top_cut = max(n * 2, len(scored) // 2)
    selected = random.sample(scored[:top_cut], min(n, len(scored[:top_cut])))
    return [_enrich(p, role) for p in selected]


def _role_score(p: dict, role: PlayerRole) -> float:
    w = ROLE_WEIGHTS[role]
    total_w = sum(w.values())
    return sum(p.get(stat, 5.0) * weight for stat, weight in w.items()) / total_w


def _random_candidates(role: PlayerRole, n: int) -> list[dict]:
    names = ["ProPlayer","StarAim","TactBrain","FlashGod","SilentKill"]
    return [{
        "name": names[i%len(names)], "nickname": names[i%len(names)],
        "era": "?", "country": "BR", "role": role.value,
        "attributes": {k: round(random.uniform(5,9),2) for k in ("rating","kast","impact","adr","kpr")},
        "trait": random.choice([t.name for t in ALL_TRAITS]),
    } for i in range(n)]


def build_player_from_data(data: dict, role: PlayerRole | None = None) -> Player:
    role = role or PlayerRole(data.get("role", PlayerRole.ENTRY.value))
    a = data.get("attributes", {})
    attrs = PlayerAttributes(**{k: a.get(k, 5.0) for k in ("rating","kast","impact","adr","kpr")})
    status = PlayerStatus(
        morale=random.uniform(-0.5, 1.5), form=random.uniform(-0.5, 0.5),
        physical=random.uniform(80.0, 100.0), mental=random.uniform(80.0, 100.0),
    )
    return Player(
        name=data.get("name", data.get("nickname", "?")),
        nickname=data.get("nickname", "?"),
        era=data.get("era", "?"),
        country=data.get("country", "??"),
        role=role,
        attributes=attrs,
        status=status,
        trait=get_trait_by_name(data.get("trait", "Veterano")),
    )


def generate_team(team_name: str | None = None, player_picks: list[dict] | None = None) -> Team:
    if team_name is None:
        team_name = random.choice(TEAM_NAMES)
    if player_picks and len(player_picks) == 5:
        players = [build_player_from_data(p, PlayerRole(p.get("role", PlayerRole.ENTRY.value)))
                   for p in player_picks]
    else:
        db = _load_db()
        era = random.choice(db["eras"]) if db.get("eras") else None
        era_id = era["id"] if era else "2023"
        players, used = [], []
        for role in ROLE_ORDER:
            cands = get_candidates_for_role(role, era_id, used, 5)
            pick = random.choice(cands)
            players.append(build_player_from_data(pick, role))
            used.append(pick["nickname"])
    synergy = _calc_synergy(players)
    return Team(name=team_name, players=players, synergy=round(synergy, 1))


def build_opponent_team(era_id: str, exclude_team_names: list[str] = None) -> dict | None:
    """
    Pick a real team from the era to use as opponent with real player stats.
    Returns dict with name, players (enriched), strength.
    """
    team = get_random_team_for_era(era_id, exclude_team_names)
    if not team:
        return None
    enriched = enrich_team_players(team)
    # Derive team strength from average rating
    avg_rating = sum(p["attributes"]["rating"] for p in enriched) / len(enriched)
    strength = round(avg_rating * 0.65, 2)  # scale to match opponent range ~5-7
    return {
        "name":     team["name"],
        "players":  enriched,
        "strength": strength,
        "country":  team.get("country", "?"),
    }


def generate_share_code(team: Team) -> str:
    data = {
        "n": team.name,
        "s": round(team.synergy, 1),
        "p": [{"k": p.nickname, "e": p.era, "r": p.role.value[0],
               "rtg": round(p.attributes.rating, 1)} for p in team.players],
    }
    raw = json.dumps(data, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_share_code(code: str) -> dict | None:
    try:
        raw = base64.urlsafe_b64decode(code.encode()).decode()
        return json.loads(raw)
    except Exception:
        return None


def _calc_synergy(players: list[Player]) -> float:
    synergy = random.uniform(-1.5, 2.0)
    roles   = [p.role for p in players]
    traits  = [p.trait.name for p in players]
    if len(set(roles)) == 5:        synergy += 1.5
    if PlayerRole.IGL in roles:     synergy += 1.0
    synergy -= traits.count("Ego Elevado") * 1.0
    synergy += traits.count("IGL Nato")    * 0.8
    synergy += traits.count("Veterano")    * 0.4
    synergy -= traits.count("Tilta Fácil") * 0.5
    synergy -= traits.count("Inconsistente") * 0.4
    return max(-5.0, min(5.0, synergy))
