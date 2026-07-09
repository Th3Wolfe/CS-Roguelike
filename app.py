"""Flask web server — CS Major Manager v4."""
import os
from flask import Flask, jsonify, request, send_from_directory
from models.team import Team
from models.player import PlayerRole
from systems.campaign_manager import CampaignManager
from systems.team_factory import (
    generate_team, build_player_from_data,
    get_candidates_for_role, get_eras,
    generate_share_code, decode_share_code, ROLE_ORDER,
)
from systems.save_system import save_game, load_game, list_saves
from uuid import uuid4
from flask import session
from systems.tactics import (
    CT_TACTICS, T_TACTICS, enemy_choose_tactic, ENEMY_PAUSE_LINES, CT_MATCHUP_MOD
)
import random as _random

app = Flask(__name__)
app.secret_key = "cs_roguelike_v4_2025"
_states: dict = {}


def get_session_state():
    sid = session.get("sid")

    if sid is None:
        sid = str(uuid4())
        session["sid"] = sid

    if sid not in _states:
        _states[sid] = {
            "team": None,
            "campaign": None,
            "pending_events": [],
            "veto": None,          # active VetoState
            "veto_maps": None,     # resolved veto result waiting for play_series
        }

    return _states[sid]


def get_game():
    state = get_session_state()
    return state["team"], state["campaign"]


def set_game(team, campaign):
    state = get_session_state()
    state["team"] = team
    state["campaign"] = campaign
    state["pending_events"] = []


@app.route("/")
def index():
    return send_from_directory("ui", "index.html")

@app.route("/ui/<path:f>")
def ui_files(f):
    return send_from_directory("ui", f)


# ── Música — lista as faixas de cada pasta de contexto ──────────────────────
MUSIC_CONTEXTS = ["frontend", "hub", "match"]
MUSIC_EXTS = (".mp3", ".ogg", ".wav", ".m4a")

@app.route("/api/music_tracks", methods=["GET"])
def music_tracks():
    base = os.path.join(app.root_path, "ui", "music")
    result = {}
    for ctx in MUSIC_CONTEXTS:
        folder = os.path.join(base, ctx)
        files = []
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                if name.lower().endswith(MUSIC_EXTS):
                    files.append(f"/ui/music/{ctx}/{name}")
        result[ctx] = files
    return jsonify({"ok": True, "tracks": result})


# ── Eras & Draft ───────────────────────────────────────────────────────────────

@app.route("/api/eras", methods=["GET"])
def eras():
    return jsonify({"ok": True, "eras": get_eras()})


@app.route("/api/draft_team", methods=["POST"])
def draft_team():
    """Return a random real team from the era for the draft screen."""
    data   = request.get_json(silent=True) or {}
    era_id = data.get("era_id", "2023")
    exclude = data.get("exclude_teams", [])
    from systems.team_factory import get_random_team_for_era, enrich_team_players
    team = get_random_team_for_era(era_id, exclude_team_names=exclude)
    if not team:
        return jsonify({"ok": False, "error": "Sem times disponíveis"}), 404
    enriched = enrich_team_players(team)
    return jsonify({"ok": True, "team": {"name": team["name"], "players": enriched}})


@app.route("/api/draft_candidates", methods=["POST"])
def draft_candidates():
    data    = request.get_json(silent=True) or {}
    era_id  = data.get("era_id", "2023")
    role_s  = data.get("role", PlayerRole.IGL.value)
    exclude = data.get("exclude", [])
    try:    role = PlayerRole(role_s)
    except: return jsonify({"ok": False, "error": f"Role inválido: {role_s}"}), 400
    cands = get_candidates_for_role(role, era_id, exclude, n=5)
    return jsonify({"ok": True, "role": role.value, "candidates": cands})


# ── Game ───────────────────────────────────────────────────────────────────────

@app.route("/api/new_game", methods=["POST"])
def new_game():
    data           = request.get_json(silent=True) or {}
    team_name      = (data.get("team_name") or "").strip() or None
    player_picks   = data.get("player_picks")
    events_enabled = data.get("events_enabled", False)
    era_id         = data.get("era_id", "2023")
    full_maps      = data.get("full_maps", [])   # 2 full-proficiency maps
    half_maps      = data.get("half_maps", [])   # 3 half-proficiency maps

    team     = generate_team(team_name, player_picks)
    team.full_maps = full_maps
    team.half_maps = half_maps

    campaign = CampaignManager(team, events_enabled=events_enabled, era_id=era_id)
    set_game(team, campaign)
    code = generate_share_code(team)
    return jsonify({"ok":True, "team":team.to_dict(), "campaign":campaign.state.to_dict(),
                    "team_score": round(team.team_score(), 2),
                    "share_code": code,
                    "bracket": campaign.get_bracket_state()})


@app.route("/api/map_pool", methods=["GET"])
def map_pool():
    """Return the CS2 active duty map pool."""
    from models.map_config import CS2_MAP_POOL, MAP_CT_BIAS
    return jsonify({"ok": True, "maps": CS2_MAP_POOL, "ct_bias": MAP_CT_BIAS})


@app.route("/api/set_map_proficiency", methods=["POST"])
def set_map_proficiency():
    """Set team's full/half proficiency maps (called after draft, before first series)."""
    team, campaign = get_game()
    if not team:
        return jsonify({"ok": False, "error": "Sem jogo"}), 404
    data      = request.get_json(silent=True) or {}
    full_maps = data.get("full_maps", [])
    half_maps = data.get("half_maps", [])
    from models.map_config import CS2_MAP_POOL
    # Validate
    if len(full_maps) != 2 or len(half_maps) != 3:
        return jsonify({"ok": False, "error": "Escolha exatamente 2 mapas completos e 3 meios"}), 400
    all_chosen = set(full_maps) | set(half_maps)
    if len(all_chosen) != 5 or not all_chosen.issubset(set(CS2_MAP_POOL)):
        return jsonify({"ok": False, "error": "Mapas inválidos"}), 400
    team.full_maps = full_maps
    team.half_maps = half_maps
    return jsonify({"ok": True, "full_maps": full_maps, "half_maps": half_maps})


@app.route("/api/start_veto", methods=["POST"])
def start_veto():
    """Start a map veto for the next series."""
    team, campaign = get_game()
    if not team:
        return jsonify({"ok": False, "error": "Sem jogo"}), 404

    from systems.veto_engine import VetoState
    # Get the pre-paired opponent from the bracket/pending pairings
    opponent = campaign._get_paired_opponent(campaign.state.stage.value) \
               if campaign.state.stage.value in ("stage1","stage2") \
               else campaign._get_playoff_opponent(campaign.state.stage.value)

    # Look up the opponent's persistent map profile from their NpcTeam entry
    opp_npc = next((t for t in campaign.npc_teams if t.name == opponent.name), None)
    opp_profile = opp_npc.get_or_create_map_profile() if opp_npc else None

    state = get_session_state()
    veto = VetoState(
        player_full_maps=team.full_maps,
        player_half_maps=team.half_maps,
        opponent_name=opponent.name,
        opponent_strength=opponent.strength,
        opponent_profile=opp_profile,
    )
    # Auto-advance if opponent goes first
    init_result = veto._maybe_advance_opponent() if not veto.player_goes_first else {"events": [], "state": veto.to_dict()}

    state["veto"]      = veto
    state["veto_maps"] = None
    return jsonify({
        "ok":             True,
        "veto":           veto.to_dict(),
        "opponent_name":  opponent.name,
        "auto_events":    init_result.get("events", []),
        "coin_flip_won":  veto.player_goes_first,
        "opp_profile":    opp_profile,   # expose to UI so player can see opponent tendencies
    })


@app.route("/api/veto_action", methods=["POST"])
def veto_action():
    """Process a player veto action: ban, pick, or side choice."""
    team, campaign = get_game()
    state = get_session_state()
    veto = state.get("veto")
    if not veto:
        return jsonify({"ok": False, "error": "Nenhum veto ativo"}), 400

    data   = request.get_json(silent=True) or {}
    action = data.get("action")  # "ban" | "pick" | "side"
    value  = data.get("value")   # map name or "ct"/"t"

    try:
        if action == "ban":
            result = veto.player_ban(value)
        elif action == "pick":
            result = veto.player_pick(value)
        elif action == "side":
            result = veto.player_choose_side(value)
        else:
            return jsonify({"ok": False, "error": f"Ação desconhecida: {action}"}), 400
    except (AssertionError, ValueError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # If pending_side_for == "opponent", auto-resolve it
    if veto.needs_side_choice() and veto.pending_side_for == "opponent":
        opp_result = veto.opponent_choose_side()
        result.setdefault("events", []).extend(opp_result.get("events", []))

    # If veto is done, store the maps for play_series
    if veto.done:
        state["veto_maps"] = veto.build_veto_maps()

    return jsonify({
        "ok":    True,
        "veto":  veto.to_dict(),
        "events": result.get("events", []),
        "done":  veto.done,
        "veto_maps": state.get("veto_maps"),
    })




@app.route("/api/state", methods=["GET"])
def get_state():
    team, campaign = get_game()
    if not team:
        return jsonify({"ok": False, "error": "Sem jogo"}), 404
    return jsonify({
        "ok": True, "team": team.to_dict(), "campaign": campaign.state.to_dict(),
        "stage_label": campaign.state.current_stage_label(),
        "team_score":  round(team.team_score(), 2),
        "is_finished": campaign.state.is_finished(),
        "share_code":  generate_share_code(team),
        "bracket":     campaign.get_bracket_state(),
    })


@app.route("/api/get_events", methods=["GET"])
def get_events():
    team, campaign = get_game()
    if not team:
        return jsonify({"ok": False, "error": "Sem jogo"}), 404
    if campaign.state.is_finished() or not campaign.events_enabled:
        return jsonify({"ok": True, "events": []})
    events = campaign.get_pending_events()
    get_session_state()["pending_events"] = events
    return jsonify({"ok": True, "events": [e.to_dict() for e in events]})


@app.route("/api/apply_choice", methods=["POST"])
def apply_choice():
    team, campaign = get_game()
    if not team: return jsonify({"ok": False, "error": "Sem jogo"}), 404
    data         = request.get_json(silent=True) or {}
    event_index  = data.get("event_index", 0)
    choice_index = data.get("choice_index", 0)
    pending = get_session_state()["pending_events"]
    if event_index >= len(pending):
        return jsonify({"ok": False, "error": "Evento inválido"}), 400
    event = pending[event_index]
    if choice_index >= len(event.choices):
        return jsonify({"ok": False, "error": "Escolha inválida"}), 400
    messages = campaign.apply_event_choice(event, choice_index)
    return jsonify({"ok": True, "messages": messages, "team": team.to_dict()})


@app.route("/api/play_series", methods=["POST"])
def play_series():
    team, campaign = get_game()
    if not team:     return jsonify({"ok": False, "error": "Sem jogo"}), 404
    if campaign.state.is_finished():
        return jsonify({"ok": False, "error": "Campanha finalizada"}), 400

    state     = get_session_state()
    veto_maps = state.pop("veto_maps", None)   # consume the veto result
    state["veto"] = None                        # clear active veto

    # Tactics from the request body — JSON keys are always strings, normalize to int
    data = request.get_json(silent=True) or {}
    raw_tactics = data.get("tactics") or {}
    tactics = {int(k): v for k, v in raw_tactics.items()} if raw_tactics else None

    result = campaign.play_series(veto_maps=veto_maps, tactics=tactics)
    return jsonify({
        "ok": True,
        "result": {
            "won":               result["won"],
            "description":       result["description"],
            "opponent_name":     result["opponent"].name,
            "opponent_strength": result["opponent"].strength,
            "team_score":        result["team_score"],
            "opp_score":         result["opp_score"],
            "win_probability":   round(result["win_probability"], 3),
            "series_detail":     result["series_detail"],
            "stage_label":       campaign.state.current_stage_label(),
            "stage_mvp":         result.get("stage_mvp"),
        },
        "campaign":   campaign.state.to_dict(),
        "team":       team.to_dict(),
        "team_score": round(team.team_score(), 2),
        "share_code": generate_share_code(team),
        "bracket":    campaign.get_bracket_state(),
    })


@app.route("/api/play_map", methods=["POST"])
def play_map():
    """
    Resolve UM mapa da série por vez, em vez da série inteira de uma tacada
    (como /api/play_series faz). Existe por dois motivos:

    1. Pause Técnico: o front chama isso mapa a mapa, e entre uma chamada e
       outra o jogador pode pausar e trocar de tática — a próxima chamada já
       usa a tática nova.
    2. IA reativa de verdade: a tática do ADVERSÁRIO é decidida AQUI, no
       momento da chamada, usando o que o jogador acabou de escolher pra
       esse mapa e o resultado do mapa anterior — não é mais sorteada sem
       contexto antes da partida começar (ver enemy_choose_tactic).

    O estado da campanha (histórico, avanço de fase, moral dos jogadores...)
    só é gravado de verdade em /api/finish_series, no fim da série. Enquanto
    isso, o progresso fica só na sessão (state["match_progress"] e o objeto
    Opponent em state["_match_opponent"], que não precisa ser serializável
    porque nunca sai do processo Python).
    """
    team, campaign = get_game()
    if not team:     return jsonify({"ok": False, "error": "Sem jogo"}), 404
    if campaign.state.is_finished():
        return jsonify({"ok": False, "error": "Campanha finalizada"}), 400

    from systems.match_resolver import _simulate_map
    from systems.tactics import enemy_choose_tactic

    state = get_session_state()
    data  = request.get_json(silent=True) or {}
    map_index   = data.get("map_index", 0)
    raw_tactics = data.get("tactics") or {}

    progress = state.get("match_progress")
    if progress is None or map_index == 0:
        veto_maps = state.pop("veto_maps", None) or []
        state["veto"] = None
        opponent, stage_pre, ts, os_ = campaign.prepare_match()
        progress = {
            "veto_maps": veto_maps,
            "stage_pre": stage_pre,
            "ts": ts, "os": os_,
            "maps": [],
        }
        state["match_progress"]  = progress
        state["_match_opponent"] = opponent

    veto_maps = progress["veto_maps"]
    if map_index >= len(veto_maps):
        return jsonify({"ok": False, "error": "Índice de mapa inválido"}), 400

    tw = sum(1 for m in progress["maps"] if m["winner"] == "team")
    ow = sum(1 for m in progress["maps"] if m["winner"] == "opponent")
    if tw == 2 or ow == 2:
        return jsonify({"ok": False, "error": "Série já decidida"}), 400

    entry = veto_maps[map_index]
    team_side_h1 = entry.get("team_side", "ct")
    team_side_h2 = "t" if team_side_h1 == "ct" else "ct"
    team_tactic_h1 = raw_tactics.get("team_h1")
    team_tactic_h2 = raw_tactics.get("team_h2")

    # A IA reage de verdade agora: usa a tática que você ACABOU de escolher
    # pra esse mapa (não uma pré-geração cega antes de saber o que você
    # jogaria) e o resultado do ÚLTIMO mapa da série (se houver) — quanto
    # mais avançada a fase, maior a chance dela te contra-atacar de propósito
    # em vez de escolher à toa (ver enemy_choose_tactic em systems/tactics.py).
    prev_result = None
    if progress["maps"]:
        prev_result = "win" if progress["maps"][-1]["winner"] == "opponent" else "loss"
    enemy_side_h1 = "t" if team_side_h1 == "ct" else "ct"
    enemy_side_h2 = team_side_h1
    enemy_tactic_h1 = enemy_choose_tactic(enemy_side_h1, progress["stage_pre"], team_tactic_h1, prev_result)
    enemy_tactic_h2 = enemy_choose_tactic(enemy_side_h2, progress["stage_pre"], team_tactic_h2, prev_result)

    result = _simulate_map(
        progress["ts"], progress["os"],
        map_name           = entry["map"],
        team_proficiency   = entry.get("proficiency", "half"),
        team_start_side     = team_side_h1,
        team_tactic_h1      = team_tactic_h1,
        team_tactic_h2      = team_tactic_h2,
        enemy_tactic_h1     = enemy_tactic_h1,
        enemy_tactic_h2     = enemy_tactic_h2,
    )
    progress["maps"].append(result.to_dict())

    tw = sum(1 for m in progress["maps"] if m["winner"] == "team")
    ow = sum(1 for m in progress["maps"] if m["winner"] == "opponent")

    return jsonify({
        "ok":                True,
        "map_result":        result.to_dict(),
        "series_done":       tw == 2 or ow == 2,
        "team_maps_won":     tw,
        "opponent_maps_won": ow,
    })


@app.route("/api/finish_series", methods=["POST"])
def finish_series():
    """Fecha uma série iniciada via /api/play_map: monta a SeriesDetail a
    partir dos mapas já resolvidos e só AGORA grava tudo no estado da
    campanha (mesma lógica de commit do /api/play_series antigo, via
    CampaignManager._finalize_series)."""
    team, campaign = get_game()
    if not team:     return jsonify({"ok": False, "error": "Sem jogo"}), 404

    from systems.match_resolver import (
        SeriesDetail, MapResult, score_to_win_probability,
        _simulate_player_stats, _simulate_opponent_stats_real,
        _simulate_opponent_player_stats,
    )

    state    = get_session_state()
    progress = state.pop("match_progress", None)
    opponent = state.pop("_match_opponent", None)
    if not progress or opponent is None:
        return jsonify({"ok": False, "error": "Nenhuma partida em andamento"}), 400
    if not progress["maps"]:
        return jsonify({"ok": False, "error": "Nenhum mapa foi jogado ainda"}), 400

    detail = SeriesDetail(
        team_strength     = progress["ts"],
        opponent_strength = progress["os"],
        win_probability   = score_to_win_probability(progress["ts"], progress["os"]),
    )
    detail.maps              = [MapResult(**m) for m in progress["maps"]]
    detail.team_maps_won     = sum(1 for m in detail.maps if m.winner == "team")
    detail.opponent_maps_won = sum(1 for m in detail.maps if m.winner == "opponent")
    detail.team_won          = detail.team_maps_won > detail.opponent_maps_won
    detail.player_stats      = _simulate_player_stats(team.players, detail.maps)
    if opponent.players:
        detail.opponent_player_stats = _simulate_opponent_stats_real(opponent.players, detail.maps)
    else:
        detail.opponent_player_stats = _simulate_opponent_player_stats(opponent.name, opponent.strength, detail.maps)

    result = campaign._finalize_series(detail, opponent, progress["stage_pre"])
    return jsonify({
        "ok": True,
        "result": {
            "won":               result["won"],
            "description":       result["description"],
            "opponent_name":     result["opponent"].name,
            "opponent_strength": result["opponent"].strength,
            "team_score":        result["team_score"],
            "opp_score":         result["opp_score"],
            "win_probability":   round(result["win_probability"], 3),
            "series_detail":     result["series_detail"],
            "stage_label":       campaign.state.current_stage_label(),
            "stage_mvp":         result.get("stage_mvp"),
        },
        "campaign":   campaign.state.to_dict(),
        "team":       team.to_dict(),
        "team_score": round(team.team_score(), 2),
        "share_code": generate_share_code(team),
        "bracket":    campaign.get_bracket_state(),
    })


@app.route("/api/tactics_info", methods=["GET"])
def tactics_info():
    """Retorna as táticas disponíveis, os mapas do veto e a matriz de
    contra-ataque (pra virar informação de jogo real, não só flavor text).
    A tática do ADVERSÁRIO não é mais pré-gerada/exposta aqui — ela só é
    decidida no momento de /api/play_map, reagindo de verdade ao que o
    jogador escolheu e ao resultado do mapa anterior (ver enemy_choose_tactic
    em systems/tactics.py, que existia mas nunca era chamada com contexto
    real antes desta correção)."""
    _, campaign = get_game()
    stage = campaign.state.stage.value if campaign else "stage1"
    state = get_session_state()
    veto_maps = state.get("veto_maps") or []

    STAGE_AI_HINT = {
        "stage1":        "Fase inicial — o adversário ainda não tem padrão, as escolhas dele parecem soltas.",
        "stage2":        "A essa altura, o adversário já reage ao que deu errado pra ele — se perder, tende a tentar te contra-atacar.",
        "playoffs_qf":   "Playoffs: adversário estuda suas rodadas anteriores e contra-ataca com frequência.",
        "playoffs_sf":   "Semifinal: um dos times mais preparados do torneio — espera contra-ataques constantes.",
        "playoffs_final": "Grande Final: o adversário vai tentar te ler o tempo todo. Cuidado com previsibilidade.",
    }

    matchups = [
        {"ct": ct, "t": t, "mod": mod}
        for (ct, t), mod in CT_MATCHUP_MOD.items()
    ]

    return jsonify({
        "ok":               True,
        "ct_tactics":       CT_TACTICS,
        "t_tactics":        T_TACTICS,
        "stage":            stage,
        "ai_hint":          STAGE_AI_HINT.get(stage, ""),
        "veto_maps":        [{"map": v["map"], "team_side": v.get("team_side", "ct")} for v in veto_maps],
        "matchups":         matchups,
        "enemy_pause_lines": ENEMY_PAUSE_LINES,
    })




@app.route("/api/history", methods=["GET"])
def get_history():
    team, campaign = get_game()
    if not team: return jsonify({"ok": False, "error": "Sem jogo"}), 404
    return jsonify({"ok": True, "history": [h.to_dict() for h in campaign.state.history]})


@app.route("/api/save", methods=["POST"])
def save():
    team, campaign = get_game()
    if not team: return jsonify({"ok": False, "error": "Sem jogo"}), 404
    filename = save_game(team, campaign)
    return jsonify({"ok": True, "filename": filename})


@app.route("/api/saves", methods=["GET"])
def saves_list():
    return jsonify({"ok": True, "saves": list_saves()})


@app.route("/api/load", methods=["POST"])
def load():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename","")
    if not filename: return jsonify({"ok": False, "error": "Filename obrigatório"}), 400
    try:
        team, campaign_data = load_game(filename)
        campaign = CampaignManager(team)
        campaign.load_from_dict(campaign_data)
        set_game(team, campaign)
        return jsonify({"ok": True, "team": team.to_dict(), "campaign": campaign.state.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/share_decode", methods=["POST"])
def share_decode():
    data = request.get_json(silent=True) or {}
    code = data.get("code","")
    decoded = decode_share_code(code)
    if not decoded: return jsonify({"ok": False, "error": "Código inválido"}), 400
    return jsonify({"ok": True, "team_data": decoded})


if __name__ == "__main__":
    os.makedirs("saves", exist_ok=True)
    print("🎮 CS Major Manager v4 → http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
