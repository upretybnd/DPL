from datetime import datetime
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import  redirect
from django.views.decorators.csrf import csrf_exempt
from .forms import ThreadForm
from .models import Category, Thread, Reply
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import UserProfile, UserPostCount
from .forms import UserProfileForm


# View for listing all categories
def category_list(request):
    categories = Category.objects.all()  # Fetch all categories
    for category in categories:
        # Fetch the latest 5 threads for each category
        category.latest_threads = category.threads.all().order_by('-created_at')[:5]

    paginator = Paginator(categories, 5)  # Display 5 categories per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'discussion/category_list.html', {
        'categories': page_obj,
    })

# View for displaying threads in a category
def category_threads(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    threads = Thread.objects.filter(category=category)



    # Increment the view count for threads
    for thread in threads:
        thread.views += 1
        thread.save()

    # Add the last reply's username for each thread
    for thread in threads:
        last_reply = thread.replies.last()  # Get the latest reply
        if last_reply:
            thread.last_reply = last_reply  # Assign the Reply instance
            thread.last_reply_username = last_reply.author.username  # Fetch username for display, if needed
        else:
            thread.last_reply = None

    # Create a paginator object, limiting to 5 threads per page
    paginator = Paginator(threads, 5)  # Show 5 threads per page
    page_number = request.GET.get('page')  # Get the page number from the query string
    page_obj = paginator.get_page(page_number)  # Get the page of threads

    return render(request, 'discussion/category_threads.html', {
        'category': category,
        'threads': page_obj,  # Pass the paginated threads
    })
# View for displaying a single thread
  # Ensures that the user is logged in before they can post a reply

def thread_detail(request, thread_pk):
    # Get the thread
    thread = get_object_or_404(Thread, pk=thread_pk)
    title = thread.author.profile.custom_title  # Access custom_title instead of title
    thread.views += 1
    thread.save()

    # Handle like on the thread post
    if request.method == 'POST' and 'like_thread' in request.POST:
        if request.user.is_authenticated:
            if request.user in thread.likes.all():
                thread.likes.remove(request.user)  # Unlike the thread
                messages.success(request, 'You have unliked this thread.')
            else:
                thread.likes.add(request.user)  # Like the thread
                messages.success(request, 'You have liked this thread.')
            thread.save()
        else:
            messages.error(request, 'You must be logged in to like this thread.')

        return redirect('thread_detail', thread_pk=thread.pk)

    # Handle like on a reply
    if request.method == 'POST' and 'like_reply' in request.POST:
        reply = get_object_or_404(Reply, id=request.POST.get('like_reply'))

        if request.user.is_authenticated:
            if request.user in reply.likes.all():
                reply.likes.remove(request.user)  # Unlike the reply
                messages.success(request, 'You have unliked this reply.')
            else:
                reply.likes.add(request.user)  # Like the reply
                messages.success(request, 'You have liked this reply.')
            reply.save()
        else:
            messages.error(request, 'You must be logged in to like this reply.')

        return redirect('thread_detail', thread_pk=thread.pk)

    # Handle reply submission to the main thread
    if request.method == 'POST' and 'reply_thread' in request.POST:
        content = request.POST.get('content')

        if not content:
            messages.error(request, 'Reply content cannot be empty.')
            return redirect('thread_detail', thread_pk=thread.pk)

        # Create reply
        Reply.objects.create(
            thread=thread,
            author=request.user,
            content=content
        )

        messages.success(request, 'Your reply has been posted!')

        # Redirect to the last page of replies
        page_number = request.GET.get('page')
        replies_list = thread.replies.all()
        paginator = Paginator(replies_list, 5)  # Show 5 replies per page
        last_page = paginator.num_pages
        url = f'{request.path}?page={last_page}'
        return redirect(url)  # Redirect to the last page

    # Pagination for replies
    replies_list = thread.replies.all()
    paginator = Paginator(replies_list, 5)  # Show 5 replies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    thread.author.profile.update_custom_title()

    return render(request, 'discussion/thread_details.html', {
        'thread': thread,
        'replies': page_obj,  # Use paginated replies
        'title': title,
    })


# View for creating a new thread
@login_required
def create_reply(request, thread_pk):
    # Retrieve the thread using the primary key (thread_pk)
    thread = get_object_or_404(Thread, pk=thread_pk)

    # Handle the form submission for the new reply
    if request.method == 'POST':
        content = request.POST.get('content')

        # Check if the reply content is not empty
        if not content:
            messages.error(request, 'Reply content cannot be empty.')
            return redirect('thread_detail', thread_pk=thread.pk)

        # Create the reply associated with the thread and the logged-in user
        reply = Reply.objects.create(
            thread=thread,
            author=request.user,
            content=content
        )

        # Update the thread's last reply to this newly created reply
        thread.last_reply = reply  # Directly update the last_reply field
        thread.save()  # Save the thread to persist the last_reply change

        user_profile = request.user.profile
        user_profile.update_post_count()

        # Success message and redirect to the thread details page
        messages.success(request, 'Your reply has been posted!')
        return redirect('thread_detail', thread_pk=thread.pk)  # Redirect to the same thread page

    # If not a POST request, just render the thread details page
    return render(request, 'discussion/thread_details.html', {
        'thread': thread,
    })

@login_required
def like_thread(request, thread_id):
    thread = get_object_or_404(Thread, id=thread_id)

    if request.user in thread.likes.all():
        thread.likes.remove(request.user)
        liked = False
    else:
        thread.likes.add(request.user)
        liked = True

    return JsonResponse({
        'success': True,
        'liked': liked,
        'total_likes': thread.likes.count()
    })


@login_required
def like_reply(request, reply_id):
    reply = get_object_or_404(Reply, id=reply_id)

    if request.user in reply.likes.all():
        reply.likes.remove(request.user)
        liked = False
    else:
        reply.likes.add(request.user)
        liked = True

    return JsonResponse({
        'success': True,
        'liked': liked,
        'total_likes': reply.likes.count()
    })


@csrf_exempt
def edit_thread(request, thread_id):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'You must be logged in to edit threads.'}, status=400)

    # Fetch the thread object or return 404 if not found
    thread = get_object_or_404(Thread, id=thread_id)

    # Ensure the user is the author of the thread
    if thread.author != request.user:
        return JsonResponse({'success': False, 'message': 'You are not authorized to edit this thread.'}, status=403)

    # Handle POST request (for content update)
    if request.method == 'POST':
        # Parse the JSON request body
        import json
        data = json.loads(request.body)
        new_content = data.get('content')

        # If no content provided, return error
        if not new_content:
            return JsonResponse({'success': False, 'message': 'Content is required.'}, status=400)

        # Update the thread content
        thread.content = new_content
        thread.save()

        # Return success response
        return JsonResponse({'success': True, 'message': 'Thread updated successfully!', 'new_content': new_content})

    # If not POST request, return an error
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

# View to edit a reply
@csrf_exempt
def edit_reply(request, reply_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'You must be logged in to edit replies.'}, status=400)

    reply = get_object_or_404(Reply, id=reply_id)

    # Check if the current user is the author of the reply
    if reply.author != request.user:
        return JsonResponse({'success': False, 'message': 'You are not authorized to edit this reply.'}, status=403)

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        new_content = data.get('content')

        if not new_content:
            return JsonResponse({'success': False, 'message': 'Content is required.'}, status=400)

        # Update the reply content
        reply.content = new_content
        reply.save()

        # Return a success response
        return JsonResponse({'success': True, 'message': 'Reply updated successfully!', 'new_content': new_content})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

# creating thread
def create_thread(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user  # Set the logged-in user as the author
            thread.save()
            return redirect('thread_detail', thread_pk=thread.pk)  # Redirect to the created thread's detail page
    else:
        form = ThreadForm()

    return render(request, 'discussion/create_thread.html', {'form': form})




@login_required
def profile_view(request, username=None):
    # If no username is provided, fall back to the logged-in user's profile
    if username is None:
        username = request.user.username

    # Try to get the profile of the requested user
    user = get_object_or_404(User, username=username)

    # Check if the user is trying to edit the profile
    edit_mode = request.GET.get('edit') == 'true'
    last_login = user.last_login
    if last_login:
        days_since_last_login = (timezone.now() - last_login).days
    else:
        days_since_last_login = None  # If no login, it can be None or 0


    # Try to get the user's profile
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    if request.method == 'POST' and edit_mode:
        # If the profile exists, populate the form with its data
        if profile:
            form = UserProfileForm(request.POST, request.FILES, instance=profile)
        else:
            # If no profile exists, create a new form without existing data
            form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = user  # Ensure the user is set to the correct one
            user_profile.save()
            return redirect('profile', username=username)  # Redirect back to the profile page after saving
    else:
        # If the user has a profile, display it, otherwise show an empty form
        if profile:
            form = UserProfileForm(instance=profile)
        else:
            form = UserProfileForm()  # Display an empty form if no profile exists

    # Access the UserPostCount directly for the user
    try:
        user_post_count = UserPostCount.objects.get(user=user)
        post_count = user_post_count.total_count
    except UserPostCount.DoesNotExist:
        post_count = 0  # Default to 0 if no UserPostCount object exists

    title = profile.get_title_based_on_post_count() if profile else 'Member'

    return render(request, 'account/profile.html', {
        'user': user,
        'edit_mode': edit_mode,
        'form': form,
        'post_count': post_count,
        'title': title,
        'days_since_last_login': days_since_last_login
    })
