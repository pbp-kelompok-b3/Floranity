from django.urls import path

from . import views

app_name = 'akun'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.my_profile, name='my_profile'),
    path('profil/edit/', views.edit_profile, name='edit_profile'),
    path('profil/<int:user_id>/', views.public_profile, name='public_profile'),
    path('pengaturan/hapus/', views.remove_account, name='remove_account'),
]
