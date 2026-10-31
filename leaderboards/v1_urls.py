from django.urls import path

from .views import PersonalLeaderboardView, ScoringRulesView

urlpatterns = [
    path("scoring-rules", ScoringRulesView.as_view(), name="v1-scoring-rules"),
    path("scoring-rules/", ScoringRulesView.as_view()),
    # Personal boards (Phase 4.3). Unknown scope/period is a v1 404 in the view.
    path(
        "leaderboards/<slug:scope>/<slug:period>",
        PersonalLeaderboardView.as_view(),
        name="v1-leaderboard",
    ),
    path("leaderboards/<slug:scope>/<slug:period>/", PersonalLeaderboardView.as_view()),
]
