from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from forum.forms import PostForum
from forum.models import Post

# Create your views here.
# Request hanndle untuk menampilkan page forum komunitas (beranda)
def show_forum(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request)}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)

    return render(request, 'forum/forum_page_home.html', context)

# Request handler untuk menampilkan page semua post milik user
def show_user_post(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request, True)}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)
    
    return render(request, 'forum/forum_page_user_post.html', context)

# Request handler untuk menampilkan page semua post yang disimpan oleh user (bookmarked post)
def show_bookmarked_post(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request, True)}
    if request.headers.get("HX-Request"):
        return render(request, 'forum/post_rows.html', context)
    
    return render(request, "forum/forum_page_bookmark.html", context)

# Request handler untuk menampilkan form membuat post baru
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

# Request handler untuk menampilkan form mengedit post milik user
# Form yang ditampilkan bukan form kosongan, tapi udah ada isi sesuai sama data post yang di-edit
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

# Request handler untuk mendapatkan semua data post
# Proses filtering (user only, query search) dilakukan di sini
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

# Request handler untuk men-toggle tombol like pada post ketika diklik
@require_POST
def toggle_like_button(request: HttpRequest, post_id):
    post = get_object_or_404(Post, pk=post_id)

    # NOTE: Autentikasi belum ada. Kalau udah ada, uncomment kode di bawah
    # if request.user in post.liked.all():
    #     post.liked.remove(request.user)
    #     return JsonResponse({"toggle_command" : "untoggle"})
    
    # post.liked.add(request.user)
    # return JsonResponse({"toggle_command" : "toggle"})

    # NOTE: Kode sementara, untuk melihat toggle berhasil
    return JsonResponse({"toggle_command" : "toggle"})

# Request handler untuk men-toggle tombol bookmark pada post ketika di klik
@require_POST
def toggle_bookmark_button(request: HttpRequest, post_id):
    post = get_object_or_404(Post, pk=post_id)
    
    # NOTE: Autentikasi belum ada. Kalau udah ada, uncomment kode di bawah
    # if request.user in post.bookmarked.all():
    #     request.user.remove(request.user)
    #     return JsonResponse({"toggle_command" : "untoggle"})
    
    # post.bookmarked.add(request.user)
    # return JsonResponse({"toggle_command" : "toggle"})

    # NOTE: Kode sementara, untuk melihat toggle berhasil
    return JsonResponse({"toggle_command" : "toggle"})