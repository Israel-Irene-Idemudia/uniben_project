
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, generics
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from django.db.models import Exists, OuterRef, Prefetch
import random

from .models import Exam, ExamSession, Question, Option
from .serializers import ExamSerializer, QuestionSerializer, ReviewQuestionSerializer
from core.models import Course
from core.serializers import CourseSerializer


class UserSubscribedCoursesWithQuizzes(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Using distinct on a specific field after ordering is a way to get unique items
        # based on that field. We also prefetch exams to be efficient.
        unique_courses_with_exams = Course.objects.annotate(
            has_exams=Exists(Exam.objects.filter(course=OuterRef('pk')))
        ).filter(has_exams=True).order_by('code', 'id').distinct('code')
        
        serializer = CourseSerializer(unique_courses_with_exams, many=True)
        return Response(serializer.data)


class ExamListView(generics.ListAPIView):
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Exam.objects.filter(course_id=course_id)


def grade_session(session: ExamSession):
    total_marks = Decimal('0')
    answers = session.answers_json or {}
    session_question_ids = answers.keys()

    # Efficiently fetch all questions and their correct options at once
    questions = Question.objects.filter(
        id__in=[int(q_id) for q_id in session_question_ids]
    ).prefetch_related(
        Prefetch('options', queryset=Option.objects.filter(is_correct=True), to_attr='correct_options')
    )
    question_map = {str(q.id): q for q in questions}

    for q_id_str in session_question_ids:
        question = question_map.get(q_id_str)
        if not question:
            continue

        user_answer = answers.get(q_id_str)
        if not user_answer:
            continue

        selected_option_id = None
        if 'selected_option_id' in user_answer:
            try:
                selected_option_id = int(user_answer['selected_option_id'])
            except (ValueError, TypeError):
                pass

        # Use the prefetched correct option
        correct_option = question.correct_options[0] if hasattr(question, 'correct_options') and question.correct_options else None

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
        # --- FIX: Prefetch all related questions and their options in one go ---
        exam = get_object_or_404(
            Exam.objects.prefetch_related('exam_questions__question__options'), 
            pk=exam_id
        )
        # --- END FIX ---
        
        num_questions_req = request.data.get('num_questions')

        # The 'exam_questions' are ExamQuestion linker model instances.
        # We pre-fetched the related 'question' and its 'options' so this is now efficient.
        all_questions = [eq.question for eq in exam.exam_questions.all()]

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
        
        initial_answers = {str(q.id): {} for q in questions_to_send}

        session = ExamSession.objects.create(
            exam=exam,
            student=request.user,
            started_at=timezone.now(),
            status=ExamSession.STATUS_IN_PROGRESS,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            answers_json=initial_answers
        )

        serialized_questions = QuestionSerializer(questions_to_send, many=True).data

        return Response({
            'session_token': session.token,
            'quiz_title': f"{exam.course.code} - {exam.title}",
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

        grade_session(session)

        session_question_ids = session.answers_json.keys()
        
        # --- FIX: Prefetch options to prevent N+1 queries ---
        questions_for_review = Question.objects.filter(
            id__in=session_question_ids
        ).prefetch_related('options')
        # --- END FIX ---

        q_map = {str(q.id): q for q in questions_for_review}
        ordered_questions = [q_map[qid] for qid in session_question_ids if qid in q_map]

        review_data = ReviewQuestionSerializer(ordered_questions, many=True).data

        return Response({
            'status': 'submitted',
            'score': f"{session.score} Points",
            'review_data': {
                'questions': review_data,
                'selected_answers': session.answers_json or {}
            }
        }, status=status.HTTP_200_OK)
