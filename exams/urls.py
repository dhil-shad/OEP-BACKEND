from django.urls import path, include
from rest_framework_nested import routers
from rest_framework import routers as standalone_routers
from .views import ExamViewSet, QuestionViewSet, SubmissionViewSet

router = routers.DefaultRouter()
router.register(r'', ExamViewSet, basename='exam')

exams_router = routers.NestedDefaultRouter(router, r'', lookup='exam')
exams_router.register(r'questions', QuestionViewSet, basename='exam-questions')
exams_router.register(r'submissions', SubmissionViewSet, basename='exam-submissions')

# Add a separate standalone router to access all submissions cleanly without needing exam ID in url
submission_router = standalone_routers.DefaultRouter()
submission_router.register(r'submissions', SubmissionViewSet, basename='all-submissions')

urlpatterns = [
    path('', include(submission_router.urls)), # /api/exams/submissions/
    path('', include(router.urls)),            # /api/exams/
    path('', include(exams_router.urls)),      # /api/exams/<id>/...
]
