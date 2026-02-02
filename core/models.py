from django.conf import settings
from django.db import models
from django.utils import timezone


class Class(models.Model):
    title = models.CharField(max_length=200)
    term = models.CharField(max_length=100, blank=True)
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='classes_taught',
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.title} ({self.term})" if self.term else self.title


class Enrollment(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
    ]

    course = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role_in_class = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['course', 'user'], name='uniq_enrollment'),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.course}"


class ProblemSet(models.Model):
    course = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='problem_sets')
    title = models.CharField(max_length=200)
    release_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.title} ({self.course})"


class Problem(models.Model):
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name='problems')
    title = models.CharField(max_length=200)
    prompt_pdf = models.FileField(upload_to='problem_prompts/')
    max_score = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return f"{self.title} ({self.problem_set})"


class Rubric(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='rubrics')
    version = models.PositiveIntegerField(default=1)
    total_points = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['problem', 'version'], name='uniq_rubric_version'),
        ]
        ordering = ['-version', 'id']

    def __str__(self) -> str:
        return f"Rubric v{self.version} for {self.problem}"


class RubricItem(models.Model):
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=255)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return f"{self.label} ({self.points} pts)"


class Submission(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_GRADED = 'graded'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_GRADED, 'Graded'),
    ]

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    final_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['problem', 'student'], name='uniq_submission'),
        ]

    def __str__(self) -> str:
        return f"Submission for {self.problem} by {self.student}"


class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='submissions/')
    mime_type = models.CharField(max_length=100, blank=True)
    page_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['page_number', 'id']

    def __str__(self) -> str:
        return f"File {self.page_number} for {self.submission_id}"


class AutoGradeRun(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='autograde_runs')
    rubric = models.ForeignKey(Rubric, on_delete=models.SET_NULL, null=True, blank=True)
    model = models.CharField(max_length=100)
    raw_output_json = models.JSONField()
    score = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"AutoGrade {self.submission_id} ({self.score})"


class Grade(models.Model):
    GRADER_AUTO = 'auto'
    GRADER_PROFESSOR = 'professor'
    GRADER_CHOICES = [
        (GRADER_AUTO, 'Auto'),
        (GRADER_PROFESSOR, 'Professor'),
    ]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='grades')
    rubric = models.ForeignKey(Rubric, on_delete=models.SET_NULL, null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    feedback = models.TextField(blank=True)
    grader_type = models.CharField(max_length=20, choices=GRADER_CHOICES)
    grader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grades_given',
    )
    finalized_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.grader_type} grade {self.score} for {self.submission_id}"


class Appeal(models.Model):
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='appeals')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Appeal for {self.submission_id}"


class AppealMessage(models.Model):
    appeal = models.ForeignKey(Appeal, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self) -> str:
        return f"Message for appeal {self.appeal_id}"
