from rest_framework import serializers
from .models import Exam, Question, Option, ExamSession

class OptionSerializer(serializers.ModelSerializer):
    # REVERTED: The frontend expects the answer text in a field named 'text'.
    # This correctly serializes the 'text' model field.
    class Meta:
        model = Option
        # UPDATED: The output fields are now 'id' and 'text', matching the frontend.
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    # This correctly sources from 'options' and outputs as 'answers' for the frontend.
    answers = OptionSerializer(many=True, read_only=True, source='options')

    class Meta:
        model = Question
        fields = ['id', 'text', 'qtype', 'marks', 'answers']

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['id','title','instructions','duration_minutes','shuffle_questions','is_published']

class ExamSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamSession
        fields = ['token','exam','student','started_at','submitted_at','status','score','answers_json']
        read_only_fields = ['token','started_at','submitted_at','status','score']
