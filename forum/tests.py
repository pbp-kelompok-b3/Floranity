from datetime import timedelta
import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from forum.models import Post

# Create your tests here.
class ForumTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "AksaIndo1834",
            "sample1@gmail.com",
            "password12345"
        )

        self.other_user = User.objects.create_user(
            "UserLain", 
            "sample2@gmail.com", 
            "password678910"
        )

        self.valid_post_data = {
            "post_title" : "Judul Tes",
            "post_body" : "Isi post tes",
            "tag" : "question"
        }

        self.client.force_login(self.user)

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


        # ----------------- Context & Page Content -----------------
    def test_show_forum_context(self):
        response = self.client.get(reverse("forum:show_forum"))

        self.assertEqual(response.context["page_title"], "Buat Post")
        self.assertFalse(response.context["is_editing_post"])
        self.assertEqual(response.context["tag_choices"], Post.TAG_CHOICES)
        self.assertIn("form", response.context)

    def test_show_user_post_only_shows_own_posts(self):
        Post.objects.create(
            author=self.other_user, post_title="Post Orang Lain",
            post_body="Isi", tag="tips",
        )
        response = self.client.get(reverse("forum:show_user_post"))
        posts = list(response.context["post_list"])

        self.assertEqual(posts, [self.post])
        self.assertTrue(response.context["is_editing_post"])
        self.assertEqual(response.context["page_title"], "Edit Post")
        self.assertEqual(response.context["tag_choices"], Post.TAG_CHOICES)
        self.assertTrue(hasattr(posts[0], "update_form"))

    def test_show_bookmarked_post_only_shows_bookmarked(self):
        other_post = Post.objects.create(
            author=self.other_user, post_title="Post Lain",
            post_body="Isi", tag="tips",
        )
        other_post.bookmarked.add(self.user)

        response = self.client.get(reverse("forum:show_bookmarked_post"))

        self.assertEqual(list(response.context["post_list"]), [other_post])
        self.assertEqual(response.context["tag_choices"], Post.TAG_CHOICES)

    def test_show_post_page(self):
        self.post.post_comments.create(user=self.user, comment_body="Komen 1")
        response = self.client.get(reverse("forum:show_post_page", args=[self.post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/post_page.html")
        self.assertEqual(response.context["post"], self.post)
        self.assertEqual(response.context["comment_list"].count(), 1)
        self.assertIn("form", response.context)

    def test_show_post_page_not_found(self):
        response = self.client.get(reverse("forum:show_post_page", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)


    # ----------------- Create / Edit / Delete (tambahan) -----------------
    def test_create_post_sets_author_to_logged_in_user(self):
        data = {"post_title": "Post Baru", "post_body": "Isi baru", "tag": "tips"}
        self.client.post(reverse("forum:create_post"), data)

        self.assertEqual(Post.objects.get(post_title="Post Baru").author, self.user)

    def test_edit_post_invalid_data_does_not_change_post(self):
        data = {"post_title": "", "post_body": "", "tag": "question"}
        response = self.client.post(reverse("forum:edit_post", args=[self.post.id]), data)

        self.assertRedirects(response, reverse("forum:show_user_post"))
        self.post.refresh_from_db()
        self.assertEqual(self.post.post_title, "Judul Tes")

    def test_delete_post_not_found(self):
        response = self.client.delete(reverse("forum:delete_post", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)


    # ----------------- Search / Filter / Sort (get_post_queryset) -----------------
    def _make_post(self, title, body="Isi", tag="tips", author=None):
        return Post.objects.create(
            author=author or self.user, post_title=title, post_body=body, tag=tag
        )

    def test_search_by_title_and_body(self):
        p1 = self._make_post("Merawat Monstera", "Siram seminggu sekali")
        p2 = self._make_post("Judul lain", "Monstera suka cahaya terang")
        self._make_post("Tidak relevan", "Kaktus")

        response = self.client.get(reverse("forum:show_forum"), {"content": "monstera"})
        self.assertCountEqual(response.context["post_list"], [p1, p2])

    def test_search_multiple_words_uses_and_logic(self):
        p1 = self._make_post("Merawat Monstera", "Siram seminggu sekali")
        self._make_post("Merawat Kaktus", "Jarang disiram")

        response = self.client.get(
            reverse("forum:show_forum"), {"content": "merawat monstera"}
        )
        self.assertEqual(list(response.context["post_list"]), [p1])

    def test_search_blank_query_returns_all(self):
        self._make_post("Post kedua")
        response = self.client.get(reverse("forum:show_forum"), {"content": "   "})
        self.assertEqual(response.context["post_list"].count(), 2)

    def test_search_no_match(self):
        response = self.client.get(reverse("forum:show_forum"), {"content": "zzzz"})
        self.assertEqual(response.context["post_list"].count(), 0)

    def test_filter_by_tag(self):
        tips_post = self._make_post("Tips post", tag="tips")
        response = self.client.get(reverse("forum:show_forum"), {"tag_filter": "tips"})

        self.assertEqual(list(response.context["post_list"]), [tips_post])

    def test_sort_recent_post_oldest_and_newest(self):
        newer = self._make_post("Post lebih baru")
        Post.objects.filter(pk=self.post.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        oldest = self.client.get(reverse("forum:show_forum"), {"recent_post": "oldest"})
        self.assertEqual(list(oldest.context["post_list"]), [self.post, newer])

        newest = self.client.get(reverse("forum:show_forum"), {"recent_post": "newest"})
        self.assertEqual(list(newest.context["post_list"]), [newer, self.post])

    def test_sort_most_likes_and_least_likes(self):
        popular = self._make_post("Post populer")
        popular.liked.add(self.user, self.other_user)

        most = self.client.get(reverse("forum:show_forum"), {"most_likes": "most_likes"})
        self.assertEqual(list(most.context["post_list"]), [popular, self.post])

        least = self.client.get(reverse("forum:show_forum"), {"most_likes": "least_likes"})
        self.assertEqual(list(least.context["post_list"]), [self.post, popular])

    def test_queryset_annotations(self):
        self.post.liked.add(self.user)
        self.post.bookmarked.add(self.other_user)
        self.post.post_comments.create(user=self.user, comment_body="Komen")

        response = self.client.get(reverse("forum:show_forum"))
        post = response.context["post_list"][0]

        self.assertEqual(post.likes_total, 1)
        self.assertEqual(post.comments_total, 1)
        self.assertTrue(post.is_liked)
        self.assertFalse(post.is_bookmarked)

    def test_search_works_on_user_post_and_bookmark_pages(self):
        self._make_post("Cari saya")
        self.post.bookmarked.add(self.user)

        r1 = self.client.get(reverse("forum:show_user_post"), {"content": "cari"})
        self.assertEqual(r1.context["post_list"].count(), 1)

        r2 = self.client.get(reverse("forum:show_bookmarked_post"), {"content": "cari"})
        self.assertEqual(r2.context["post_list"].count(), 0)


    # ----------------- Toggle Like / Bookmark (tambahan) -----------------
    def test_toggle_like_twice_untoggles(self):
        url = reverse("forum:toggle_like_button", args=[self.post.id])
        self.client.post(url)
        response = self.client.post(url)

        self.assertEqual(response.json(), {"toggle_command": "untoggle"})
        self.assertNotIn(self.user, self.post.liked.all())

    def test_toggle_like_not_found(self):
        url = reverse("forum:toggle_like_button", args=[uuid.uuid4()])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_toggle_bookmark_toggle_and_untoggle(self):
        url = reverse("forum:toggle_bookmark_button", args=[self.post.id])

        response = self.client.post(url)
        self.assertEqual(response.json(), {"toggle_command": "toggle"})
        self.assertIn(self.user, self.post.bookmarked.all())

        response = self.client.post(url)
        self.assertEqual(response.json(), {"toggle_command": "untoggle"})
        self.assertNotIn(self.user, self.post.bookmarked.all())

    def test_toggle_bookmark_rejects_get(self):
        url = reverse("forum:toggle_bookmark_button", args=[self.post.id])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_toggle_bookmark_not_found(self):
        url = reverse("forum:toggle_bookmark_button", args=[uuid.uuid4()])
        self.assertEqual(self.client.post(url).status_code, 404)


    # ----------------- Comment Section / Add Comment (tambahan) -----------------
    def test_show_comment_section(self):
        self.post.post_comments.create(user=self.user, comment_body="Komen 1")
        response = self.client.get(reverse("forum:show_comment_section", args=[self.post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forum/comment_section.html")
        self.assertEqual(response.context["post_id"], self.post.id)
        self.assertEqual(response.context["comment_list"].count(), 1)

    def test_show_comment_section_not_found(self):
        url = reverse("forum:show_comment_section", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_add_comment_saves_user_and_post(self):
        url = reverse("forum:add_comment", args=[self.post.id])
        self.client.post(url, {"comment_body": "Komentar tes"})

        comment = self.post.post_comments.get()
        self.assertEqual(comment.user, self.user)

    def test_add_comment_post_not_found(self):
        url = reverse("forum:add_comment", args=[uuid.uuid4()])
        response = self.client.post(url, {"comment_body": "Komentar"})
        self.assertEqual(response.status_code, 404)


# Untuk user anonim (belum logged in)
class ForumAnonymousTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", "o@gmail.com", "password12345")
        self.post = Post.objects.create(
            author=self.user, post_title="Judul", post_body="Isi", tag="question"
        )

    def assertRedirectsToLogin(self, response, url):
        self.assertRedirects(
            response, f"/login/?next={url}", fetch_redirect_response=False
        )

    def test_user_post_requires_login(self):
        url = reverse("forum:show_user_post")
        self.assertRedirectsToLogin(self.client.get(url), url)

    def test_bookmarked_post_requires_login(self):
        url = reverse("forum:show_bookmarked_post")
        self.assertRedirectsToLogin(self.client.get(url), url)

    def test_create_post_requires_login(self):
        url = reverse("forum:create_post")
        response = self.client.post(url, {"post_title": "x", "post_body": "y", "tag": "tips"})
        self.assertRedirectsToLogin(response, url)
        self.assertEqual(Post.objects.count(), 1)

    def test_edit_post_requires_login(self):
        url = reverse("forum:edit_post", args=[self.post.id])
        response = self.client.post(url, {"post_title": "Hack", "post_body": "y", "tag": "tips"})
        self.assertRedirectsToLogin(response, url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.post_title, "Judul")

    def test_delete_post_requires_login(self):
        url = reverse("forum:delete_post", args=[self.post.id])
        self.assertRedirectsToLogin(self.client.delete(url), url)
        self.assertTrue(Post.objects.filter(pk=self.post.id).exists())

    def test_toggle_like_requires_login(self):
        url = reverse("forum:toggle_like_button", args=[self.post.id])
        self.assertRedirectsToLogin(self.client.post(url), url)

    def test_toggle_bookmark_requires_login(self):
        url = reverse("forum:toggle_bookmark_button", args=[self.post.id])
        self.assertRedirectsToLogin(self.client.post(url), url)

    def test_add_comment_anonymous_gets_hx_redirect(self):
        url = reverse("forum:add_comment", args=[self.post.id])
        response = self.client.post(url, {"comment_body": "Komentar"})

        self.assertEqual(response.status_code, 200)
        login_url = reverse("akun:login")
        next_url = reverse("forum:show_post_page", args=[self.post.id])
        self.assertEqual(response["HX-Redirect"], f"{login_url}?next={next_url}")
        self.assertEqual(self.post.post_comments.count(), 0)

    def test_show_forum_works_for_anonymous(self):
        response = self.client.get(reverse("forum:show_forum"))
        self.assertEqual(response.status_code, 200)
