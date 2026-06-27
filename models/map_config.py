"""CS2 map pool configuration: side bias, proficiency tiers.

Map pool and CT-side win rates updated to reflect the 2026 active duty pool
(Premier Season 4, January 2026 — Train removed, Anubis returned).

CT bias values based on pro-play data from HLTV / Abios / ESEA 2025-2026:
- Anubis remains the most T-sided map in the pool (T wins ~55.5% of rounds).
- Overpass is the most CT-sided (CT wins ~55%).
- Nuke is CT-sided in Premier (~55%) but closer to ~53% in pro tournament play.
- Mirage and Inferno both lean slightly CT (~52%).
- Dust2 and Ancient are near-balanced (~50-51% CT).
Values here target pro-level balance (not Premier pubs which skew more extreme).
"""

# Active duty pool as of June 2026
CS2_MAP_POOL = [
    "Mirage", "Inferno", "Dust2", "Nuke",
    "Ancient", "Anubis", "Overpass",
]

# CT win rate per regulation half (first 12 rounds) — pro-play 2025-2026.
# A value of 0.54 means CTs win ~54% of rounds when they start CT side.
MAP_CT_BIAS: dict[str, float] = {
    "Mirage":   0.52,   # slightly CT-sided; strong AWP positions, quick rotations
    "Inferno":  0.52,   # slightly CT-sided; Banana choke, tight Apartments
    "Dust2":    0.51,   # near-balanced; slight CT edge on Mid/Long early
    "Nuke":     0.53,   # CT-sided in pro play; rotations, verticality, noise cues
    "Ancient":  0.50,   # balanced; cave/mid control rewards both sides equally
    "Anubis":   0.445,  # strongly T-sided; open sites, multiple rush paths
                        # (post-Jan 2026 rework, Bridge geometry changed, but
                        #  T advantage still ~55.5% per HLTV/ESEA Season 52 data)
    "Overpass": 0.55,   # strongly CT-sided; Bathroom/Monster angles, long rotations
}

# Proficiency tiers
PROF_FULL = "full"   # 2 maps chosen by player → +bonus
PROF_HALF = "half"   # 3 maps chosen            → neutral
PROF_NONE = "none"   # remaining 2              → penalty

# Win-rate modifiers applied to per-round win probability
PROF_MODIFIER: dict[str, float] = {
    PROF_FULL:  +0.06,   # full: +6pp (reduced from +8pp — was too cheap a guarantee)
    PROF_HALF:  +0.00,   # half: neutral
    PROF_NONE:  -0.10,   # none: -10pp (unfamiliar map, disorganised executes)
}

def get_proficiency(map_name: str, full_maps: list[str], half_maps: list[str]) -> str:
    if map_name in full_maps:
        return PROF_FULL
    if map_name in half_maps:
        return PROF_HALF
    return PROF_NONE
