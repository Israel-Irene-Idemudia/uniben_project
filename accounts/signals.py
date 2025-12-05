# accounts/signals.py
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from django_rest_passwordreset.signals import reset_password_token_created


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
