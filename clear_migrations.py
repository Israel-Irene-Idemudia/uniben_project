import os

apps = ["core", "cbt"]  # add all apps that have migrations

for app in apps:
    migrations_path = os.path.join(app, "migrations")
    for f in os.listdir(migrations_path):
        if f.endswith(".py") and f != "__init__.py":
            os.remove(os.path.join(migrations_path, f))
    print(f"✅ Cleared migrations for {app}")
