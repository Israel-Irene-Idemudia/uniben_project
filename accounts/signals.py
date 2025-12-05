# accounts/signals.py
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django_rest_passwordreset.signals import reset_password_token_created


User = get_user_model()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an email is sent to the user
    """
    # Render the email template with the token and user
    context = {
        'user': reset_password_token.user,
        'token': reset_password_token.key,
        'username': reset_password_token.user.username,
    }
    
    # Render the email content from the template
    email_html_message = render_to_string('reset_password.html', context)
    email_plaintext_message = f"""
Hello,

You are receiving this email because you requested a password reset for your user account at Skholar.

Please enter the following code in the app to reset your password:

{reset_password_token.key}

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
