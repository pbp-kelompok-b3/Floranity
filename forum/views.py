from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Count, Q
from forum.forms import PostForm, CommentForm
from forum.models import Post

# Create your views here.
# Request hanndle untuk menampilkan page forum komunitas (beranda)
def show_forum(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request)}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)

    context["form"] = PostForm()
    context["page_title"] = "Buat Post"
    context["is_editing_post"] = False
    context['tag_choices'] = Post.TAG_CHOICES
    return render(request, 'forum/forum_page_home.html', context)

# Request handler untuk menampilkan page semua post milik user
def show_user_post(request: HttpRequest):
    all_post = get_post_queryset(request, True)
    for post in all_post:
        post.update_form = PostForm(instance=post)

    context = {"post_list" : all_post}
    if request.headers.get("HX-Request"):
        return render(request, "forum/post_rows.html", context)

    context['page_title'] = "Edit Post"
    context['is_editing_post'] = True
    context["tag_choices"] = Post.TAG_CHOICES
    return render(request, 'forum/forum_page_user_post.html', context)

# Request handler untuk menampilkan page semua post yang disimpan oleh user (bookmarked post)
def show_bookmarked_post(request: HttpRequest):
    context = {"post_list" : get_post_queryset(request, True)}
    if request.headers.get("HX-Request"):
        return render(request, 'forum/post_rows.html', context)
    
    context["tag_choices"] = Post.TAG_CHOICES
    return render(request, "forum/forum_page_bookmark.html", context)

# Request handler untuk menampilkan page dari post
def show_post_page(request: HttpRequest, post_id):
    post = get_object_or_404(Post, pk=post_id)
    all_comment = post.post_comments.all().order_by("-created_at")

    context = {
        "post" : post,
        "comment_list" : all_comment,
        "form" : CommentForm()
    }

    return render(request, "forum/post_page.html", context)

# Request handler untuk menampilkan form membuat post baru
def create_post(request: HttpRequest):
    form = PostForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        
        # NOTE: Ketika sistem autentikasi udah ada, uncomment kode di bawah 
        # post.author = request.user

        post.save()
        return redirect("forum:show_post_page", post_id=post.id)

# Request handler untuk menampilkan form mengedit post milik user
# Form yang ditampilkan bukan form kosongan, tapi udah ada isi sesuai sama data post yang di-edit
@require_POST
def edit_post(request: HttpRequest, post_id):
    post_obj = get_object_or_404(Post, pk=post_id)
    form = PostForm(request.POST or None, instance=post_obj)

    if form.is_valid():
        post = form.save(commit=False)

        # NOTE: Ketika sistem autentikasi udah ada, uncomment kode di bawah 
        # post.author = request.user
        
        post.save()
        return redirect("forum:show_user_post")

@require_http_methods(["DELETE"])
def delete_post(request: HttpRequest, post_id):
    post = get_object_or_404(Post, pk=post_id)
    post.delete()
    return HttpResponse("")

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

    # Untuk filter berdasarkan query "search bar"
    q = request.GET.get("content", "").strip()
    if q:
        for word in q.split():
            all_post = all_post.filter(
                Q(post_title__icontains=word) |
                Q(post_body__icontains=word)
            )

    # Untuk sorting berdasarkan value select "tag_filter"
    q = request.GET.get("tag_filter", "").strip()
    if q:
        all_post = all_post.filter(tag=q)

    # Untuk sorting berdasarkan value select "recent_post"
    q = request.GET.get("recent_post", "").strip()
    if q:
        if q == "oldest":
            all_post = all_post.order_by("created_at")
        else:
            all_post = all_post.order_by("-created_at")

    # Untuk sorting berdasarkan value select "most_likes"
    q = request.GET.get("most_likes", "").strip()
    if q:
        if q == "most_likes":
            all_post = all_post.order_by("-likes_total")
        else:
            all_post = all_post.order_by("likes_total")

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

    # NOTE: Kode sementara, untuk melihat toggle active berhasil
    return JsonResponse({"toggle_command" : "toggle"})

# Request handler untuk menampilkan comment section pada sebuah post
def show_comment_section(request: HttpRequest, post_id):
    post = get_object_or_404(Post, pk=post_id)
    all_comments = post.post_comments.all().order_by("-created_at")

    context = {
        "comment_list" : all_comments,
        "form" : CommentForm(),
        "post_id" : post_id
    }

    return render(request, "forum/comment_section.html", context)

# Request handler untuk menambahkan komen pada sebuah post
@require_POST
def add_comment(request: HttpRequest, post_id):
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, pk=post_id)
    
    if form.is_valid():
        created_comment = form.save(commit=False)
        created_comment.commented_at = post
        created_comment.save()

    all_comments = post.post_comments.all().order_by("-created_at")
    return render(request, "forum/comment_rows.html", context={"comment_list" : all_comments})