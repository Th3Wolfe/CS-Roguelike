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
            "pending_events": []
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


# ── Eras & Draft ───────────────────────────────────────────────────────────────

@app.route("/api/eras", methods=["GET"])
def eras():
    return jsonify({"ok": True, "eras": get_eras()})


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
    data         = request.get_json(silent=True) or {}
    team_name    = data.get("team_name","").strip() or None
    player_picks = data.get("player_picks")
    events_enabled = data.get("events_enabled", False)   # disabled by default

    team     = generate_team(team_name, player_picks)
    campaign = CampaignManager(team, events_enabled=events_enabled)
    set_game(team, campaign)
    code = generate_share_code(team)
    return jsonify({"ok":True, "team":team.to_dict(), "campaign":campaign.state.to_dict(),
                    "share_code": code})


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
    result = campaign.play_series()
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
        "campaign": campaign.state.to_dict(),
        "team":     team.to_dict(),
        "team_score": round(team.team_score(), 2),
        "share_code": generate_share_code(team),
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
