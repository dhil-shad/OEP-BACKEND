from django.urls import path
from .views import RegisterView, UserProfileView, JoinInstitutionView, InstitutionRequestsView, RespondJoinRequestView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('join-institution/', JoinInstitutionView.as_view(), name='join_institution'),
    path('institution/requests/', InstitutionRequestsView.as_view(), name='institution_requests'),
    path('institution/requests/<int:pk>/respond/', RespondJoinRequestView.as_view(), name='respond_request'),
]
