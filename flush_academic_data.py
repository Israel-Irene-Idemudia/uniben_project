#!/usr/bin/env python
"""
Safe database flush script for Lumora/Skholar backend.

DELETES:
- Level (all levels)
- Course (all courses)
- Question (all questions)
- Option (all options - cascades from questions)
- Exam (all exams)
- ExamSession (all quiz sessions)
- ExamQuestion (linking table)

PRESERVES:
- Users (students, staff, admins)
- Faculty (e.g., "Engineering", "Science")
- Department (e.g., "Computer Science", "Mathematics")
- CourseArea (optional groupings within departments)
- All other app data (news, events, materials, etc.)

Run with: python flush_academic_data.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uniben_portal.settings')
django.setup()

from core.models import Level, Course
from cbt.models import Question, Option, Exam, ExamSession, ExamQuestion


def confirm_flush():
    """Ask user for confirmation before flushing."""
    print("=" * 70)
    print("DATABASE FLUSH - ACADEMIC DATA ONLY")
    print("=" * 70)
    print("\n[!] WARNING: This will PERMANENTLY DELETE:")
    print("  - All Levels")
    print("  - All Courses")
    print("  - All Questions & Options")
    print("  - All Exams & Exam Sessions")
    print("\n[+] This will PRESERVE:")
    print("  - All Users (students, staff, admins)")
    print("  - All Faculties")
    print("  - All Departments")
    print("  - All CourseAreas")
    print("  - All other app data (news, events, materials, etc.)")
    print("=" * 70)
    
    # Show current counts
    print(f"\nCurrent Database Counts:")
    print(f"  Levels: {Level.objects.count()}")
    print(f"  Courses: {Course.objects.count()}")
    print(f"  Questions: {Question.objects.count()}")
    print(f"  Exams: {Exam.objects.count()}")
    print(f"  Exam Sessions: {ExamSession.objects.count()}")
    print("=" * 70)
    
    response = input("\nType 'DELETE' to proceed (any other input cancels): ")
    return response.strip() == 'DELETE'


def flush_data():
    """Execute the flush operation."""
    print("\nStarting flush...")
    
    # 1. Delete Exam Sessions (has FK to Exam)
    session_count = ExamSession.objects.count()
    ExamSession.objects.all().delete()
    print(f"[OK] Deleted {session_count} Exam Sessions")
    
    # 2. Delete ExamQuestion linking table
    examq_count = ExamQuestion.objects.count()
    ExamQuestion.objects.all().delete()
    print(f"[OK] Deleted {examq_count} ExamQuestion links")
    
    # 3. Delete Exams
    exam_count = Exam.objects.count()
    Exam.objects.all().delete()
    print(f"[OK] Deleted {exam_count} Exams")
    
    # 4. Delete Questions (Options cascade automatically)
    question_count = Question.objects.count()
    Question.objects.all().delete()
    print(f"[OK] Deleted {question_count} Questions (and their Options)")
    
    # 5. Delete Courses
    course_count = Course.objects.count()
    Course.objects.all().delete()
    print(f"[OK] Deleted {course_count} Courses")
    
    # 6. Delete Levels
    level_count = Level.objects.count()
    Level.objects.all().delete()
    print(f"[OK] Deleted {level_count} Levels")
    
    print("\n[SUCCESS] Flush completed successfully!")
    print("\nNext Steps:")
    print("  1. Re-import your courses using the import script")
    print("  2. Re-create exams and questions as needed")
    print("=" * 70)


if __name__ == '__main__':
    if confirm_flush():
        flush_data()
    else:
        print("\n[CANCELLED] Flush cancelled. No changes made.")
        sys.exit(0)
