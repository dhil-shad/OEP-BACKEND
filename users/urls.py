from django.urls import path
from .views import (
    RegisterView, UserProfileView, JoinInstitutionView, 
    InstitutionRequestsView, RespondJoinRequestView, 
    DepartmentViewSet, NotificationViewSet,
    PublicInstitutionDepartmentsView, InstitutionStudentsView,
    InstitutionStudentActionView, InstitutionInstructorsView,
    DepartmentStudentsView, SectionViewSet, PublicDepartmentSectionsView,
    StudyClassViewSet, PublicSectionClassesView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('join-institution/', JoinInstitutionView.as_view(), name='join_institution'),
    path('public/institutions/<str:uid>/departments/', PublicInstitutionDepartmentsView.as_view(), name='public-departments'),
    path('public/departments/<int:dept_id>/sections/', PublicDepartmentSectionsView.as_view(), name='public-sections'),
    path('public/sections/<int:section_id>/classes/', PublicSectionClassesView.as_view(), name='public-classes'),
    path('institution/requests/', InstitutionRequestsView.as_view(), name='institution_requests'),
    path('institution/requests/<int:pk>/respond/', RespondJoinRequestView.as_view(), name='respond_request'),
    path('institution/students/', InstitutionStudentsView.as_view(), name='institution-students'),
    path('institution/instructors/', InstitutionInstructorsView.as_view(), name='institution-instructors'),
    path('department/students/', DepartmentStudentsView.as_view(), name='department-students'),
    path('institution/students/<int:pk>/action/', InstitutionStudentActionView.as_view(), name='institution-student-action'),
    path('departments/', DepartmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='department-list'),
    path('departments/<int:pk>/', DepartmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='department-detail'),
    path('notifications/', NotificationViewSet.as_view({'get': 'list'}), name='notification-list'),
    path('notifications/<int:pk>/', NotificationViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='notification-detail'),
    path('sections/', SectionViewSet.as_view({'get': 'list', 'post': 'create'}), name='section-list'),
    path('sections/<int:pk>/', SectionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='section-detail'),
    path('classes/', StudyClassViewSet.as_view({'get': 'list', 'post': 'create'}), name='class-list'),
    path('classes/<int:pk>/', StudyClassViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='class-detail'),
]
