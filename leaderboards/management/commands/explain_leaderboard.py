"""Print the database plan for one personal board query (Phase 4.3, D-5).

Read-only: it runs EXPLAIN on exactly the SQL the endpoint runs. With
--analyze on PostgreSQL it also EXECUTES that SELECT to report real timings
(still read-only, but it does load the database: use a staging copy).

    python manage.py explain_leaderboard university week --unit-id 1
    python manage.py explain_leaderboard department lifetime --unit-id 7 --analyze
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from leaderboards import boards
from seasons.models import Season


class Command(BaseCommand):
    help = "Show the query plan for a personal leaderboard (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("scope", choices=boards.SCOPES)
        parser.add_argument("period", choices=boards.PERIODS)
        parser.add_argument("--unit-id", type=int, required=True, help="Department, faculty or university id.")
        parser.add_argument("--season-id", type=int, help="Default: the open season of the period's kind.")
        parser.add_argument("--viewer-id", type=int, help="User whose neighbours are fetched.")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--around", type=int, default=2)
        parser.add_argument("--top", type=int, default=10)
        parser.add_argument("--analyze", action="store_true", help="PostgreSQL only: EXPLAIN (ANALYZE, BUFFERS).")

    def handle(self, *args, **opts):
        season = None
        if opts["season_id"] is not None:
            season = Season.objects.filter(pk=opts["season_id"]).first()
            if season is None:
                raise CommandError("Season not found.")
        try:
            window = boards.resolve_window(opts["period"], season)
        except boards.BoardError as exc:
            raise CommandError(str(exc))
        if window is None:
            raise CommandError("No open season of that kind; pass --season-id.")

        sql, params = boards.build_board_sql(
            scope=opts["scope"], unit_id=opts["unit_id"], window=window,
            viewer_id=opts["viewer_id"], offset=0, limit=opts["limit"], around=opts["around"],
            top=opts["top"],
        )
        if connection.vendor == "postgresql":
            prefix = "EXPLAIN (ANALYZE, BUFFERS) " if opts["analyze"] else "EXPLAIN "
        elif connection.vendor == "sqlite":
            if opts["analyze"]:
                raise CommandError("--analyze needs PostgreSQL.")
            prefix = "EXPLAIN QUERY PLAN "
        else:
            raise CommandError(f"Unsupported database: {connection.vendor}")

        self.stdout.write(f"-- database: {connection.vendor}")
        with connection.cursor() as cursor:
            cursor.execute(prefix + sql, params)
            for row in cursor.fetchall():
                self.stdout.write(" | ".join(str(col) for col in row))
