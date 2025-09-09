from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal

from .models import Exam, ExamSession, ExamQuestion, Question, Option
from .serializers import ExamSerializer, QuestionSerializer, ExamSessionSerializer

def grade_session(session: ExamSession):
    total = Decimal('0')
    exam = session.exam
    for eq in exam.exam_questions.select_related('question').all():
        q = eq.question
        ans = session.answers_json.get(str(q.id), {})
        if q.qtype in (Question.QTYPE_MCQ, Question.QTYPE_MULTI):
            selected = ans.get('selected_option_ids', [])
            correct_ids = list(q.options.filter(is_correct=True).values_list('id', flat=True))
            # exact set match => award full marks
            if set(map(int, selected)) == set(map(int, correct_ids)):
                total += q.marks
            else:
                # apply negative mark if configured:
                total -= exam.negative_mark or Decimal('0')
        else:
            # text answers require manual grading -> skip here
            pass
    session.score = max(total, Decimal('0'))
    session.status = ExamSession.STATUS_SUBMITTED
    session.submitted_at = timezone.now()
    session.save()
    return session.score

class ExamListView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get(self, request):
        exams = Exam.objects.filter(is_published=True)
        return Response(ExamSerializer(exams, many=True).data)

class StartExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id, is_published=True)
        # Optionally: check enrollment / start_time / end_time here
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
        import random
        if exam.shuffle_questions:
            random.shuffle(questions)
            for q in questions:
                if 'options' in q:
                    random.shuffle(q['options'])
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
        # merge answers into session.answers_json
        data = session.answers_json or {}
        data.update(answers)
        session.answers_json = data
        session.save()
        return Response({'status':'ok'})

class SubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, token):
        session = get_object_or_404(ExamSession, token=token, student=request.user)
        # final merge (accept latest answers in payload if provided)
        answers = request.data.get('answers')
        if isinstance(answers, dict):
            data = session.answers_json or {}
            data.update(answers)
            session.answers_json = data
            session.save()
        # Run grading for objective Qs (subjective will need manual grading)
        grade_session(session)
        return Response({'status':'submitted','score':str(session.score)})

