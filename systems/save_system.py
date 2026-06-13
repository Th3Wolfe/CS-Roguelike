"""Save and load game state to/from JSON files."""
import json
import os
from datetime import datetime
from models.team import Team
from systems.campaign_manager import CampaignManager

SAVES_DIR = os.path.join(os.path.dirname(__file__), "..", "saves")


def ensure_saves_dir() -> None:
    """Ensure the saves directory exists."""
    os.makedirs(SAVES_DIR, exist_ok=True)


def list_saves() -> list[str]:
    """Return a list of save file names."""
    ensure_saves_dir()
    return [f for f in os.listdir(SAVES_DIR) if f.endswith(".json")]


def save_game(team: Team, campaign: CampaignManager, filename: str | None = None) -> str:
    """Save current game state to a JSON file. Returns the save filename."""
    ensure_saves_dir()
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"save_{team.name}_{ts}.json"
    path = os.path.join(SAVES_DIR, filename)
    data = {
        "team": team.to_dict(),
        "campaign": campaign.to_dict(),
        "saved_at": datetime.now().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def load_game(filename: str) -> tuple[Team, dict]:
    """Load game state from a JSON file. Returns (team, campaign_data)."""
    path = os.path.join(SAVES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    team = Team.from_dict(data["team"])
    return team, data["campaign"]
