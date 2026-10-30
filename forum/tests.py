import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from forum.models import Post

# Create your tests here.
class ForumTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "AksaIndo1834",
            "sample1@gmail.com",
            "password12345"
        )

        self.valid_post_data = {
            "post_title" : "Judul Tes",
            "post_body" : "Isi post tes",
            "tag" : "question"
        }

        self.post = Post.objects.create(author=self.user, **self.valid_post_data)

    # ----------------- URL Access -----------------
    def test_home_page_url(self):
        response = self.client.get(reverse("forum:show_forum"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/forum_page_home.html")

    def test_user_post_page_url(self):
        response = self.client.get(reverse("forum:show_user_post"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/forum_page_user_post.html")

    def test_bookmark_page_url(self):
        response = self.client.get(reverse("forum:show_bookmarked_post"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/forum_page_bookmark.html")

    def test_not_exist_url(self):
        response = self.client.get("forum/non_exist/")

        self.assertEqual(response.status_code, 404)


    # ----------------- Create Post URL Test ----------------
    def test_post_form_valid_redirect_and_saves(self):
        post_data = {
            "author" : self.user,
            "post_title" : "Judul Post Tes 2",
            "post_body" : "Isi post tes 2",
            "tag" : "tips"
        }

        response = self.client.post(reverse("forum:create_post"), post_data)
        new_post = Post.objects.get(post_title="Judul Post Tes 2", post_body="Isi post tes 2")

        self.assertRedirects(response, reverse("forum:show_post_page", args=[new_post.id]))
        self.assertEqual(Post.objects.count(), 2)

    def test_create_post_reject_get(self):
        response = self.client.get(reverse("forum:create_post"), self.valid_post_data)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Post.objects.count(), 1)

    def test_create_post_with_invalid_data(self):
        response = self.client.post(reverse("forum:create_post"), data={"post_title" : "No Post Body"})

        self.assertRedirects(response, reverse("forum:show_forum"))
        self.assertEqual(Post.objects.count(), 1)


    # ----------------- Edit Post URL Test -----------------
    def test_edit_post_valid_updates_data(self):
        data = {**self.valid_post_data, "post_title": "Judul baru"}
        response = self.client.post(reverse("forum:edit_post", args=[self.post.id]), data)

        self.assertRedirects(response, reverse("forum:show_user_post"))
        self.post.refresh_from_db()
        self.assertEqual(self.post.post_title, "Judul baru")

    def test_edit_post_rejects_get(self):
        response = self.client.get(reverse("forum:edit_post", args=[self.post.id]))
        self.assertEqual(response.status_code, 405) 

    def test_edit_post_not_found(self):
        url = reverse("forum:edit_post", args=[uuid.uuid4()])
        response = self.client.post(url, self.valid_post_data)
        self.assertEqual(response.status_code, 404)


    # ----------------- Delete Post URL Test -----------------
    def test_delete_post_with_delete_method(self):
        response = self.client.delete(reverse("forum:delete_post", args=[self.post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=self.post.id).exists())

    def test_delete_post_rejects_get(self):
        response = self.client.get(reverse("forum:delete_post", args=[self.post.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Post.objects.filter(pk=self.post.id).exists())


    # ----------------- Add Comment Test -----------------
    def test_add_comment_valid(self):
        url = reverse("forum:add_comment", args=[self.post.id])
        response = self.client.post(url, {"comment_body": "Komentar tes"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/comment_rows.html")
        self.assertEqual(self.post.post_comments.count(), 1)

    def test_add_comment_invalid_not_saved(self):
        url = reverse("forum:add_comment", args=[self.post.id])
        response = self.client.post(url, {"comment_body": ""})

        self.assertEqual(response.status_code, 200)  # view tetap render comment_rows
        self.assertEqual(self.post.post_comments.count(), 0)


    # ----------------- like / bookmark -----------------
    def test_toggle_like_returns_json(self):
        response = self.client.post(reverse("forum:toggle_like_button", args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"toggle_command": "toggle"})

    def test_toggle_like_rejects_get(self):
        response = self.client.get(reverse("forum:toggle_like_button", args=[self.post.id]))
        self.assertEqual(response.status_code, 405)


    # ----------------- HTMX Request Test -----------------
    def test_htmx_request_on_show_forum(self):
        response = self.client.get(reverse("forum:show_forum"), HTTP_HX_REQUEST=True)

        self.assertTemplateUsed(response, "forum/post_rows.html")
        self.assertTemplateNotUsed(response, "forum/forum_page_home.html")
    
    def test_htmx_request_on_show_user_post(self):
        response = self.client.get(reverse("forum:show_user_post"), HTTP_HX_REQUEST=True)

        self.assertTemplateUsed(response, "forum/post_rows.html")
        self.assertTemplateNotUsed(response, "forum/forum_page_user_post.html")
    
    def test_htmx_request_on_show_bookmarked_post(self):
        response = self.client.get(reverse("forum:show_bookmarked_post"), HTTP_HX_REQUEST=True)

        self.assertTemplateUsed(response, "forum/post_rows.html")
        self.assertTemplateNotUsed(response, "forum/forum_page_bookmark.html")