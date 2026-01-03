from rest_framework import serializers
from .models import Exam, Question, Option, ExamSession, DebaterQuestion

# Serializer for when a user is TAKING a quiz.
# It intentionally hides the 'is_correct' field.
class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text']

# Serializer for when a user is REVIEWING a quiz.
# It INCLUDES the 'is_correct' field.
class CorrectAnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct']

# Serializer for the questions during a quiz.
class QuestionSerializer(serializers.ModelSerializer):
    answers = OptionSerializer(many=True, read_only=True, source='options')
    class Meta:
        model = Question
        fields = ['id', 'text', 'qtype', 'marks', 'answers']

# Serializer for the questions during review.
class ReviewQuestionSerializer(serializers.ModelSerializer):
    answers = CorrectAnswerOptionSerializer(many=True, read_only=True, source='options')
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


class DebaterQuestionSerializer(serializers.ModelSerializer):
    """Serializer for Debater game questions"""
    class Meta:
        model = DebaterQuestion
        fields = ['id', 'statement', 'answer', 'category']
