from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, generics
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from django.db.models import Exists, OuterRef
import random

from .models import Exam, ExamSession, ExamQuestion, Question, Option
from .serializers import ExamSerializer, QuestionSerializer, ReviewQuestionSerializer
from core.models import Course
from core.serializers import CourseSerializer


class UserSubscribedCoursesWithQuizzes(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.annotate(
            has_exams=Exists(Exam.objects.filter(course=OuterRef('pk')))
        ).filter(has_exams=True)


class ExamListView(generics.ListAPIView):
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Exam.objects.filter(course_id=course_id)


def grade_session(session: ExamSession):
    total_marks = Decimal('0')
    answers = session.answers_json or {}
    all_question_ids = {str(eq.question.id) for eq in session.exam.exam_questions.all()}

    for q_id_str in all_question_ids:
        try:
            question = Question.objects.get(id=int(q_id_str))
        except Question.DoesNotExist:
            continue

        user_answer = answers.get(q_id_str)
        selected_option_id = None
        if user_answer and 'selected_option_id' in user_answer:
            try:
                selected_option_id = int(user_answer['selected_option_id'])
            except (ValueError, TypeError):
                selected_option_id = None

        correct_option = question.options.filter(is_correct=True).first()

        if correct_option and selected_option_id == correct_option.id:
            total_marks += question.marks
        elif selected_option_id is not None:
            total_marks -= session.exam.negative_mark or Decimal('0')

    session.score = max(total_marks, Decimal('0'))
    session.status = ExamSession.STATUS_SUBMITTED
    session.submitted_at = timezone.now()
    session.save()

class StartExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        num_questions_req = request.data.get('num_questions')

        session = ExamSession.objects.create(
            exam=exam,
            student=request.user,
            started_at=timezone.now(),
            status=ExamSession.STATUS_IN_PROGRESS,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            device_info=request.META.get('HTTP_USER_AGENT', '')
        )

        # THE DEFINITIVE FIX: Correctly query questions through the ExamQuestion model.
        exam_questions = exam.exam_questions.all()
        all_questions = [eq.question for eq in exam_questions]

        if exam.shuffle_questions:
            random.shuffle(all_questions)

        questions_to_send = all_questions
        if num_questions_req is not None:
            try:
                num_questions = int(num_questions_req)
                if num_questions > 0:
                    questions_to_send = all_questions[:num_questions]
            except (ValueError, TypeError):
                pass

        serialized_questions = QuestionSerializer(questions_to_send, many=True).data

        if exam.shuffle_questions:
            for q_data in serialized_questions:
                if 'options' in q_data:
                    random.shuffle(q_data['options'])

        return Response({
            'session_token': session.token,
            'quiz_title': f"{exam.course.code} - {exam.title}", # Corrected from exam.name
            'questions': serialized_questions,
            'duration_minutes': exam.duration_minutes
        }, status=status.HTTP_200_OK)

class AutoSaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        session = get_object_or_404(ExamSession, token=token, student=request.user)
        answers = request.data.get('answers', {})
        data = session.answers_json or {}
        data.update(answers)
        session.save()
        return Response({'status': 'ok'})

class SubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        session = get_object_or_404(ExamSession, token=token, student=request.user)
        answers = request.data.get('answers')
        
        if isinstance(answers, dict):
            data = session.answers_json or {}
            data.update(answers)
            session.answers_json = data
            session.save()

        grade_session(session)

        # Correctly get questions for review.
        exam_questions = session.exam.exam_questions.all()
        all_exam_questions = [eq.question for eq in exam_questions]
        review_data = ReviewQuestionSerializer(all_exam_questions, many=True).data

        return Response({
            'status': 'submitted',
            'score': f"{session.score} Points",
            'review_data': {
                'questions': review_data,
                'selected_answers': session.answers_json or {}
            }
        }, status=status.HTTP_200_OK)
