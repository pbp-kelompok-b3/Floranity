from django.urls import path
from forum.views import show_forum, edit_post, create_post, show_user_post, show_bookmarked_post

app_name = "forum"

urlpatterns = [
    path("forum/", show_forum, name="show_forum"),
    path("forum/post_saya/", show_user_post, name="show_user_post"),
    path("forum/koleksi_post_saya/", show_bookmarked_post, name="show_bookmarked_post"),
    path("forum/create/", create_post, name="create_post"),
    path("forum/<uuid:post_id>/edit/", edit_post, name="edit_post"),
]