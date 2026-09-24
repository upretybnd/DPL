import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, F, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ThreadForm, UserProfileForm
from .models import Category, Reply, Thread, UserPostCount, UserProfile

REPLIES_PER_PAGE = 5


# View for listing all categories
def category_list(request):
    categories = Category.objects.all().order_by('id')

    paginator = Paginator(categories, 5)  # Display 5 categories per page
    page_obj = paginator.get_page(request.GET.get('page'))

    for category in page_obj:
        # Fetch the latest 5 threads for each category on this page
        category.latest_threads = (
            category.threads.select_related('author__profile', 'last_reply__author')
            .annotate(reply_count=Count('replies'))
            .order_by('-created_at')[:5]
        )

    return render(request, 'discussion/category_list.html', {
        'categories': page_obj,
    })


# View for displaying threads in a category
def category_threads(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    threads = (
        Thread.objects.filter(category=category)
        .select_related('author__profile', 'last_reply__author')
        .annotate(reply_count=Count('replies'))
        .order_by('-created_at')
    )

    paginator = Paginator(threads, 5)  # Show 5 threads per page
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'discussion/category_threads.html', {
        'category': category,
        'threads': page_obj,
    })


def _toggle_like(obj, user):
    if obj.likes.filter(pk=user.pk).exists():
        obj.likes.remove(user)
        return False
    obj.likes.add(user)
    return True


def _create_reply(thread, user, content):
    reply = Reply.objects.create(thread=thread, author=user, content=content)
    thread.last_reply = reply
    thread.save(update_fields=['last_reply'])
    return reply


def _last_page_url(request, thread):
    last_page = Paginator(thread.replies.all(), REPLIES_PER_PAGE).num_pages
    return f'{thread.get_absolute_url()}?page={last_page}'


# View for displaying a single thread
def thread_detail(request, thread_pk):
    thread = get_object_or_404(Thread.objects.select_related('author__profile', 'category'), pk=thread_pk)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to do that.')
            return redirect(f"/accounts/login/?next={thread.get_absolute_url()}")

        if 'like_thread' in request.POST:
            liked = _toggle_like(thread, request.user)
            messages.success(request, 'You have liked this thread.' if liked else 'You have unliked this thread.')
            return redirect('thread_detail', thread_pk=thread.pk)

        if 'like_reply' in request.POST:
            reply = get_object_or_404(Reply, id=request.POST.get('like_reply'), thread=thread)
            liked = _toggle_like(reply, request.user)
            messages.success(request, 'You have liked this reply.' if liked else 'You have unliked this reply.')
            return redirect('thread_detail', thread_pk=thread.pk)

        if 'reply_thread' in request.POST:
            content = request.POST.get('content', '').strip()
            if not content:
                messages.error(request, 'Reply content cannot be empty.')
                return redirect('thread_detail', thread_pk=thread.pk)
            _create_reply(thread, request.user, content)
            messages.success(request, 'Your reply has been posted!')
            return redirect(_last_page_url(request, thread))

        return redirect('thread_detail', thread_pk=thread.pk)

    # Atomic increment so concurrent visits don't overwrite each other
    Thread.objects.filter(pk=thread.pk).update(views=F('views') + 1)
    thread.refresh_from_db(fields=['views'])

    replies_list = (
        thread.replies.select_related('author__profile')
        .prefetch_related('likes')
        .order_by('created_at')
    )
    page_obj = Paginator(replies_list, REPLIES_PER_PAGE).get_page(request.GET.get('page'))

    return render(request, 'discussion/thread_details.html', {
        'thread': thread,
        'replies': page_obj,
        'thread_liked': request.user.is_authenticated and thread.likes.filter(pk=request.user.pk).exists(),
        'liked_reply_ids': set(
            request.user.liked_replies.filter(thread=thread).values_list('id', flat=True)
        ) if request.user.is_authenticated else set(),
    })


@login_required
@require_POST
def create_reply(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    content = request.POST.get('content', '').strip()

    if not content:
        messages.error(request, 'Reply content cannot be empty.')
        return redirect('thread_detail', thread_pk=thread.pk)

    _create_reply(thread, request.user, content)
    messages.success(request, 'Your reply has been posted!')
    return redirect(_last_page_url(request, thread))


@login_required
@require_POST
def like_thread(request, thread_id):
    thread = get_object_or_404(Thread, id=thread_id)
    liked = _toggle_like(thread, request.user)
    return JsonResponse({'success': True, 'liked': liked, 'total_likes': thread.likes.count()})


@login_required
@require_POST
def like_reply(request, reply_id):
    reply = get_object_or_404(Reply, id=reply_id)
    liked = _toggle_like(reply, request.user)
    return JsonResponse({'success': True, 'liked': liked, 'total_likes': reply.likes.count()})


def _content_from_json(request):
    try:
        return (json.loads(request.body or b'{}').get('content') or '').strip()
    except (ValueError, AttributeError):
        return ''


@require_POST
def edit_thread(request, thread_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'You must be logged in to edit threads.'}, status=401)

    thread = get_object_or_404(Thread, id=thread_id)
    if thread.author != request.user:
        return JsonResponse({'success': False, 'message': 'You are not authorized to edit this thread.'}, status=403)

    new_content = _content_from_json(request)
    if not new_content:
        return JsonResponse({'success': False, 'message': 'Content is required.'}, status=400)

    thread.content = new_content
    thread.save(update_fields=['content', 'updated_at'])
    return JsonResponse({'success': True, 'message': 'Thread updated successfully!', 'new_content': new_content})


@require_POST
def edit_reply(request, reply_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'You must be logged in to edit replies.'}, status=401)

    reply = get_object_or_404(Reply, id=reply_id)
    if reply.author != request.user:
        return JsonResponse({'success': False, 'message': 'You are not authorized to edit this reply.'}, status=403)

    new_content = _content_from_json(request)
    if not new_content:
        return JsonResponse({'success': False, 'message': 'Content is required.'}, status=400)

    reply.content = new_content
    reply.save(update_fields=['content', 'updated_at'])
    return JsonResponse({'success': True, 'message': 'Reply updated successfully!', 'new_content': new_content})


@login_required
def create_thread(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            return redirect('thread_detail', thread_pk=thread.pk)
    else:
        form = ThreadForm(initial={'category': request.GET.get('category')})

    return render(request, 'discussion/create_thread.html', {'form': form})


@login_required
def profile_view(request, username=None):
    profile_user = get_object_or_404(User, username=username or request.user.username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)

    is_owner = profile_user == request.user
    edit_mode = is_owner and request.GET.get('edit') == 'true'

    if request.method == 'POST':
        if not is_owner:
            messages.error(request, 'You can only edit your own profile.')
            return redirect('profile', username=profile_user.username)
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile', username=profile_user.username)
        edit_mode = True
    else:
        form = UserProfileForm(instance=profile)

    days_since_last_login = None
    if profile_user.last_login:
        days_since_last_login = (timezone.now() - profile_user.last_login).days

    post_count = UserPostCount.objects.filter(user=profile_user).values_list('total_count', flat=True).first() or 0

    return render(request, 'account/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'is_owner': is_owner,
        'edit_mode': edit_mode,
        'form': form,
        'post_count': post_count,
        'rank': profile.rank(),
        'days_since_last_login': days_since_last_login,
        'recent_threads': profile_user.threads.select_related('category').order_by('-created_at')[:5],
        'reply_count': profile_user.replies.count(),
        'visit_streak': getattr(getattr(profile_user, 'uservisitstreak', None), 'visit_streak', 0),
    })
