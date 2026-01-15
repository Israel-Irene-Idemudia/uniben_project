# Campus Location Data Migration Script
# Run this after deploying to seed initial locations
# Usage: python manage.py shell
#        >>> exec(open('seed_locations.py').read())

from core.models import CampusLocation

# Comprehensive UNIBEN locations data
initial_locations = [
    # Faculties
    {"name": "Faculty of Agriculture", "category": "faculty", "latitude": 6.400297, "longitude": 5.623108, "description": "Located opposite the Faculty of Law."},
    {"name": "Faculty of Arts", "category": "faculty", "latitude": 6.403500, "longitude": 5.618200, "description": "Near the Faculty of Social Sciences."},
    {"name": "Faculty of Computing", "category": "faculty", "latitude": 6.400124, "longitude": 5.615093, "description": "Also known as Dept of Computer Science."},
    {"name": "Faculty of Dentistry", "category": "faculty", "latitude": 6.396210, "longitude": 5.617295, "description": "Part of the College of Medical Sciences."},
    {"name": "Faculty of Education", "category": "faculty", "latitude": 6.401500, "longitude": 5.621000, "description": "Near the Education Field."},
    {"name": "Faculty of Engineering", "category": "faculty", "latitude": 6.401852, "longitude": 5.615612, "description": "Along Uniben Road."},
    {"name": "Faculty of Environmental Sciences", "category": "faculty", "latitude": 6.402500, "longitude": 5.619000, "description": "Near Faculty of Physical Sciences."},
    {"name": "Faculty of Law", "category": "faculty", "latitude": 6.401200, "longitude": 5.618500, "description": "Near the Uniben Book Shop."},
    {"name": "Faculty of Life Sciences", "category": "faculty", "latitude": 6.399506, "longitude": 5.614849, "description": "Near Faculty of Engineering."},
    {"name": "Faculty of Management Sciences", "category": "faculty", "latitude": 6.399500, "longitude": 5.614500, "description": "Near Faculty of Engineering."},
    {"name": "Faculty of Pharmacy", "category": "faculty", "latitude": 6.396500, "longitude": 5.619000, "description": "Near the Medical Complex."},
    {"name": "Faculty of Physical Sciences", "category": "faculty", "latitude": 6.400124, "longitude": 5.615093, "description": "Houses Physics and Chemistry."},
    {"name": "Faculty of Social Sciences", "category": "faculty", "latitude": 6.402800, "longitude": 5.619500, "description": "Adjacent to Faculty of Arts."},
    {"name": "Faculty of Veterinary Medicine", "category": "faculty", "latitude": 6.400100, "longitude": 5.612000, "description": "Within Ugbowo campus."},
    {"name": "Faculty of Vocational and Technical Education (VTE)", "category": "faculty", "latitude": 6.401500, "longitude": 5.621000, "description": "Located within the Faculty of Education complex."},
    {"name": "Faculty of Nursing Sciences (NSC)", "category": "faculty", "latitude": 6.390343, "longitude": 5.611804, "description": "Located within the UBTH Complex area."},
    {"name": "School of Basic Medical Sciences (BMS)", "category": "faculty", "latitude": 6.397000, "longitude": 5.618500, "description": "Part of the Medical Complex."},
    {"name": "School of Basic Clinical Sciences (BCS)", "category": "faculty", "latitude": 6.397000, "longitude": 5.618500, "description": "Part of the Medical Complex."},
    {"name": "Faculty of Science Laboratory Technology (SLT)", "category": "faculty", "latitude": 6.400124, "longitude": 5.615093, "description": "Often shares facilities with Physical Sciences."},
    {"name": "Department of Theatre Arts", "category": "faculty", "latitude": 6.323200, "longitude": 5.602200, "description": "Within Ekenwan Campus."},
    {"name": "Department of Music", "category": "faculty", "latitude": 6.323300, "longitude": 5.602100, "description": "Within Ekenwan Campus."},
    {"name": "Department of Fine and Applied Arts", "category": "faculty", "latitude": 6.323000, "longitude": 5.602000, "description": "Within Ekenwan Campus."},
    {"name": "Department of Early Childhood Education", "category": "faculty", "latitude": 6.322900, "longitude": 5.602300, "description": "Within Ekenwan Campus."},
    {"name": "Centre of Excellence in Geosciences (COEGPE)", "category": "faculty", "latitude": 6.401852, "longitude": 5.615612, "description": "Within the Faculty of Engineering."},
    {"name": "Centre of Excellence in Aquaculture (CEAFT)", "category": "faculty", "latitude": 6.400297, "longitude": 5.623108, "description": "Within the Faculty of Agriculture."},
    
    # Hostels
    {"name": "Hall 1 (Queen Idia Hostel)", "category": "hostel", "latitude": 6.398217, "longitude": 5.616943, "description": "Female hostel."},
    {"name": "Hall 2 (Emotan Hall)", "category": "hostel", "latitude": 6.397500, "longitude": 5.616000, "description": "Female hostel."},
    {"name": "Hall 3 (Real Madrid)", "category": "hostel", "latitude": 6.398500, "longitude": 5.615000, "description": "Male hostel."},
    {"name": "Hall 4 (Basement)", "category": "hostel", "latitude": 6.399000, "longitude": 5.615500, "description": "Male hostel."},
    {"name": "Hall 5 Hostel", "category": "hostel", "latitude": 6.398800, "longitude": 5.621500, "description": "Opposite Hall 4."},
    {"name": "Hall 6 Hostel", "category": "hostel", "latitude": 6.399500, "longitude": 5.622500, "description": "Near Keystone Hostel."},
    {"name": "Hall 7 Hostel", "category": "hostel", "latitude": 6.400000, "longitude": 5.623500, "description": "Near Hall 6."},
    {"name": "NDDC Hostel", "category": "hostel", "latitude": 6.397000, "longitude": 5.615000, "description": "Large hostel facility."},
    {"name": "Festus Akingbola Hostel", "category": "hostel", "latitude": 6.397028, "longitude": 5.610150, "description": "Near the Sports Complex/Golf Course."},
    {"name": "Intercontinental Hostel", "category": "hostel", "latitude": 6.398800, "longitude": 5.615200, "description": "Near the Basement area."},
    {"name": "Tetfund Hostels (A, B, C)", "category": "hostel", "latitude": 6.399500, "longitude": 5.622500, "description": "Near the Hall 6 area."},
    {"name": "Sen. Danjuma Hostel", "category": "hostel", "latitude": 6.400000, "longitude": 5.623500, "description": "Near the Hall 7 area."},
    {"name": "Clinical Hostel", "category": "hostel", "latitude": 6.397000, "longitude": 5.618500, "description": "Near the Medical Complex."},
    {"name": "PG Hostel Ekenwan", "category": "hostel", "latitude": 6.323100, "longitude": 5.602100, "description": "Postgraduate hostel at Ekenwan."},
    {"name": "Keystone Hostel", "category": "hostel", "latitude": 6.400500, "longitude": 5.622000, "description": "Private hostel."},
    
    # Admin Buildings
    {"name": "Senate Building", "category": "admin", "latitude": 6.400000, "longitude": 5.610000, "description": "Administrative heart."},
    {"name": "Bursary Department", "category": "admin", "latitude": 6.398500, "longitude": 5.613500, "description": "Financial matters."},
    {"name": "John Harris Library", "category": "admin", "latitude": 6.400500, "longitude": 5.611500, "description": "Central library."},
    {"name": "Vice-Chancellor's Office", "category": "admin", "latitude": 6.400100, "longitude": 5.610500, "description": "Within Senate complex."},
    {"name": "Institute of Education (INE)", "category": "admin", "latitude": 6.323100, "longitude": 5.602100, "description": "Located at the Ekenwan Campus."},
    {"name": "Institute of Public Administration (IPAHSM)", "category": "admin", "latitude": 6.400000, "longitude": 5.610000, "description": "Located near the Senate Building."},
    {"name": "Centre for Entrepreneurship Development (CED)", "category": "admin", "latitude": 6.400500, "longitude": 5.611500, "description": "Near the John Harris Library."},
    {"name": "Centre for Forensic Programmes (CFPDS)", "category": "admin", "latitude": 6.400124, "longitude": 5.615093, "description": "Near the Science faculties."},
    {"name": "Centre for Gender Studies (CGS)", "category": "admin", "latitude": 6.403500, "longitude": 5.618200, "description": "Near the Faculty of Arts."},
    {"name": "Centre for Continuous Legal Education (CLE)", "category": "admin", "latitude": 6.401200, "longitude": 5.618500, "description": "Within the Faculty of Law."},
    {"name": "African Institute of Management (AIML)", "category": "admin", "latitude": 6.399500, "longitude": 5.614500, "description": "Near Management Sciences."},
    {"name": "JUPEB Office", "category": "admin", "latitude": 6.400000, "longitude": 5.610000, "description": "Near the Senate Building."},
    {"name": "Student's Guidance Centre (Old Bookshop)", "category": "admin", "latitude": 6.402500, "longitude": 5.617500, "description": "Located in the Old Bookshop Building."},
    {"name": "ICTU/CRPU Building", "category": "admin", "latitude": 6.400000, "longitude": 5.610000, "description": "Near the Senate Building."},
    
    # Landmarks
    {"name": "Main Gate (Ugbowo)", "category": "landmark", "latitude": 6.399785, "longitude": 5.609863, "description": "Primary entrance."},
    {"name": "Uniben Book Shop", "category": "landmark", "latitude": 6.402500, "longitude": 5.617500, "description": "Academic materials."},
    {"name": "June 12, UNIBEN", "category": "landmark", "latitude": 6.400800, "longitude": 5.618000, "description": "Commemorative site."},
    {"name": "Akindeko Main Auditorium", "category": "landmark", "latitude": 6.399757, "longitude": 5.613131, "description": "Multi-purpose auditorium."},
    {"name": "UNIBEN New Shuttle Park", "category": "landmark", "latitude": 6.399900, "longitude": 5.610200, "description": "Main transportation hub just inside Main Gate."},
    {"name": "Ekosodin", "category": "landmark", "latitude": 6.405000, "longitude": 5.605000, "description": "Student residential area."},
    {"name": "BDPA Community", "category": "landmark", "latitude": 6.410000, "longitude": 5.615000, "description": "Residential area near campus."},
    
    # Sports
    {"name": "Main Bowl Sports Complex", "category": "sports", "latitude": 6.397500, "longitude": 5.612500, "description": "Sports facility."},
    {"name": "UNIBEN Gym", "category": "sports", "latitude": 6.399200, "longitude": 5.619800, "description": "Fitness center."},
    {"name": "UNIBEN Golf Course", "category": "sports", "latitude": 6.397028, "longitude": 5.610150, "description": "Near the Sports Complex."},
    
    # Health
    {"name": "UNIBEN Health Center", "category": "health", "latitude": 6.396000, "longitude": 5.611000, "description": "Medical facility."},
    {"name": "Medical Complex", "category": "health", "latitude": 6.397000, "longitude": 5.618500, "description": "Medical departments."},
    {"name": "Institute of Child Health (ICH)", "category": "health", "latitude": 6.396000, "longitude": 5.611000, "description": "Near the UNIBEN Health Center."},
    {"name": "Centre of Excellence in Reproductive Health (CERHI)", "category": "health", "latitude": 6.397000, "longitude": 5.618500, "description": "Within the Medical Complex."},
    {"name": "University of Benin Teaching Hospital (UBTH)", "category": "health", "latitude": 6.395000, "longitude": 5.605000, "description": "Adjacent to Ugbowo campus."},
    
    # Commercial
    {"name": "Unity Bank", "category": "commercial", "latitude": 6.399500, "longitude": 5.614500, "description": "Near the commercial/admin area."},
    {"name": "Uselu Market", "category": "commercial", "latitude": 6.385000, "longitude": 5.610000, "description": "Nearby local market."},
]

created_count = 0
updated_count = 0

for loc in initial_locations:
    obj, created = CampusLocation.objects.update_or_create(
        name=loc['name'],
        defaults={
            'category': loc['category'],
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
            'description': loc.get('description', ''),
            'is_active': True,
        }
    )
    if created:
        created_count += 1
        print(f"✅ Created: {loc['name']}")
    else:
        updated_count += 1
        print(f"🔄 Updated: {loc['name']}")

print(f"\n🎉 Done! Created {created_count} new, Updated {updated_count} existing locations.")
print(f"📍 Total locations: {CampusLocation.objects.count()}")
