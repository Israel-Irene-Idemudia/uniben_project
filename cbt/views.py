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
# UPDATED: Imported the new ReviewQuestionSerializer
from .serializers import ExamSerializer, QuestionSerializer, ReviewQuestionSerializer, ExamSessionSerializer
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
        course_id = self.kwargs['course_id']
        return Exam.objects.filter(course_id=course_id)

def grade_session(session: ExamSession):
    total = Decimal('0')
    exam = session.exam
    for eq in exam.exam_questions.select_related('question').all():
        q = eq.question
        ans = session.answers_json.get(str(q.id), {})
        if q.qtype in (Question.QTYPE_MCQ, Question.QTYPE_MULTI):
            selected = ans.get('selected_option_ids', [])
            correct_ids = list(q.options.filter(is_correct=True).values_list('id', flat=True))
            if set(map(int, selected)) == set(map(int, correct_ids)):
                total += q.marks
            else:
                total -= exam.negative_mark or Decimal('0')
        else:
            pass
    session.score = max(total, Decimal('0'))
    session.status = ExamSession.STATUS_SUBMITTED
    session.submitted_at = timezone.now()
    session.save()
    return session.score

class StartExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        session = ExamSession.objects.create(
            exam=exam,
            student=request.user,
            started_at=timezone.now(),
            status=ExamSession.STATUS_IN_PROGRESS,
            ip_address=request.META.get('REMOTE_ADDR',''),
            device_info=request.META.get('HTTP_USER_AGENT','')
        )
        eqs = ExamQuestion.objects.filter(exam=exam).select_related('question')
        questions = []
        for eq in eqs:
            q = eq.question
            questions.append(QuestionSerializer(q).data)
        
        if exam.shuffle_questions:
            random.shuffle(questions)
            for q in questions:
                if 'answers' in q and q['answers']:
                    random.shuffle(q['answers'])

        return Response({
            'session_token': session.token,
            'questions': questions,
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
        return Response({'status':'ok'})

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

        # MODIFIED: Get all questions from the exam again to prepare the review data.
        exam = session.exam
        eqs = ExamQuestion.objects.filter(exam=exam).select_related('question')
        questions_for_review = []
        for eq in eqs:
            q = eq.question
            # Use the new ReviewQuestionSerializer to include correct answers.
            questions_for_review.append(ReviewQuestionSerializer(q).data)

        # Return the graded score AND the full questions data for review.
        return Response({
            'status': 'submitted',
            'score': str(session.score),
            'questions': questions_for_review
        })
