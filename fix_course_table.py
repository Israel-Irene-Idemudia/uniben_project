"""
Script to fix the course_course table by adding missing columns.
This handles the case where the table was created with an old schema.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uniben_portal.settings')
django.setup()

from django.db import connection

def fix_course_table():
    with connection.cursor() as cursor:
        # Check if the table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'course_course'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("Table course_course does not exist. Run migrations first.")
            return
        
        # Get existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'course_course';
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Define all columns that should exist
        columns_to_add = []
        
        if 'title' not in existing_columns:
            columns_to_add.append(("title", "VARCHAR(255) NULL"))
        
        if 'level' not in existing_columns:
            columns_to_add.append(("level", "INTEGER NULL"))
        
        if 'semester' not in existing_columns:
            columns_to_add.append(("semester", "INTEGER NULL"))
        
        if 'faculty_code' not in existing_columns:
            columns_to_add.append(("faculty_code", "VARCHAR(10) NULL"))
        
        if 'faculty_title' not in existing_columns:
            columns_to_add.append(("faculty_title", "VARCHAR(255) NULL"))
        
        if 'department_code' not in existing_columns:
            columns_to_add.append(("department_code", "VARCHAR(10) NULL"))
        
        if 'department_title' not in existing_columns:
            columns_to_add.append(("department_title", "VARCHAR(255) NULL"))
        
        if 'certificate_code' not in existing_columns:
            columns_to_add.append(("certificate_code", "VARCHAR(20) NULL"))
        
        if 'certificate_title' not in existing_columns:
            columns_to_add.append(("certificate_title", "VARCHAR(255) NULL"))
        
        if 'created_at' not in existing_columns:
            columns_to_add.append(("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
        
        if 'updated_at' not in existing_columns:
            columns_to_add.append(("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
        
        # Add missing columns
        if columns_to_add:
            print(f"\nAdding {len(columns_to_add)} missing columns...")
            for col_name, col_type in columns_to_add:
                try:
                    sql = f"ALTER TABLE course_course ADD COLUMN {col_name} {col_type};"
                    print(f"  Executing: {sql}")
                    cursor.execute(sql)
                    print(f"  [OK] Added column: {col_name}")
                except Exception as e:
                    print(f"  [ERROR] Error adding {col_name}: {e}")
            
            # Add indexes
            print("\nAdding indexes...")
            try:
                if 'faculty_code' in [c[0] for c in columns_to_add]:
                    cursor.execute("CREATE INDEX IF NOT EXISTS course_course_faculty_code_idx ON course_course(faculty_code);")
                    print("  [OK] Added index on faculty_code")
            except Exception as e:
                print(f"  Note: {e}")
            
            try:
                if 'department_code' in [c[0] for c in columns_to_add]:
                    cursor.execute("CREATE INDEX IF NOT EXISTS course_course_department_code_idx ON course_course(department_code);")
                    print("  [OK] Added index on department_code")
            except Exception as e:
                print(f"  Note: {e}")
            
            try:
                if 'certificate_code' in [c[0] for c in columns_to_add]:
                    cursor.execute("CREATE INDEX IF NOT EXISTS course_course_certificate_code_idx ON course_course(certificate_code);")
                    print("  [OK] Added index on certificate_code")
            except Exception as e:
                print(f"  Note: {e}")
            
            print("\n[SUCCESS] Course table structure fixed successfully!")
        else:
            print("\n[SUCCESS] All columns already exist. No changes needed.")

if __name__ == '__main__':
    fix_course_table()
