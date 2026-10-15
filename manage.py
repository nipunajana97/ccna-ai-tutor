import json
from tutor.config import Settings
from tutor.store import UsageStore

if __name__ == "__main__":
    settings = Settings.from_env()
    store = UsageStore(settings.data_dir / "usage.sqlite3")
    print(json.dumps(store.metrics(), indent=2))
