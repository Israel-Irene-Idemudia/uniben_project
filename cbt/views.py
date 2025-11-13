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
        # Students should only see courses they are subscribed to that have quizzes
        # This requires a proper subscription model which is assumed for this query
        return Course.objects.annotate(
            has_exams=Exists(Exam.objects.filter(course=OuterRef('pk')))
        ).filter(has_exams=True)


class ExamListView(generics.ListAPIView):
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Exam.objects.filter(course_id=course_id)


# BUG FIX: Score calculation logic is now robust.
def grade_session(session: ExamSession):
    total_marks = Decimal('0')
    answers = session.answers_json or {}

    # Get all question IDs for this exam session to ensure we grade all of them
    all_question_ids = {str(eq.question.id) for eq in session.exam.exam_questions.all()}

    for q_id_str in all_question_ids:
        question = Question.objects.get(id=int(q_id_str))
        user_answer = answers.get(q_id_str)

        # Safely get the selected option ID
        selected_option_id = None
        if user_answer and 'selected_option_id' in user_answer:
            try:
                selected_option_id = int(user_answer['selected_option_id'])
            except (ValueError, TypeError):
                selected_option_id = None # Handle cases where the ID is not a valid integer

        # Get the correct option ID for the question
        correct_option = question.options.filter(is_correct=True).first()

        if correct_option and selected_option_id == correct_option.id:
            total_marks += question.marks
        else:
            # Apply negative marking only if an answer was submitted and it was wrong
            if selected_option_id is not None:
                total_marks -= session.exam.negative_mark or Decimal('0')
    
    # Score cannot be negative
    session.score = max(total_marks, Decimal('0'))
    session.status = ExamSession.STATUS_SUBMITTED
    session.submitted_at = timezone.now()
    session.save()

class StartExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        num_questions_str = request.data.get('num_questions')

        session = ExamSession.objects.create(
            exam=exam,
            student=request.user,
            started_at=timezone.now(),
            status=ExamSession.STATUS_IN_PROGRESS,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            device_info=request.META.get('HTTP_USER_AGENT', '')
        )

        # Fetch all questions for the exam
        all_questions = list(Question.objects.filter(examquestion__exam=exam))
        
        # Shuffle all questions before slicing
        if exam.shuffle_questions:
            random.shuffle(all_questions)

        # BUG FIX: Respect the num_questions parameter.
        try:
            num_questions = int(num_questions_str)
            if num_questions > 0:
                questions_to_send = all_questions[:num_questions]
            else:
                questions_to_send = all_questions
        except (ValueError, TypeError):
            questions_to_send = all_questions

        # Serialize the final list of questions
        serialized_questions = QuestionSerializer(questions_to_send, many=True).data

        # Shuffle options within each question if enabled
        if exam.shuffle_questions:
            for q_data in serialized_questions:
                if 'options' in q_data:
                    random.shuffle(q_data['options'])

        return Response({
            'session_token': session.token,
            'quiz_title': f"{exam.course.code} - {exam.name}",
            'questions': serialized_questions,
            'duration_minutes': exam.duration_minutes
        })

class AutoSaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        session = get_object_or_404(ExamSession, token=token, student=request.user)
        answers = request.data.get('answers', {})
        data = session.answers_json or {}
        data.update(answers)
        session.answers_json = data
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

        # Grade the session using the corrected logic
        grade_session(session)

        # BUG FIX: Prepare and send the full data required for review.
        all_exam_questions = Question.objects.filter(examquestion__exam=session.exam)
        review_data = ReviewQuestionSerializer(all_exam_questions, many=True).data

        return Response({
            'status': 'submitted',
            'score': f"{session.score} Points",
            'review_data': {
                'questions': review_data,
                'selected_answers': session.answers_json or {}
            }
        })
