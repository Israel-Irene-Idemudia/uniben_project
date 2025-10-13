import json
from core.models import Course

with open('initial_data.json') as f:
    data = json.load(f)

for entry in data:
    if entry["model"] == "core.course":
        fields = entry["fields"]
        code = fields["code"]
        level_id = fields["level"]

course, created = Course.objects.get_or_create(
    code=code,
    level_id=level_id,
    defaults=fields
    )

if created:
    print(f"Added {code} (Level {level_id})")
else:
    print(f"Skipped duplicate: {code} (Level {level_id})")
