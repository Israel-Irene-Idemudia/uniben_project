# Campus Location Data Migration Script
# Run this after deploying to seed initial locations from the hardcoded list
# Usage: python manage.py shell < seed_locations.py

from core.models import CampusLocation

# Data from the original uniben_locations.dart
initial_locations = [
    # Faculties
    {'name': 'Faculty of Arts', 'category': 'faculty', 'latitude': 6.4038, 'longitude': 5.6182},
    {'name': 'Faculty of Education', 'category': 'faculty', 'latitude': 6.4029, 'longitude': 5.6195},
    {'name': 'Faculty of Engineering', 'category': 'faculty', 'latitude': 6.4005, 'longitude': 5.6153},
    {'name': 'Faculty of Law', 'category': 'faculty', 'latitude': 6.4050, 'longitude': 5.6175},
    {'name': 'Faculty of Life Sciences', 'category': 'faculty', 'latitude': 6.4011, 'longitude': 5.6205},
    {'name': 'Faculty of Physical Sciences', 'category': 'faculty', 'latitude': 6.4018, 'longitude': 5.6215},
    {'name': 'Faculty of Social Sciences', 'category': 'faculty', 'latitude': 6.4045, 'longitude': 5.6178},
    {'name': 'Faculty of Pharmacy', 'category': 'faculty', 'latitude': 6.3985, 'longitude': 5.6085},
    {'name': 'Faculty of Agriculture', 'category': 'faculty', 'latitude': 6.415, 'longitude': 5.632},
    
    # Admin Buildings
    {'name': 'Senate Building (Admin)', 'category': 'admin', 'latitude': 6.4023, 'longitude': 5.6179},
    {'name': 'Student Affairs Division', 'category': 'admin', 'latitude': 6.4062, 'longitude': 5.6168},
    
    # Landmarks
    {'name': 'John Harris Library', 'category': 'landmark', 'latitude': 6.4021, 'longitude': 5.6190},
    {'name': 'Akin Deko Auditorium', 'category': 'landmark', 'latitude': 6.4015, 'longitude': 5.6172},
    {'name': 'Main Gate', 'category': 'landmark', 'latitude': 6.4095, 'longitude': 5.6125},
    {'name': 'Sports Complex', 'category': 'landmark', 'latitude': 6.4085, 'longitude': 5.6145},
    {'name': 'Uniben Staff School', 'category': 'landmark', 'latitude': 6.412, 'longitude': 5.615},
    
    # Health
    {'name': 'Health Services (Medical Centre)', 'category': 'health', 'latitude': 6.4001, 'longitude': 5.6135},
    
    # Hostels
    {'name': 'Hall 1 (Male Hostel)', 'category': 'hostel', 'latitude': 6.4078, 'longitude': 5.6160},
    {'name': 'Hall 2 (Male Hostel)', 'category': 'hostel', 'latitude': 6.4070, 'longitude': 5.6155},
    {'name': 'Hall 3 (Female Hostel)', 'category': 'hostel', 'latitude': 6.4005, 'longitude': 5.6120},
    {'name': 'Hall 4 (Female Hostel)', 'category': 'hostel', 'latitude': 6.3995, 'longitude': 5.6115},
]

created_count = 0
for loc in initial_locations:
    obj, created = CampusLocation.objects.get_or_create(
        name=loc['name'],
        defaults={
            'category': loc['category'],
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
            'is_active': True,
        }
    )
    if created:
        created_count += 1
        print(f"Created: {loc['name']}")
    else:
        print(f"Exists: {loc['name']}")

print(f"\nDone! Created {created_count} new locations.")
