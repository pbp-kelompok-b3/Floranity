from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q
from forum.forms import PostForum
from forum.models import Post

# Create your views here.
def show_forum(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request)}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)

    return render(request, 'forum/forum_page_home.html', context)

def show_user_post(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request, True)}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)
    
    return render(request, 'forum/forum_page_user_post.html', context)

def show_bookmarked_post(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request, True)}
    if request.headers.get("HX-Request"):
        return render(request, 'forum/post_rows.html', context)
    
    return render(request, "forum/forum_page_bookmark.html", context)

def create_post(request: HttpRequest):
    form = PostForum(request.POST or None)

    if request.method == "POST" and form.is_valid():
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

    if request.method == "POST" and form.is_valid():
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

def get_post_queryset(request: HttpRequest, show_user_only: bool = False):
    all_post = Post.objects.select_related("author").annotate(
        likes_total=Count("liked", distinct=True), 
        comments_total=Count("post_comments", distinct=True)
        ).order_by("-created_at")

    # NOTE: Ketika sistem autentikasi udah ada, uncomment kode di bawah 
    # if show_user_only:
    #     all_post.filter(author=request.user)

    q = request.GET.get("content", "").strip()
    if q:
        for word in q.split():
            all_post = all_post.filter(
                Q(post_title__icontains=word) |
                Q(post_body__icontains=word)
            )

    return all_post