from django.contrib import admin

from . import models


@admin.register(models.Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'term', 'professor', 'created_at')
    search_fields = ('title', 'term', 'professor__username', 'professor__email')


@admin.register(models.Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'role_in_class', 'status', 'created_at')
    search_fields = ('course__title', 'user__username', 'user__email')


@admin.register(models.ProblemSet)
class ProblemSetAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'release_at', 'due_at', 'created_at')
    search_fields = ('title', 'course__title')


@admin.register(models.Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'problem_set', 'max_score', 'order', 'created_at')
    search_fields = ('title', 'problem_set__title')


@admin.register(models.Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('problem', 'version', 'total_points', 'created_at')


@admin.register(models.RubricItem)
class RubricItemAdmin(admin.ModelAdmin):
    list_display = ('rubric', 'label', 'points', 'order')


@admin.register(models.Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('problem', 'student', 'submitted_at', 'status', 'final_score')
    search_fields = ('problem__title', 'student__username', 'student__email')


@admin.register(models.SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ('submission', 'file', 'mime_type', 'page_number')


@admin.register(models.AutoGradeRun)
class AutoGradeRunAdmin(admin.ModelAdmin):
    list_display = ('submission', 'model', 'score', 'created_at')


@admin.register(models.Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('submission', 'grader_type', 'score', 'finalized_at')


@admin.register(models.Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ('submission', 'student', 'status', 'created_at')


@admin.register(models.AppealMessage)
class AppealMessageAdmin(admin.ModelAdmin):
    list_display = ('appeal', 'author', 'created_at')
