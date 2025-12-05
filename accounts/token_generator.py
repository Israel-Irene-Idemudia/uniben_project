# accounts/token_generator.py
import random
from django_rest_passwordreset.tokens import BaseTokenGenerator


class NumericTokenGenerator(BaseTokenGenerator):
    """
    Generates a 5-digit numeric token for password reset.
    """
    
    def generate_token(self, *args, **kwargs) -> str:
        """
        Generate a random 5-digit numeric token.
        Returns a string like "12345", "00123", etc.
        """
        return str(random.randint(10000, 99999))
