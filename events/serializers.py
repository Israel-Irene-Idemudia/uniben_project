from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    # Explicitly handle image field to return full URL
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Event
        fields = '__all__'

