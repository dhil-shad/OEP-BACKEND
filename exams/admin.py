from django.contrib import admin
from .models import Exam, Question, Option, Submission, Answer, ActivityLog

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ('text', 'exam', 'question_type', 'marks')
    list_filter = ('exam', 'question_type')

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class ExamAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'instructor', 'start_time', 'end_time', 'duration_minutes', 'is_active')
    list_filter = ('is_active', 'instructor')
    search_fields = ('title', 'description')

admin.site.register(Exam, ExamAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option)
admin.site.register(Submission)
admin.site.register(Answer)
admin.site.register(ActivityLog)
