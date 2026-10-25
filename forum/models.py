from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post_title = models.CharField(max_length=250, null=False, blank=False)
    post_body = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    liked = models.ManyToManyField(User, related_name="liked_post")
    bookmarked = models.ManyToManyField(User, related_name="bookmarked_post")

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    comment_body = models.TextField(null=False, blank=False)
    commented_at = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_comments")