from django.db.models import Q
from .models import News

def get_user_news(user):
    """
    Returns all news visible to a user:
    - Global news (for_all=True)
    - Or matching faculty, department, or level
    """
    return News.objects.filter(
        Q(for_all=True) |
        Q(faculty=user.faculty) |
        Q(department=user.department) |
        Q(level=user.level)
    ).order_by('-created_at')
