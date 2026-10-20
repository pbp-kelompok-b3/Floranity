from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from forum.forms import PostForum
from forum.models import Post

# Create your views here.
def show_forum(request: HttpRequest):
    return render(request, 'forum/forum_page_home.html')

def show_user_post(request: HttpRequest):
    return render(request, 'forum/forum_page_user_post.html')

def show_bookmarked_post(request: HttpRequest):
    return render(request, "forum/forum_page_bookmark.html")

def create_post(request: HttpRequest):
    form = PostForum(request.POST or None)

    if request.method == "POST" and form.is_valid:
        post = form.save(commit=False)
        post.author = request.user
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
        post.author = request.user
        post.save()
        return redirect("forum:show_forum")

    context = {
        "is_editing_post" : True,
        "page_title" : "Mengedit Post",
        "form" : form
    }

    return render(request, 'forum/post_form.html', context)

def get_post_json(request: HttpRequest, show_user_only: bool):
    all_post = Post.objects.all().order_by("-created_at")
    if show_user_only:
        all_post.filter(author=request.user)
    
    data = []
    for post in all_post:
        data.append({
            "pk" : str(post.id),
            "fields" : {
                "author" : post.author,
                "post_title" : post.post_title,
                "post_body" : post.post_body,
                "created_at" : post.created_at
            }
        })

    return JsonResponse(data, safe=False)