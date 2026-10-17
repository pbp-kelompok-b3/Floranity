from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from forum.forms import PostForum
from forum.models import Post

# Create your views here.
def show_forum(request: HttpRequest):
    return render(request, 'forum/forum_page.html')

def create_post(request: HttpRequest):
    form = PostForum(request.POST or None)

    if request.method == "POST" and form.is_valid:
        post = form.save(commit=False)
        post.creator = request.user
        post.save()
        return redirect("forum:show_forum")

    context = {
        "is_editing_post" : False,
        "page_title" : "Membuat Post",
        "form" : form
    }

    return render(request, 'forum/post_form.html', context)

def edit_post(request: HttpRequest, post_id):
    post_obj = get_object_or_404(Post, pk=post_id)
    post_obj_data = {
        "post_title" : post_obj.post_title,
        "post_body" : post_obj.post_body,
    }

    form = PostForum(request.POST or None, initial=post_obj_data, instance=post_obj)

    if request.method == "POST" and form.is_valid:
        post = form.save(commit=False)
        post.creator = request.user
        post.save()
        return redirect("forum:show_forum")

    context = {
        "is_editing_post" : True,
        "page_title" : "Mengedit Post",
        "form" : form
    }

    return render(request, 'forum/post_form.html', context)