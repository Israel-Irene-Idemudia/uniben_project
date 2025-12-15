
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
    import logging
    logger = logging.getLogger(__name__)
    
    total_marks = Decimal('0')
    answers = session.answers_json or {}
    session_question_ids = answers.keys()
    
    logger.info(f"=== GRADING SESSION {session.token[:8]} ===")
    logger.info(f"Total questions answered: {len(session_question_ids)}")
    logger.info(f"Answers JSON: {answers}")

    # Fetch all questions with ALL their options
    questions = Question.objects.filter(
        id__in=[int(q_id) for q_id in session_question_ids]
    ).prefetch_related('options')
    
    question_map = {str(q.id): q for q in questions}
    logger.info(f"Questions fetched: {len(question_map)}")

    for q_id_str in session_question_ids:
        question = question_map.get(q_id_str)
        if not question:
            logger.warning(f"Question {q_id_str} not found in map")
            continue

        user_answer = answers.get(q_id_str)
        if not user_answer:
            logger.warning(f"No answer for question {q_id_str}")
            continue
        
        logger.info(f"Q{q_id_str}: user_answer={user_answer}, type={type(user_answer)}")

        selected_option_id = None
        if isinstance(user_answer, dict):
            selected_option_id = user_answer.get('selected_option_id')
            logger.info(f"Q{q_id_str}: Extracted from dict: {selected_option_id}")
        else:
            # Handle case where answer is just the option ID directly
            selected_option_id = user_answer
            logger.info(f"Q{q_id_str}: Direct value: {selected_option_id}")

        if selected_option_id is not None:
            try:
                selected_option_id = int(selected_option_id)
                logger.info(f"Q{q_id_str}: Converted to int: {selected_option_id}")
            except (ValueError, TypeError):
                logger.error(f"Q{q_id_str}: Failed to convert {selected_option_id} to int")
                selected_option_id = None

        # Find the correct option by iterating through all options
        correct_option = None
        for opt in question.options.all():
            if opt.is_correct:
                correct_option = opt
                break
        
        if correct_option:
            logger.info(f"Q{q_id_str}: Correct option ID={correct_option.id}")
            logger.info(f"Q{q_id_str}: Selected={selected_option_id}, Match={selected_option_id == correct_option.id}")
        else:
            logger.error(f"Q{q_id_str}: NO CORRECT OPTION FOUND!")

        if correct_option and selected_option_id == correct_option.id:
            total_marks += question.marks
            logger.info(f"Q{q_id_str}: CORRECT! +{question.marks} marks. Total: {total_marks}")
        elif selected_option_id is not None:
            penalty = session.exam.negative_mark or Decimal('0')
            total_marks -= penalty
            logger.info(f"Q{q_id_str}: WRONG! -{penalty} marks. Total: {total_marks}")


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
        
        # FIX: Frontend sends answers directly as body, not nested under 'answers' key
        # request.data is already the map: {"question_id": option_id, ...}
        answers = request.data
        
        if isinstance(answers, dict) and answers:
            # Replace session answers completely (don't merge with empty initialization)
            session.answers_json = answers
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
