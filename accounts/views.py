from django.core.exceptions import ValidationError

from forum.models import UserProfile
from .utils import generate_verification_token
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth import logout as auth_logout
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.contrib import messages

def forget_password(request):
    return render(request, 'account/forget_password.html')

def logout(request):
    # Perform logout
    auth_logout(request)

    return render(request, 'account/logout.html')


def generate_verification_token(user_email):
    user = User.objects.get(email=user_email)
    uid = urlsafe_base64_encode(str(user.pk).encode())
    token = default_token_generator.make_token(user)
    return uid, token

def send_verification_email(user_email):
    uid, token = generate_verification_token(user_email)
    verification_link = f"http://127.0.0.1:8002/accounts/verify-email/{uid}/{token}/"  # Make sure this URL matches your URL pattern
    send_mail(
        subject="Verify Your Email - Dynamic Public Library",
        message=f"Hello, \n\nPlease verify your email by clicking on the link below:\n{verification_link}\n\nThank you!",
        from_email="no-reply@dpl.org.np",
        recipient_list=[user_email],
        fail_silently=False,
    )

def sign_up(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')

        # Validate inputs
        if not email or not password or not confirm_password:
            messages.error(request, 'All fields are required.')
            return redirect('sign_up')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('sign_up')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already in use.')
            return redirect('sign_up')

        try:
            # Create inactive user
            user = User.objects.create_user(username=email.split('@')[0], email=email, password=password)
            user.is_active = False  # Make user inactive until verified
            user.save()

            # Send verification email
            send_verification_email(user.email)  # Ensure this function is implemented

            # Safely create user profile
            UserProfile.objects.get_or_create(user=user)

            messages.success(request, 'Account created! Please verify your email to activate your account.')
            return redirect('login')

        except ValidationError as e:
            messages.error(request, f'Error creating account: {", ".join(e.messages)}')
            return redirect('sign_up')

        except IntegrityError:
            messages.error(request, 'A profile already exists for this user.')
            return redirect('sign_up')

    return render(request, 'account/sign_up.html')

def verify_email(request, uidb64, token):
    try:
        # Decode the UID
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)

        # Check the token
        if default_token_generator.check_token(user, token):
            user.is_active = True  # Activate the user
            user.save()
            messages.success(request, "Email verified successfully! You can now log in.")
            return redirect('login')
        else:
            return HttpResponse("Invalid or expired token.")

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return HttpResponse("Invalid token or user does not exist.")


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Both email and password are required.')
            return redirect('login')

        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'You are now logged in!')
                    return redirect('home')
                else:
                    messages.error(request, 'Your email is not verified yet.')
            else:
                messages.error(request, 'Invalid login credentials.')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')

    return render(request, 'account/login.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)

            uid = urlsafe_base64_encode(str(user.pk).encode())

            # Create the reset link
            reset_link = f"http://127.0.0.1:8002/accounts/reset-password/{uid}/{token}/"

            # Send the reset link to the user's email
            send_mail(
                subject="Password Reset Request",
                message=f"Hi {user.username},\n\nPlease click the following link to reset your password:\n{reset_link}\n\nThank you.",
                from_email="no-reply@dpl.org.np",
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
            return redirect('forgot_password')

    return render(request, 'account/forget_password.html')


def reset_password(request, uidb64, token):
    try:
        # Decode the UID and retrieve the user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)

        # Check if the token is valid
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password = request.POST.get('password')
                user.set_password(new_password)  # Set the new password
                user.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
                return redirect('login')  # Redirect to login page after successful reset

            return render(request, 'account/reset_password.html', {'uid': uidb64, 'token': token})
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('forgot_password')  # Redirect to forgot password page if the token is invalid
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Invalid password reset link.')
        return redirect('forgot_password')  # Redirect to forgot password if something goes wrong
