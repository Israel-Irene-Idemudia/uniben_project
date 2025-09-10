from django.shortcuts import render
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Course, Question
from .serializers import CourseSerializer, QuestionSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # GET /api/courses/{id}/questions/
    @action(detail=True, methods=["get"])
    def questions(self, request, pk=None):
        course = self.get_object()
        serializer = QuestionSerializer(course.questions.all(), many=True)
        return Response(serializer.data)

    # POST /api/courses/{id}/submit/
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        course = self.get_object()
        question_id = request.data.get("question_id")
        selected = request.data.get("selected")

        try:
            question = course.questions.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"error": "Question not found"}, status=404)

        correct = (selected == question.answer)
        return Response({"correct": correct, "score": 1 if correct else 0})


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
