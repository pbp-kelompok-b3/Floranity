from django.urls import path

from . import api_views

app_name = 'akun_api'
urlpatterns = [
    path('csrf/', api_views.csrf_token, name='csrf'),
    path('register/', api_views.register, name='register'),
    path('login/', api_views.login_user, name='login'),
    path('logout/', api_views.logout_user, name='logout'),
    path('me/', api_views.profile_me, name='profile-me'),
    path('profiles/<int:user_id>/', api_views.profile_detail, name='profile-detail'),
]
