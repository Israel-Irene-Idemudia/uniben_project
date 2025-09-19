"""
URL configuration for uniben_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

# --- This is the crucial import ---
# It tells this file where to find the custom login view we created in the 'accounts' app.
from accounts.views import MyTokenObtainPairView

urlpatterns = [
    # Django Admin Site
    path('admin/', admin.site.urls),

    # API endpoints for different apps
    path('api/', include('news.urls')),
    path('api/', include('events.urls')),
    path('api/', include('materials.urls')),
    path('api/cbt/', include('cbt.urls')),
    path("api/", include("api.urls")),
    path("api/core/", include("core.urls")),
    path("ai/", include("aiassistant.urls")),
    
    # --- Authentication Endpoints ---
    
    # This path now correctly uses our custom view for logging in.
    path("api/token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    
    # This path uses the default view for refreshing an authentication token.
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # This includes all URLs from the 'accounts' app, such as '/register/'.
    path("api/accounts/", include("accounts.urls")),
]

