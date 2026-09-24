import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from forum.models import UserProfile
from reports.permissions import user_has_portal_access

logger = logging.getLogger(__name__)
User = get_user_model()

FROM_EMAIL = "no-reply@dpl.org.np"


def _user_from_uidb64(uidb64):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def _token_link(request, url_name, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse(url_name, kwargs={"uidb64": uid, "token": token}))


def _unique_username(email):
    base = email.split("@")[0][:140] or "member"
    username = base
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def send_verification_email(request, user):
    link = _token_link(request, "verify_email", user)
    send_mail(
        subject="Verify Your Email - Dynamic Public Library",
        message=f"Hello,\n\nPlease verify your email by clicking on the link below:\n{link}\n\nThank you!",
        from_email=FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@require_POST
def logout(request):
    auth_logout(request)
    return render(request, "account/logout.html")


def sign_up(request):
    if request.method != "POST":
        return render(request, "account/sign_up.html")

    full_name = request.POST.get("fullName", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirmPassword", "")

    if not email or not password or not confirm_password:
        messages.error(request, "All fields are required.")
        return redirect("sign_up")

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return redirect("sign_up")

    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, "An account with this email already exists. Try logging in or resetting your password.")
        return redirect("sign_up")

    try:
        validate_password(password, user=User(email=email))
    except ValidationError as e:
        for error in e.messages:
            messages.error(request, error)
        return redirect("sign_up")

    with transaction.atomic():
        user = User.objects.create_user(username=_unique_username(email), email=email, password=password)
        user.is_active = False  # Activated once the email is verified
        user.first_name = full_name[:150]
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if full_name:
            profile.full_name = full_name
            profile.save(update_fields=["full_name"])

    try:
        send_verification_email(request, user)
    except Exception:
        logger.exception("Failed to send verification email to %s", email)
        messages.warning(
            request,
            "Your account was created, but we could not send the verification email. Please contact us to activate it.",
        )
        return redirect("login")

    messages.success(request, "Account created! Please check your email to activate your account.")
    return redirect("login")


def verify_email(request, uidb64, token):
    user = _user_from_uidb64(uidb64)
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This verification link is invalid or has expired.")
        return redirect("login")

    user.is_active = True
    user.save(update_fields=["is_active"])
    messages.success(request, "Email verified successfully! You can now log in.")
    return redirect("login")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Both email and password are required.")
            return redirect("login")

        # ModelBackend rejects inactive users, so check the password directly
        # to tell unverified accounts apart from bad credentials.
        user = User.objects.filter(email__iexact=email).order_by("-is_active", "pk").first()
        if user is None or not user.check_password(password):
            messages.error(request, "Invalid email or password.")
        elif not user.is_active:
            messages.error(request, "Your email is not verified yet. Please check your inbox for the verification link.")
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "You are now logged in!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            # Staff land on their management dashboard; members go to the home page.
            if user_has_portal_access(user):
                return redirect("report_home")
            return redirect("home")

    return render(request, "account/login.html")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            link = _token_link(request, "reset_password", user)
            try:
                send_mail(
                    subject="Password Reset Request",
                    message=f"Hi {user.username},\n\nPlease click the following link to reset your password:\n{link}\n\nIf you did not request this, you can ignore this email.",
                    from_email=FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send password reset email to %s", email)

        # Same response whether or not the account exists, so emails can't be enumerated.
        messages.success(request, "If an account exists for that email, a password reset link has been sent.")
        return redirect("login")

    return render(request, "account/forget_password.html")


def reset_password(request, uidb64, token):
    user = _user_from_uidb64(uidb64)
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "The password reset link is invalid or has expired.")
        return redirect("forgot_password")

    if request.method == "POST":
        new_password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmPassword", "")
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Your password has been reset. You can now log in with your new password.")
                return redirect("login")

    return render(request, "account/reset_password.html", {"uid": uidb64, "token": token})
