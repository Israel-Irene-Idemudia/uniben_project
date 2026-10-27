# Baseline (27 Oct 2026, branch skholar-world-dev, Python 3.11, SQLite)

- python manage.py check: no issues
- python manage.py test: Ran 12 tests, OK (about 37 s)
- The previously failing materials.tests.MaterialAPITests.test_user_materials_list
  passed in this run. It depends on ordering, so treat it as flaky, not fixed.
- PostgreSQL concurrency test for the redeem endpoint: skipped on SQLite,
  needs a PostgreSQL run.
- Test mode uses SQLite and FileSystemStorage, set by IS_TESTING in settings.py.