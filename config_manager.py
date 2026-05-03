import json
import os
from pathlib import Path

APP_NAME = "MiniVault 3.1"
local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
CONFIG_DIR = Path(local_appdata) / "Programs" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"


def init_config():
    """Tworzy folder aplikacji, jeśli nie istnieje."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_settings():
    """Wczytuje ustawienia lub zwraca domyślne."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"appearance_mode": "Dark", "last_user": ""}


def save_settings(settings):
    """Zapisuje słownik ustawień do pliku."""
    init_config()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")