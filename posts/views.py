from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.urls import reverse

from datetime import datetime

from .forms import PostForm, CommentForm

from .models import Group, Post, User, Follow


@cache_page(5 * 1, key_prefix="index_page")
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.

    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением

    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator},
    )


def group_post(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 10)

    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "group.html",
        {"group": group, "page": page, 'paginator': paginator}
    )


@login_required
def post_new(request):
    if not request.method == 'POST':
        form = PostForm()
        return render(
            request,
            'posts/post_new.html',
            {'form': form, 'is_edit': False},
        )
    
    form = PostForm(request.POST, files=request.FILES or None,)
    if not form.is_valid():
        return render(
            request,
            'posts/post_new.html',
            {'form': form, 'is_edit': False}
        )

    post = form.save(commit=False)
    post.author = request.user
    post.pub_date = datetime.now()
    post.save()

    return redirect('index')


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.all()
    paginator = Paginator(posts, 10)

    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'profile/profile.html',
        {'profile': user,
         'page': page,
         'paginator': paginator}
    )


def post_view(request, username, post_id):
    user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = CommentForm()
    comments = post.comments.all()
    following = Follow.objects.filter(author__username=username, user=request.user)
    return render(
        request,
        'posts/post.html',
        {'author': user, 'post': post, 'form': form, 'items': comments, 'following': following},
    )


@login_required
def post_edit(request, username, post_id):
    # тут тело функции. Не забудьте проверить,
    # что текущий пользователь — это автор записи.
    # В качестве шаблона страницы редактирования укажите шаблон создания новой записи
    # который вы создали раньше (вы могли назвать шаблон иначе)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    if not post.author == request.user:
        return redirect('post', username=username, post_id=post_id)
    # добавим в form свойство files
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if not request.method == 'POST':
        return render(request, 'posts/post_new.html', {'post': post, 'form': form, 'is_edit': True})
    if not form.is_valid():
        return render(request, 'posts/post_new.html', {'post': post, 'form': form, 'is_edit': True})
    form.save()
    return redirect('post', username=request.user.username, post_id=post_id)


def page_not_found(request, exception): # noqa
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    # form = CommentForm()
    # return render(
    #     request,
    #     'comments/comments.html',
    #     {'form': form},
    # )
    if not request.method == 'POST':
        form = CommentForm()
        return render(
            request,
            'posts/post.html',
            {'form': form},
        )

    form = CommentForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            'posts/post.html',
            {'form': form}
        )

    comment = form.save(commit=False)
    comment.post = get_object_or_404(Post, pk=post_id, author__username=username)
    comment.author = request.user
    comment.created = datetime.now()
    comment.save()

    return redirect('post', username, post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    user = request.user
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.

    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(request, "follow.html", {'page': page, 'paginator': paginator})


@login_required
def profile_follow(request, username):
    Follow.objects.create(
        user=request.user,
        author=get_object_or_404(User, username=username)
    )
    return redirect('profile', username)


@login_required
def profile_unfollow(request, username):
    Follow.objects.get(user=request.user).delete()
    return redirect('index')