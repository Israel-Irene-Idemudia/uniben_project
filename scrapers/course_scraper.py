
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def scrape_courses():
    base_url = "https://waeup.uniben.edu"
    faculties_url = f"{base_url}/faculties"
    
    print(f"Starting scrape of {faculties_url}")

    try:
        response = requests.get(faculties_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching faculties page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_courses = []

    # Find all faculty links
    faculty_links = soup.select("table a[href*='/faculties/']")

    if not faculty_links:
        print("No faculty links found on the main page.")
        return

    print(f"Found {len(faculty_links)} faculties. Processing each one...")

    for faculty_link in faculty_links:
        faculty_name = faculty_link.text.strip()
        faculty_url = f"{base_url}{faculty_link['href']}"
        
        print(f"\\n--- Processing Faculty: {faculty_name} ---")

        try:
            faculty_page = requests.get(faculty_url)
            faculty_page.raise_for_status()
            faculty_soup = BeautifulSoup(faculty_page.text, 'html.parser')
            
            # Find all department links within the faculty
            department_links = faculty_soup.select("table a[href*='/departments/']")
            if not department_links:
                print(f"No departments found for {faculty_name}.")
                continue

            print(f"Found {len(department_links)} departments in {faculty_name}.")

            for dept_link in department_links:
                department_name = dept_link.text.strip()
                dept_url = f"{base_url}{dept_link['href']}"

                # Navigate to the 'certificates' page for the department
                certificates_url = dept_url.replace('/departments/', '/certificates/')
                
                try:
                    certs_page = requests.get(certificates_url)
                    certs_page.raise_for_status()
                    certs_soup = BeautifulSoup(certs_page.text, 'html.parser')
                    
                    # Find the link for "Bachelor of" for full-time
                    # This uses a regex to find "Bachelor of" but not "part-time"
                    bachelor_link = certs_soup.find(
                        'a', 
                        href=re.compile(r'/certificates/'),
                        string=re.compile(r'Bachelor of', re.IGNORECASE)
                    )

                    # A secondary check if the first one fails, looking for BART etc.
                    if not bachelor_link:
                         bachelor_link = certs_soup.find(
                            'a', 
                            href=re.compile(r'/certificates/'),
                            string=re.compile(r'BART|BSC|BENG|BEDU', re.IGNORECASE)
                        )

                    if not bachelor_link or 'part-time' in bachelor_link.text.lower():
                        print(f"  - No suitable Bachelor's program found for {department_name}.")
                        continue

                    program_name = bachelor_link.text.strip()
                    courses_url = f"{base_url}{bachelor_link['href']}"
                    
                    print(f"  - Scraping courses for: {department_name} ({program_name})")

                    courses_page = requests.get(courses_url)
                    courses_page.raise_for_status()
                    courses_soup = BeautifulSoup(courses_page.text, 'html.parser')
                    
                    # Find all course tables on the page (one for each level/semester)
                    course_tables = courses_soup.find_all('table')
                    
                    for table in course_tables:
                        # Extract level and semester from the table's preceding header
                        header = table.find_previous(['h3', 'h4'])
                        level_text = header.text if header else "Unknown Level"
                        
                        level_match = re.search(r'(\d)00 Level', level_text)
                        level = int(level_match.group(1)) * 100 if level_match else 0
                        
                        semester = "First" if "First Semester" in level_text else "Second"

                        rows = table.find_all('tr')[1:]  # Skip header row
                        for row in rows:
                            cols = row.find_all('td')
                            if len(cols) >= 2:
                                course_code = cols[0].text.strip()
                                course_title = cols[1].text.strip()
                                
                                # Skip if it's an empty row
                                if not course_code and not course_title:
                                    continue

                                all_courses.append({
                                    "Level": level,
                                    "Semester": semester,
                                    "Course Code": course_code,
                                    "Course Title": course_title,
                                    "Faculty": faculty_name,
                                    "Department": department_name,
                                })

                except requests.exceptions.RequestException as e:
                    print(f"    - Could not process {department_name}: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            print(f"Could not process faculty {faculty_name}: {e}")
            continue

    if not all_courses:
        print("\\nScraping complete, but no courses were found.")
        return
        
    # Convert to DataFrame and save to CSV
    df = pd.DataFrame(all_courses)
    output_path = 'backend/uniben_project/scrapers/scraped_courses.csv'
    df.to_csv(output_path, index=False)
    
    print(f"\\n\\nScraping complete! Found {len(all_courses)} courses.")
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    scrape_courses()
