from rest_framework import serializers
from .models import Exam, Question, Option, ExamSession

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    # RENAMED 'options' to 'answers' to match the Flutter app's expectation
    answers = OptionSerializer(many=True, read_only=True, source='options')

    class Meta:
        model = Question
        # UPDATED fields list to use the new name 'answers'
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
