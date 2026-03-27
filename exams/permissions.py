from rest_framework import permissions

class IsInstructor(permissions.BasePermission):
    """
    Custom permission to only allow instructors to edit objects.
    """
    def has_permission(self, request, view):
        return request.user and request.user.role == 'INSTRUCTOR'

class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow instructors to creat/edit. Students can read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.role == 'INSTRUCTOR'
        
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # For exams, only the instructor who created it can edit it
        if hasattr(obj, 'instructor'):
             return obj.instructor == request.user
        # For questions/options check the related exam
        if hasattr(obj, 'exam'):
             return obj.exam.instructor == request.user
        return False
