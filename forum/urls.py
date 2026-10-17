from django.urls import path
from forum.views import show_forum, edit_post, create_post

app_name = "forum"

urlpatterns = [
    path("forum/", show_forum, name="show_forum"),
    path("forum/create/", create_post, name="create_post"),
    path("forum/<uuid:post_id>/edit/", edit_post, name="edit_post")
]