"""Match resolution — CS2 MR12 format (first to 13, OT at MR3 blocks)."""
import random
import math
from dataclasses import dataclass, field
from models.team import Team
from models.opponent import Opponent

CS_MAPS = [
    "Mirage", "Inferno", "Dust2", "Overpass", "Nuke",
    "Ancient", "Anubis", "Vertigo", "Train",
]

ROUNDS_TO_WIN      = 13
OT_ROUNDS_WIN      = 4
OT_ROUNDS_PER_SIDE = 3


@dataclass
class PlayerMatchStats:
    nickname:  str
    role:      str
    kills:     int   = 0
    deaths:    int   = 0
    assists:   int   = 0
    adr_total: float = 0.0   # sum of damage over all rounds
    rounds:    int   = 0     # total rounds played in this series

    @property
    def kd(self) -> float:
        return round(self.kills / max(self.deaths, 1), 2)

    @property
    def adr(self) -> float:
        return round(self.adr_total / max(self.rounds, 1), 1)

    @property
    def kpr(self) -> float:
        return round(self.kills / max(self.rounds, 1), 2)

    def to_dict(self) -> dict:
        return {
            "nickname": self.nickname,
            "role":     self.role,
            "kills":    self.kills,
            "deaths":   self.deaths,
            "assists":  self.assists,
            "kd":       self.kd,
            "adr":      self.adr,
            "kpr":      self.kpr,
            "rounds":   self.rounds,
        }


@dataclass
class MapResult:
    map_name:       str
    team_score:     int
    opponent_score: int
    winner:         str   # "team" | "opponent"
    went_ot:        bool  = False


@dataclass
class SeriesDetail:
    maps:               list[MapResult] = field(default_factory=list)
    team_maps_won:      int   = 0
    opponent_maps_won:  int   = 0
    team_won:           bool  = False
    team_strength:      float = 0.0
    opponent_strength:  float = 0.0
    win_probability:    float = 0.5
    player_stats:       list  = field(default_factory=list)   # list[PlayerMatchStats]

    def to_dict(self) -> dict:
        return {
            "maps": [
                {
                    "map_name":       m.map_name,
                    "team_score":     m.team_score,
                    "opponent_score": m.opponent_score,
                    "winner":         m.winner,
                    "went_ot":        m.went_ot,
                }
                for m in self.maps
            ],
            "team_maps_won":     self.team_maps_won,
            "opponent_maps_won": self.opponent_maps_won,
            "team_won":          self.team_won,
            "team_strength":     round(self.team_strength, 2),
            "opponent_strength": round(self.opponent_strength, 2),
            "win_probability":   round(self.win_probability, 3),
            "player_stats":      [s.to_dict() for s in self.player_stats],
        }


def score_to_win_probability(team_score: float, opp_score: float) -> float:
    diff = team_score - opp_score
    raw  = 1.0 / (1.0 + math.exp(-diff * 0.75))
    return max(0.04, min(0.96, raw))


def _simulate_map(ts: float, os_: float) -> MapResult:
    """Simulate a single CS2 map using MR12 rules."""
    noise = random.gauss(0, 0.7)
    p = max(0.12, min(0.88, 1.0 / (1.0 + math.exp(-(ts - os_ + noise) * 0.55))))

    t_r = o_r = 0

    # Regulation — stop immediately at 12-12
    while t_r < ROUNDS_TO_WIN and o_r < ROUNDS_TO_WIN:
        if random.random() < p:
            t_r += 1
        else:
            o_r += 1
        if t_r == 12 and o_r == 12:
            break

    went_ot = False

    # Overtime — repeat MR3 blocks until total scores differ
    if t_r == 12 and o_r == 12:
        went_ot = True
        while True:
            ot_t = ot_o = 0
            while ot_t < OT_ROUNDS_WIN and ot_o < OT_ROUNDS_WIN:
                if random.random() < p:
                    ot_t += 1
                else:
                    ot_o += 1
            t_r += ot_t
            o_r += ot_o
            if t_r != o_r:
                break

    winner = "team" if t_r > o_r else "opponent"
    return MapResult(map_name="", team_score=t_r, opponent_score=o_r,
                     winner=winner, went_ot=went_ot)


def _simulate_player_stats(
    players: list,
    maps: list[MapResult],
) -> list[PlayerMatchStats]:
    """
    Simulate kills round by round for each map.

    Per round:
    - The winning team kills all 5 opponents (guaranteed 5 kills on that side)
    - The losing team also gets some kills before being eliminated (random 0-4)
    - Kills within each team are distributed by weighted kpr attribute
    - Deaths on a round = number of kills the opponent scored that round
    - ADR is simulated per round based on the adr attribute
    """
    stats = [PlayerMatchStats(nickname=p.nickname, role=p.role.value) for p in players]

    for m in maps:
        total_rounds = m.team_score + m.opponent_score

        # Expected total kills per team:
        # winner gets ~2.5 kills/round, loser ~1.2 kills/round
        total_team_kills  = int(round(m.team_score * 2.5 + m.opponent_score * 1.2))
        total_team_deaths = int(round(m.opponent_score * 2.5 + m.team_score * 1.2))

        # Kill share: kpr² amplifies differences between players + proportional noise
        # This means an Entry with kpr=8 gets ~4x the weight of a Support with kpr=4
        kpr_weights = [
            max(0.01, (p.attributes.kpr ** 2) * (1.0 + random.gauss(0, 0.18)))
            for p in players
        ]
        total_kw = sum(kpr_weights)
        shares   = [w / total_kw for w in kpr_weights]

        # Death share: inversely proportional to kpr (fraggier players die less per kill)
        # Also add role noise — entry fraggers die more even with high kpr
        death_weights = [
            max(0.01, (1.0 / max(p.attributes.kpr, 0.5)) * (1.0 + random.gauss(0, 0.15)))
            for p in players
        ]
        total_dw     = sum(death_weights)
        death_shares = [w / total_dw for w in death_weights]

        map_kills  = _alloc(total_team_kills,  shares)
        map_deaths = _alloc(total_team_deaths, death_shares)

        # ADR: use adr attribute scaled to realistic range, with per-map noise
        map_damage = [
            max(0.0, (40.0 + p.attributes.adr * 7.0 + random.gauss(0, 10.0))) * total_rounds
            for p in players
        ]

        for i in range(5):
            assists = max(0, int(map_kills[i] * random.uniform(0.12, 0.22)))
            stats[i].kills     += map_kills[i]
            stats[i].deaths    += map_deaths[i]
            stats[i].assists   += assists
            stats[i].adr_total += map_damage[i]
            stats[i].rounds    += total_rounds

    return stats


def _alloc(total: int, shares: list[float]) -> list[int]:
    """Distribute `total` kills among players by share, keeping the sum exact."""
    raw    = [total * s for s in shares]
    result = [int(x) for x in raw]
    remainder = total - sum(result)
    # Give leftover to players with largest fractional parts
    fracs = sorted(range(len(raw)), key=lambda i: raw[i] - result[i], reverse=True)
    for i in fracs[:remainder]:
        result[i] += 1
    return result


def _simulate_opponent_player_stats(opponent_name: str, opp_strength: float, maps: list[MapResult]) -> list[dict]:
    """
    Generate plausible round-by-round stats for 5 fictional opponent players.
    Opponent won the rounds they won (opponent_score) and lost the rest.
    """
    ROLES = ["IGL", "AWPer", "Entry Fragger", "Support", "Lurker"]
    # Opponent kpr proxy from strength (stronger = higher kpr)
    base_kprs = [max(0.05, 0.55 + opp_strength * 0.04 + random.gauss(0, 0.08)) for _ in range(5)]
    total_kpr = sum(base_kprs)
    shares = [k / total_kpr for k in base_kprs]
    death_weights = [max(0.05, 1.0 / max(k, 0.1)) for k in base_kprs]
    total_dw = sum(death_weights)
    death_shares = [w / total_dw for w in death_weights]

    all_kills  = [0] * 5
    all_deaths = [0] * 5
    all_adr    = [0.0] * 5
    all_rounds = 0

    for m in maps:
        # From the opponent's perspective: they won opp_score rounds
        opp_rounds_won = m.opponent_score
        total_rounds   = m.team_score + m.opponent_score
        all_rounds    += total_rounds

        for _ in range(total_rounds):
            opp_won = random.random() < (opp_rounds_won / max(total_rounds, 1))
            our_kills = random.choices([1,2,3,4,5], weights=[5,25,35,25,10])[0] if opp_won else random.choices([0,1,2,3,4], weights=[20,35,28,12,5])[0]
            our_deaths = random.choices([0,1,2,3,4], weights=[20,35,28,12,5])[0] if opp_won else random.choices([1,2,3,4,5], weights=[5,25,35,25,10])[0]

            rem_k = our_kills
            for i in range(4):
                k = max(0, min(rem_k, round(our_kills * shares[i] + random.gauss(0, 0.4))))
                all_kills[i] += k; rem_k -= k
            all_kills[4] += max(0, rem_k)

            rem_d = our_deaths
            for i in range(4):
                d = max(0, min(rem_d, round(our_deaths * death_shares[i] + random.gauss(0, 0.3))))
                all_deaths[i] += d; rem_d -= d
            all_deaths[4] += max(0, rem_d)

        base_adr = 40.0 + opp_strength * 7.0
        for i in range(5):
            all_adr[i] += (base_adr + random.gauss(0, 12.0)) * total_rounds

    result = []
    for i, role in enumerate(ROLES):
        kd  = round(all_kills[i] / max(all_deaths[i], 1), 2)
        adr = round(all_adr[i] / max(all_rounds, 1), 1)
        kpr_val = round(all_kills[i] / max(all_rounds, 1), 2)
        result.append({
            "nickname":  f"{opponent_name.split()[0]}#{i+1}",
            "team":      opponent_name,
            "role":      role,
            "kills":     all_kills[i],
            "deaths":    all_deaths[i],
            "assists":   max(0, int(all_kills[i] * random.uniform(0.12, 0.22))),
            "kd":        kd,
            "adr":       adr,
            "kpr":       kpr_val,
            "rounds":    all_rounds,
        })
    return result


def resolve_series(team: Team, opponent: Opponent) -> SeriesDetail:
    """Resolve a BO3 series with CS2 MR12 rules, including player kill stats."""
    ts  = round(team.team_score(), 2)
    os_ = round(opponent.total_score(), 2)
    prob = score_to_win_probability(ts, os_)

    maps_pool = random.sample(CS_MAPS, 3)
    detail = SeriesDetail(team_strength=ts, opponent_strength=os_, win_probability=prob)

    for map_name in maps_pool:
        if detail.team_maps_won == 2 or detail.opponent_maps_won == 2:
            break
        result = _simulate_map(ts, os_)
        result.map_name = map_name
        detail.maps.append(result)
        if result.winner == "team":
            detail.team_maps_won += 1
        else:
            detail.opponent_maps_won += 1

    detail.team_won = detail.team_maps_won > detail.opponent_maps_won

    # Simulate player stats for team players
    detail.player_stats = _simulate_player_stats(team.players, detail.maps)

    return detail


def describe_result(detail: SeriesDetail, opponent_name: str) -> str:
    result  = "VITÓRIA" if detail.team_won else "DERROTA"
    ms      = f"{detail.team_maps_won}-{detail.opponent_maps_won}"
    diff    = abs(detail.team_strength - detail.opponent_strength)
    quality = ("muito disputada" if diff < 0.5 else
               "disputada"       if diff < 1.5 else
               "confortável"     if diff < 3   else "dominante")
    pct     = int(detail.win_probability * 100)
    fav     = "favorito" if detail.win_probability > 0.5 else "azarão"
    ot_maps = sum(1 for m in detail.maps if m.went_ot)
    ot_note = f" ({ot_maps} mapa(s) em OT)" if ot_maps else ""
    return (f"{result} {quality} contra {opponent_name} ({ms}){ot_note}. "
            f"Eram {fav} ({pct}% de chance).")
