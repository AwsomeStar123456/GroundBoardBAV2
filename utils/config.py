import json
import os

DEFAULTS = {
    "LOAD_JSON_SUCCESS":0,
    "BUTTON_PIN_SYNC": 14,
    "BUTTON_PIN_AP": 10
}

class Config:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self._data = {}
        self.load()

    def load(self):
        """Load config from file. Create with defaults if missing."""
        try:
            with open(self.filename, "r") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            # File missing or invalid → start with defaults
            self._data = DEFAULTS.copy()
            self.save()

    def save(self):
        """Write current config to disk."""
        with open(self.filename, "w") as f:
            json.dump(self._data, f)

    def get(self, key, default=None):
        """Get a value. Returns default if the key doesn't exist."""
        return self._data.get(key, default)

    def set(self, key, value):
        """Set a value (creates the key if it doesn't exist) and save."""
        self._data[key] = value
        self.save()

    def update(self, values):
        """Set several keys and write once."""
        if not values:
            return
        self._data.update(values)
        self.save()

    def delete(self, key):
        """Remove a key (optional helper)."""
        if key in self._data:
            del self._data[key]
            self.save()