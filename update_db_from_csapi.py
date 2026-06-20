"""
update_db_from_csapi.py
=======================
Atualiza a era "2025" do players_database.json usando dados ao vivo da
CS API (https://api.csapi.de) — sem chave, gratuita, atualizada diariamente.

USO:
    python update_db_from_csapi.py
    python update_db_from_csapi.py --db caminho/para/players_database.json
    python update_db_from_csapi.py --dry-run   # mostra o que faria, sem salvar
    python update_db_from_csapi.py --debug      # inspeciona a estrutura real da API

O script:
  1. Busca /players/stats (pool global) e /rankings para tier
  2. Para cada time do ranking, busca /teams/{id} para o roster
  3. Cruza roster com o pool de stats por nome de jogador
  4. Converte rating HLTV → escala do jogo (1-10)
  5. Infere role_hint e trait via heurística
  6. Sobrescreve só a era "2025" no JSON

Dependências: apenas stdlib + requests
    pip install requests
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌  'requests' não instalado. Execute: pip install requests")
    sys.exit(1)

# ── Configuração ──────────────────────────────────────────────────────────────

BASE_URL  = "https://api.csapi.de"
TOP_N     = 16      # quantos times do ranking puxar
SLEEP_S   = 0.35    # pausa entre chamadas
MIN_MAPS  = 5       # mínimo de mapas para aceitar stats

DEFAULT_DB = Path(__file__).parent / "CS-Roguelike" / "data" / "players_database.json"

# ── HTTP ──────────────────────────────────────────────────────────────────────

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "cs-roguelike-updater/2.0",
})


def get(path: str, params: dict = None, silent: bool = False) -> dict | list | None:
    url = BASE_URL + path
    try:
        r = session.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        if not silent:
            print(f"  ⚠  HTTP {e.response.status_code} → {url}")
        return None
    except Exception as e:
        if not silent:
            print(f"  ⚠  Erro em {url}: {e}")
        return None


# ── Debug: inspeciona estrutura real da API ───────────────────────────────────

def debug_mode():
    """Imprime a estrutura JSON cru dos principais endpoints para diagnóstico."""
    print("\n🔍  DEBUG — estrutura real da API\n")

    endpoints = [
        ("/counts", None),
        ("/rankings", {"limit": 3}),
        ("/players/stats", {"limit": 3, "min_played": 1}),
        ("/players/stats/raw", {"limit": 2}),
    ]

    for path, params in endpoints:
        print(f"{'─'*60}")
        print(f"GET {path}  params={params}")
        data = get(path, params)
        if data is None:
            print("  (sem resposta)")
            continue
        text = json.dumps(data, indent=2, ensure_ascii=False)
        # Mostra só primeiros 1500 chars para não inundar o terminal
        print(text[:1500])
        if len(text) > 1500:
            print("  ... (truncado)")
        print()

    # Tenta pegar um time e um jogador reais
    print(f"{'─'*60}")
    print("GET /rankings (completo, 1 item)")
    ranking = get("/rankings", {"limit": 1})
    if ranking:
        items = ranking if isinstance(ranking, list) else ranking.get("rankings", [ranking])
        if items:
            first = items[0]
            print(json.dumps(first, indent=2))
            tid = first.get("team_id") or first.get("id")
            if tid:
                print(f"\nGET /teams/{tid}")
                team = get(f"/teams/{tid}")
                print(json.dumps(team, indent=2, ensure_ascii=False)[:2000])

                roster = (team or {}).get("roster", [])
                if roster:
                    pid = roster[0].get("id")
                    if pid:
                        print(f"\nGET /players/{pid}")
                        player = get(f"/players/{pid}")
                        print(json.dumps(player, indent=2, ensure_ascii=False)[:2000])

    sys.exit(0)


# ── Extração de stats (tolerante a várias estruturas) ─────────────────────────

def extract_stats(obj: dict) -> dict:
    """
    Extrai stats de um objeto API, tentando múltiplas estruturas possíveis.
    Retorna dict normalizado com chaves: rating, kast, adr, k, d, swing, maps_played.
    """
    # 1. Campo "stats" aninhado
    nested = obj.get("stats") or {}

    # 2. Campos soltos no nível raiz
    root = {}
    for key in ("rating", "kast", "adr", "k", "d", "swing", "maps_played",
                "kills", "deaths", "maps", "mapsplayed", "maps_count",
                "impact", "hs", "hs_percent"):
        if key in obj:
            root[key] = obj[key]

    # Usa o que tiver mais dados
    stats = nested if len(nested) >= len(root) else root

    # Normaliza aliases de campos
    aliases = {
        "kills":      "k",
        "deaths":     "d",
        "maps":       "maps_played",
        "mapsplayed": "maps_played",
        "maps_count": "maps_played",
        "impact":     "swing",
    }
    for old, new in aliases.items():
        if old in stats and new not in stats:
            stats[new] = stats[old]

    # Calcula swing (k - d) se ausente
    if "swing" not in stats and "k" in stats and "d" in stats:
        try:
            stats["swing"] = float(stats["k"]) - float(stats["d"])
        except (TypeError, ValueError):
            pass

    return stats


# ── Conversão de stats para escala do jogo ────────────────────────────────────

def hltv_to_game(val: float, lo: float, hi: float, glo=1.0, ghi=10.0) -> float:
    """Mapeia [lo, hi] → [glo, ghi], clamping nas bordas."""
    clamped = max(lo, min(hi, val))
    return round(glo + (clamped - lo) / (hi - lo) * (ghi - glo), 2)


def stats_to_attributes(stats: dict) -> dict:
    """
    Converte stats HLTV para atributos na escala 1-10.
    Faixas de referência de pros ativos (top 50 HLTV):
      rating:  0.85 – 1.60
      kast(%): 60   – 88
      adr:     60   – 110
      k/mapa:  12   – 22
      swing:  -2    – 9
    """
    rating = float(stats.get("rating", 1.0))
    kast   = float(stats.get("kast",   72.0))
    adr    = float(stats.get("adr",    75.0))
    k      = float(stats.get("k",      15.0))
    d      = float(stats.get("d",      14.0))
    swing  = float(stats.get("swing",   1.0))

    return {
        "rating": hltv_to_game(rating, 0.85, 1.58),
        "kast":   hltv_to_game(kast,   58.0, 88.0),
        "impact": hltv_to_game(adr,    58.0, 108.0),   # ADR como proxy de impacto
        "adr":    hltv_to_game(adr,    58.0, 108.0),
        "kpr":    hltv_to_game(swing, -2.0,  9.0),     # swing como proxy de kpr
    }


def guess_role(stats: dict) -> str:
    rating = float(stats.get("rating", 1.0))
    kast   = float(stats.get("kast",   72.0))
    adr    = float(stats.get("adr",    75.0))
    k      = float(stats.get("k",      15.0))
    d      = float(stats.get("d",      14.0))
    swing  = k - d

    if kast >= 76 and rating < 1.12 and adr < 78:
        return "IGL"
    if kast >= 78 and adr < 72:
        return "Support"
    if rating >= 1.20 and adr >= 85 and d < 14:
        return "AWPer"
    if adr >= 82 and d >= 14.5:
        return "Entry Fragger"
    if swing >= 2.5 and d < 13.5:
        return "Lurker"
    return "Entry Fragger"


def guess_trait(stats: dict, role: str) -> str:
    rating      = float(stats.get("rating", 1.0))
    kast        = float(stats.get("kast",   72.0))
    maps_played = int(stats.get("maps_played", 20))

    if role == "IGL":        return "IGL Nato"
    if rating >= 1.42:       return "Ego Elevado"
    if rating >= 1.28 and maps_played < 60: return "Prodígio"
    if kast >= 80 and rating >= 1.10:       return "Clutcher"
    if kast >= 78:           return "Workaholic"
    if rating >= 1.15:       return "Veterano"
    if maps_played < 40:     return "Inconsistente"
    return "Piadista"


COUNTRY_MAP = {
    "vitality": "FR", "furia": "BR", "spirit": "RU", "navi": "UA",
    "natus vincere": "UA", "falcons": "SA", "mouz": "DE", "aurora": "TR",
    "mongolz": "MN", "the mongolz": "MN", "parivision": "KZ",
    "g2": "INT", "faze": "INT", "imperial": "BR", "astralis": "DK",
    "heroic": "DK", "big": "DE", "liquid": "US", "cloud9": "US",
    "betboom": "RU", "legacy": "BR", "pain": "BR", "mibr": "BR",
    "9z": "AR", "apogee": "INT", "gamerlegion": "SE",
}


def guess_country(team_name: str) -> str:
    lower = team_name.lower()
    for key, cc in COUNTRY_MAP.items():
        if key in lower:
            return cc
    return "INT"


def guess_tier(rank: int) -> int:
    if rank <= 4:  return 1
    if rank <= 10: return 2
    return 3


# ── Busca de dados ─────────────────────────────────────────────────────────────

def fetch_rankings(top_n: int) -> list[dict]:
    data = get("/rankings")
    if not data:
        return []
    items = data if isinstance(data, list) else data.get("rankings", [])
    result = []
    for i, entry in enumerate(items[:top_n]):
        result.append({
            "id":   entry.get("team_id") or entry.get("id"),
            "name": entry.get("team_name") or entry.get("name", "?"),
            "rank": entry.get("rank", i + 1),
        })
    return result


def fetch_players_stats_pool(limit: int = 300) -> dict[str, dict]:
    """
    Busca /players/stats (pool global) e retorna dict {nome_lower: stats_dict}.
    Esse endpoint agrega os últimos 3 meses e inclui maps_played.
    """
    print("  📥  Buscando pool global de stats (/players/stats)...")
    data = get("/players/stats", params={"limit": limit, "min_played": 1})
    if not data:
        print("  ⚠  /players/stats não retornou dados.")
        return {}

    items = data if isinstance(data, list) else data.get("players", data.get("items", []))
    pool = {}
    for p in items:
        name = (p.get("name") or "").lower().strip()
        if name:
            stats = extract_stats(p)
            stats["_id"] = p.get("id")
            stats["_full_name"] = p.get("full_name") or p.get("name") or name
            stats["_country"] = p.get("country") or "??"
            pool[name] = stats
    print(f"  ✅  Pool: {len(pool)} jogadores com stats.")
    return pool


def fetch_team_roster(team_id: int) -> list[dict]:
    """Retorna lista de {id, name} do roster de um time."""
    data = get(f"/teams/{team_id}")
    if not data:
        return []
    roster = data.get("roster", [])
    return roster


def build_player_entry(nickname: str, stats: dict) -> dict | None:
    """Constrói o dict de jogador para o players_database.json."""
    maps_played = int(stats.get("maps_played", 0))
    if maps_played < MIN_MAPS:
        return None

    attrs   = stats_to_attributes(stats)
    role    = guess_role(stats)
    trait   = guess_trait(stats, role)
    country = (stats.get("_country") or "??")
    if len(country) != 2 or country == "??":
        country = "INT"
    full_name = stats.get("_full_name") or nickname

    return {
        "name":      full_name,
        "nickname":  nickname,
        "country":   country.upper(),
        "role_hint": role,
        "trait":     trait,
        **attrs,
    }


# ── Construção da era 2025 ────────────────────────────────────────────────────

def build_era_2025(top_n: int, verbose: bool = True) -> list[dict]:
    # 1. Pool global de stats (uma única chamada)
    time.sleep(SLEEP_S)
    pool = fetch_players_stats_pool(limit=300)

    if not pool:
        print("❌  Pool de stats vazio. Tentando continuar sem ele...")

    # 2. Rankings
    print(f"\n  📡  Buscando ranking VRS (top {top_n})...")
    time.sleep(SLEEP_S)
    rankings = fetch_rankings(top_n)
    if not rankings:
        print("❌  Não foi possível obter o ranking.")
        return []
    print(f"  ✅  {len(rankings)} times no ranking.\n")

    teams_output = []

    for rank_entry in rankings:
        team_id   = rank_entry["id"]
        team_name = rank_entry["name"]
        rank      = rank_entry["rank"]
        tier      = guess_tier(rank)

        print(f"  #{rank:>2}  {team_name} (tier {tier})")
        time.sleep(SLEEP_S)

        # 3. Roster do time
        roster = fetch_team_roster(team_id)
        if not roster:
            print(f"      ⚠  Roster vazio. Pulando.")
            continue

        players_output = []

        for member in roster:
            nickname = (member.get("name") or "").strip()
            if not nickname:
                continue

            # 4. Busca stats: primeiro no pool, depois endpoint individual
            stats = pool.get(nickname.lower())

            if not stats:
                # Fallback: endpoint individual
                pid = member.get("id")
                if pid:
                    time.sleep(SLEEP_S)
                    pdata = get(f"/players/{pid}", silent=True)
                    if pdata:
                        stats = extract_stats(pdata)
                        stats["_id"] = pid
                        stats["_full_name"] = pdata.get("full_name") or nickname
                        stats["_country"] = pdata.get("country") or "INT"

            if not stats:
                print(f"      ↳ sem stats: {nickname}")
                continue

            maps_played = int(stats.get("maps_played", 0))
            if maps_played < MIN_MAPS:
                print(f"      ↳ skip {nickname} ({maps_played} mapas < {MIN_MAPS})")
                continue

            entry = build_player_entry(nickname, stats)
            if entry:
                players_output.append(entry)
                if verbose:
                    print(f"      ✓ {entry['nickname']:16} {entry['role_hint']:16} "
                          f"rating={entry['rating']:.1f}  maps={maps_played}  trait={entry['trait']}")

        if len(players_output) < 3:
            print(f"      ⚠  Só {len(players_output)} jogador(es) com dados. Pulando {team_name}.\n")
            continue

        teams_output.append({
            "name":    team_name,
            "tier":    tier,
            "country": guess_country(team_name),
            "players": players_output,
        })
        print(f"      → {len(players_output)} jogadores adicionados.\n")

    return teams_output


# ── Salvar no banco ───────────────────────────────────────────────────────────

def update_database(db_path: Path, teams: list[dict], dry_run: bool = False) -> None:
    if not db_path.exists():
        print(f"❌  Arquivo não encontrado: {db_path}")
        sys.exit(1)

    with open(db_path, encoding="utf-8") as f:
        db = json.load(f)

    era_found = False
    for i, era in enumerate(db.get("eras", [])):
        if str(era.get("id")) == "2025":
            db["eras"][i]["teams"] = teams
            db["eras"][i]["label"] = "2025/2026 — CS2 Atual (auto)"
            db["eras"][i]["description"] = (
                f"Dados ao vivo via csapi.de — {len(teams)} times atualizados automaticamente."
            )
            era_found = True
            break

    if not era_found:
        db.setdefault("eras", []).append({
            "id": "2025", "label": "2025/2026 — CS2 Atual (auto)",
            "description": f"Dados via csapi.de — {len(teams)} times.",
            "teams": teams, "players": [],
        })

    if dry_run:
        print("\n🔍  DRY RUN — primeiros 2 times:\n")
        preview = {"eras": [{"id": "2025", "teams": teams[:2]}]}
        print(json.dumps(preview, indent=2, ensure_ascii=False)[:3000])
        print("\n(nenhum arquivo modificado)")
        return

    backup = db_path.with_suffix(".json.bak")
    import shutil
    shutil.copy2(db_path, backup)
    print(f"💾  Backup: {backup}")

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    total_players = sum(len(t["players"]) for t in teams)
    print(f"✅  Banco atualizado: {db_path}")
    print(f"    Era 2025: {len(teams)} times, {total_players} jogadores.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Atualiza players_database.json com dados ao vivo de api.csapi.de"
    )
    parser.add_argument("--db",      type=Path, default=DEFAULT_DB)
    parser.add_argument("--top",     type=int,  default=TOP_N,
                        help=f"Times do ranking a incluir (padrão: {TOP_N})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra resultado sem salvar")
    parser.add_argument("--quiet",   action="store_true",
                        help="Menos output por jogador")
    parser.add_argument("--debug",   action="store_true",
                        help="Inspeciona estrutura real da API e sai")
    args = parser.parse_args()

    if args.debug:
        debug_mode()

    print("=" * 60)
    print("  CS Roguelike — Atualizador via csapi.de  v2")
    print("=" * 60)
    print(f"  DB:      {args.db}")
    print(f"  Top:     {args.top} times  |  Min maps: {MIN_MAPS}")
    print(f"  Dry run: {args.dry_run}")
    print("=" * 60)

    teams = build_era_2025(top_n=args.top, verbose=not args.quiet)

    if not teams:
        print("\n❌  Nenhum time gerado. Rode com --debug para inspecionar a API.")
        sys.exit(1)

    print(f"\n📊  {len(teams)} times prontos.")
    update_database(args.db, teams, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
