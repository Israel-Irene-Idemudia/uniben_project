# accounts/token_generator.py
import secrets
from django_rest_passwordreset.tokens import BaseTokenGenerator


class NumericTokenGenerator(BaseTokenGenerator):
    """
    Generates a 5-digit numeric token for password reset.
    """
    
    def generate_token(self, *args, **kwargs) -> str:
       
        return str(secrets.randbelow(90000) + 10000)
