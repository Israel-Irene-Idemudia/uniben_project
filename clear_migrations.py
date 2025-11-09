import os

apps = ["accounts", "api", "cbt", "core", "events", "materials", "news"]  # add all apps that have migrations

for app in apps:
    migrations_path = os.path.join(app, "migrations")
    if not os.path.exists(migrations_path):
        continue
    for f in os.listdir(migrations_path):
        if f.endswith(".py") and f != "__init__.py":
            os.remove(os.path.join(migrations_path, f))
            print(f"🗑️ Removed migration file: {f} from {app}")
    print(f"✅ Cleared migrations for {app}")
