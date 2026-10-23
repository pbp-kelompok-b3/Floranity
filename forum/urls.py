from django.urls import path
from forum.views import *

app_name = "forum"

urlpatterns = [
    path("forum/", show_forum, name="show_forum"),
    path("forum/post_saya/", show_user_post, name="show_user_post"),
    path("forum/koleksi_post_saya/", show_bookmarked_post, name="show_bookmarked_post"),
    path("forum/create/", create_post, name="create_post"),
    path("forum/<uuid:post_id>/edit/", edit_post, name="edit_post"),
    path("forum/<uuid:post_id>/like/", toggle_like_button, name="toggle_like_button"),
    path("forum/<uuid:post_id>/bookmark/", toggle_bookmark_button, name="toggle_bookmark_button"),
    path("forum/<uuid:post_id>/comment_section/", show_comment_section, name="show_comment_section"),
    path("forum/<uuid:post_id>/add_comment/", add_comment, name="add_comment")
]