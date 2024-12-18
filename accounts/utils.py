from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# Generate the verification token
def generate_verification_token(user):
    """
    Generate a token that can be used for email verification.
    """
    # Using the default token generator to create a verification token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))  # Base64 encoding the user ID
    return uid, token


# Verify the token when the user clicks on the verification link
def verify_token(token):
    """
    Verify the token when the user clicks on the verification link.
    """
    try:
        # Decode the user ID from base64
        uid = force_str(urlsafe_base64_decode(token))
        user = User.objects.get(pk=uid)

        # Validate the token
        if default_token_generator.check_token(user, token):
            return user.email  # Return the user's email if token is valid
        else:
            return None
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise ValidationError("Invalid token or user.")
