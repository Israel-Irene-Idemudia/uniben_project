# accounts/signals.py
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django_rest_passwordreset.signals import reset_password_token_created
import secrets
from django.utils import timezone
from django_rest_passwordreset.models import ResetPasswordToken


import logging

from django.db import transaction

from accounts.models import UserProfile
from accounts.services import sync_department_history

logger = logging.getLogger(__name__)

User = get_user_model()
def _new_code(exclude_pk):
    # secrets, not random: reset codes must not be predictable.
    # Retry on a clash because ResetPasswordToken.key is unique.
    while True:
        code = str(secrets.randbelow(90000) + 10000)
        if not ResetPasswordToken.objects.exclude(pk=exclude_pk).filter(key=code).exists():
            return code

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an email is sent to the user with a 5-digit numeric code
    """
   
    numeric_token = _new_code(reset_password_token.pk)
    reset_password_token.key = numeric_token
    # A re-requested code must get a fresh expiry window.
    reset_password_token.created_at = timezone.now()
    reset_password_token.save()
    
    # Render the email template with the numeric token
    context = {
        'user': reset_password_token.user,
        'token': numeric_token,
        'username': reset_password_token.user.username,
    }
    
    # Render the email content from the template
    email_html_message = render_to_string('reset_password.html', context)
    email_plaintext_message = f"""
Hello,

You are receiving this email because you requested a password reset for your user account at Skholar.

Please enter the following 5-digit code in the app to reset your password:

{numeric_token}

Your username, in case you've forgotten: {reset_password_token.user.username}

Thanks for using our site!
The Skholar team
"""

    send_mail(
        # Subject
        "Password Reset for Skholar",
        # Plain text message
        email_plaintext_message,
        # From email
        settings.DEFAULT_FROM_EMAIL,
        # To email
        [reset_password_token.user.email],
        # HTML message
        html_message=email_html_message,
        fail_silently=False,
    )


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send a welcome email when a new user registers.
    Only sends on user creation (not updates).
    """
    if created and instance.email:
        context = {
            'username': instance.username,
            'email': instance.email,
        }
        
        # Render the welcome email template
        email_html_message = render_to_string('welcome_email.html', context)
        email_plaintext_message = f"""
Hello {instance.username},

Welcome to Skholar! We're excited to have you as part of our growing community of students.

With Skholar, you can:
- Access course materials anytime, anywhere
- Manage your class timetable with smart reminders
- Stay updated with campus news and gist
- Practice with CBT exams
- Get help from our AI assistant

If you have any questions or need help, feel free to reach out to us.

Best regards,
The Skholar Team
"""

        try:
            send_mail(
                "Welcome to Skholar!",
                email_plaintext_message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                html_message=email_html_message,
                fail_silently=True,  # Don't break registration if email fails
            )
        except Exception:
            # Log the error but don't prevent user registration
            pass

@receiver(post_save, sender=UserProfile)
def keep_department_history(sender, instance, **kwargs):
    """Every path that changes a department (registration, legacy profile
    update, admin) leaves a history row. A failure here must never break
    registration or a profile update, so it is logged and swallowed; the
    savepoint stops a database error from poisoning the outer transaction."""
    try:
        with transaction.atomic():
            sync_department_history(instance)
    except Exception:
        logger.exception("Could not record department history for user %s", instance.user_id)