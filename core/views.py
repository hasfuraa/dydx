from io import BytesIO

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Avg
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import forms, models, services
from .decorators import professor_required, student_required
from django.contrib.auth.forms import PasswordChangeForm


@login_required
def dashboard(request):
    if request.user.is_staff:
        return professor_dashboard(request)
    return student_dashboard(request)


@professor_required
def professor_dashboard(request):
    classes = models.Class.objects.filter(professor=request.user)
    class_cards = []
    for course in classes:
        enrollments = course.enrollments.count()
        problem_sets = course.problem_sets.prefetch_related('problems')
        ps_stats = []
        for ps in problem_sets:
            problem_count = ps.problems.count()
            expected = enrollments * problem_count if problem_count else 0
            submitted = models.Submission.objects.filter(problem__problem_set=ps).count()
            percent = round((submitted / expected) * 100, 1) if expected else 0
            avg_score = models.Submission.objects.filter(problem__problem_set=ps).aggregate(
                avg=Avg('final_score')
            )['avg']
            ps_stats.append(
                {
                    'id': ps.id,
                    'title': ps.title,
                    'due_at': ps.due_at,
                    'percent': percent,
                    'avg_score': avg_score,
                }
            )
        class_cards.append({'course': course, 'problem_sets': ps_stats})

    appeals_open = models.Appeal.objects.filter(status=models.Appeal.STATUS_OPEN).count()

    context = {
        'class_cards': class_cards,
        'appeals_open': appeals_open,
    }
    return render(request, 'dashboard_professor.html', context)


@student_required
def student_dashboard(request):
    enrollments = models.Enrollment.objects.filter(user=request.user).select_related('course')
    courses = [e.course for e in enrollments]

    upcoming = (
        models.ProblemSet.objects.filter(course__in=courses, due_at__isnull=False)
        .order_by('due_at')
        .select_related('course')
    )

    submissions = models.Submission.objects.filter(student=request.user)

    context = {
        'enrollments': enrollments,
        'upcoming': upcoming,
        'submissions': submissions,
        'now': timezone.now(),
    }
    return render(request, 'dashboard_student.html', context)


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = forms.StudentSignUpForm(request.POST)
        if form.is_valid():
            user_model = get_user_model()
            email = form.cleaned_data['email'].strip().lower()
            username = form.cleaned_data['username'].strip() or email
            password = form.cleaned_data['password']
            if user_model.objects.filter(username=username).exists():
                return render(request, 'registration/signup.html', {'form': form, 'error': 'Username already taken.'})
            if user_model.objects.filter(email=email).exists():
                return render(request, 'registration/signup.html', {'form': form, 'error': 'Email already in use.'})
            user = user_model.objects.create_user(username=username, email=email, password=password)
            login(request, user, backend='core.auth_backends.EmailOrUsernameBackend')
            return redirect('dashboard')
    else:
        form = forms.StudentSignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@professor_required
def admin_password_reset(request):
    message = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        if not email or not password:
            message = 'Email and new password are required.'
        else:
            user_model = get_user_model()
            try:
                user = user_model.objects.get(email=email)
                user.set_password(password)
                user.save(update_fields=['password'])
                message = f'Password reset for {user.email}.'
            except user_model.DoesNotExist:
                message = 'No user found with that email.'
    return render(request, 'professor/admin_reset.html', {'message': message})


@student_required
def student_password_change(request):
    message = None
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            message = 'Password updated.'
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'student/password_change.html', {'form': form, 'message': message})


@professor_required
def class_list(request):
    classes = models.Class.objects.filter(professor=request.user)
    return render(request, 'professor/class_list.html', {'classes': classes})


@professor_required
def class_create(request):
    if request.method == 'POST':
        form = forms.ClassForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.professor = request.user
            course.save()
            return redirect('class_detail', class_id=course.id)
    else:
        form = forms.ClassForm()
    return render(request, 'professor/class_form.html', {'form': form})


@professor_required
def class_detail(request, class_id: int):
    course = get_object_or_404(models.Class, id=class_id, professor=request.user)
    problem_sets = course.problem_sets.all()
    enrollments = course.enrollments.select_related('user')
    return render(
        request,
        'professor/class_detail.html',
        {'course': course, 'problem_sets': problem_sets, 'enrollments': enrollments},
    )


@professor_required
def enrollment_add(request, class_id: int):
    course = get_object_or_404(models.Class, id=class_id, professor=request.user)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            return render(
                request,
                'professor/enrollment_add.html',
                {'course': course, 'error': 'Email is required.'},
            )
        user_model = get_user_model()
        user = get_object_or_404(user_model, email=email)
        models.Enrollment.objects.get_or_create(course=course, user=user)
        return redirect('class_detail', class_id=class_id)
    return render(request, 'professor/enrollment_add.html', {'course': course})


@professor_required
def problem_set_create(request, class_id: int):
    course = get_object_or_404(models.Class, id=class_id, professor=request.user)
    if request.method == 'POST':
        form = forms.ProblemSetForm(request.POST)
        if form.is_valid():
            ps = form.save(commit=False)
            ps.course = course
            ps.save()
            return redirect('problem_set_detail', problem_set_id=ps.id)
    else:
        form = forms.ProblemSetForm()
    return render(request, 'professor/problem_set_form.html', {'form': form, 'course': course})


@professor_required
def problem_set_detail(request, problem_set_id: int):
    ps = get_object_or_404(models.ProblemSet, id=problem_set_id, course__professor=request.user)
    problems = ps.problems.all()
    return render(request, 'professor/problem_set_detail.html', {'problem_set': ps, 'problems': problems})


@professor_required
def problem_create(request, problem_set_id: int):
    ps = get_object_or_404(models.ProblemSet, id=problem_set_id, course__professor=request.user)
    error = None
    if request.method == 'POST':
        form = forms.ProblemForm(request.POST, request.FILES)
        if form.is_valid():
            problem = form.save(commit=False)
            problem.problem_set = ps
            problem.save()
            try:
                services.infer_default_rubric(problem, version=1)
                return redirect('problem_detail', problem_id=problem.id)
            except Exception as exc:
                error = str(exc)
    else:
        form = forms.ProblemForm()
    return render(request, 'professor/problem_form.html', {'form': form, 'problem_set': ps, 'error': error})


@professor_required
def problem_detail(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__professor=request.user)
    rubric = services.get_active_rubric(problem)
    submissions = (
        models.Submission.objects.filter(problem=problem)
        .select_related('student')
        .prefetch_related('files')
        .order_by('student__email')
    )
    return render(
        request,
        'professor/problem_detail.html',
        {'problem': problem, 'rubric': rubric, 'submissions': submissions},
    )


@login_required
def problem_prompt_preview(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id)
    if request.user.is_staff:
        if problem.problem_set.course.professor_id != request.user.id:
            raise Http404('Not found')
    else:
        if not models.Enrollment.objects.filter(course=problem.problem_set.course, user=request.user).exists():
            raise Http404('Not found')
    if not problem.prompt_pdf:
        raise Http404('No prompt PDF')
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise Http404('PDF preview unavailable') from exc

    try:
        pdf = pdfium.PdfDocument(problem.prompt_pdf.path)
    except FileNotFoundError:
        raise Http404('Prompt PDF not found on server')
    if len(pdf) < 1:
        raise Http404('PDF has no pages')
    page = pdf[0]
    image = page.render(scale=2).to_pil()
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@professor_required
def problem_delete(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__professor=request.user)
    if request.method == 'POST':
        problem_set_id = problem.problem_set_id
        problem.delete()
        return redirect('problem_set_detail', problem_set_id=problem_set_id)
    return render(request, 'professor/problem_delete.html', {'problem': problem})


@professor_required
def rubric_regenerate(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__professor=request.user)
    if request.method != 'POST':
        return redirect('problem_detail', problem_id=problem.id)

    error = None
    try:
        latest = services.get_active_rubric(problem)
        next_version = (latest.version + 1) if latest else 1
        suggestion = request.POST.get('rubric_suggestion', '')
        services.infer_default_rubric(problem, version=next_version, suggestion=suggestion)
        return redirect('problem_detail', problem_id=problem.id)
    except Exception as exc:
        error = str(exc)
        rubric = services.get_active_rubric(problem)
        return render(
            request,
            'professor/problem_detail.html',
            {'problem': problem, 'rubric': rubric, 'error': error},
        )


@professor_required
def rubric_edit(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__professor=request.user)
    rubric = services.get_active_rubric(problem)
    if rubric is None:
        raise Http404('Rubric not found')

    formset = forms.RubricItemFormSet(queryset=rubric.items.all())
    if request.method == 'POST':
        formset = forms.RubricItemFormSet(request.POST, queryset=rubric.items.all())
        if formset.is_valid():
            formset.save()
            return redirect('problem_detail', problem_id=problem.id)
    return render(
        request,
        'professor/rubric_edit.html',
        {'problem': problem, 'rubric': rubric, 'formset': formset},
    )


@student_required
def student_class_list(request):
    enrollments = models.Enrollment.objects.filter(user=request.user).select_related('course')
    return render(request, 'student/class_list.html', {'enrollments': enrollments})


@student_required
def student_class_detail(request, class_id: int):
    enrollment = get_object_or_404(models.Enrollment, course_id=class_id, user=request.user)
    problem_sets = enrollment.course.problem_sets.all()
    return render(
        request,
        'student/class_detail.html',
        {'course': enrollment.course, 'problem_sets': problem_sets},
    )


@student_required
def student_problem_set_detail(request, problem_set_id: int):
    ps = get_object_or_404(models.ProblemSet, id=problem_set_id, course__enrollments__user=request.user)
    problems = ps.problems.all()
    submissions = {
        s.problem_id: s
        for s in models.Submission.objects.filter(student=request.user, problem__problem_set=ps)
    }
    if ps.due_at and timezone.now() > ps.due_at:
        for submission in submissions.values():
            if submission.status == models.Submission.STATUS_DRAFT and submission.files.exists():
                services.finalize_submission(submission)
    rows = []
    for problem in problems:
        submission = submissions.get(problem.id)
        if submission:
            latest_grade = submission.grades.order_by('-score', '-finalized_at', '-id').first()
            if latest_grade:
                submission.final_score = latest_grade.score
                submission.status = models.Submission.STATUS_GRADED
                submission.save(update_fields=['final_score', 'status'])
        rows.append(
            {
                'problem': problem,
                'submission': submission,
                'has_score': submission is not None and submission.final_score is not None,
            }
        )
    return render(
        request,
        'student/problem_set_detail.html',
        {'problem_set': ps, 'rows': rows},
    )


@student_required
def student_problem_detail(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__enrollments__user=request.user)
    submission = models.Submission.objects.filter(problem=problem, student=request.user).first()
    rubric = None
    if submission and submission.status != models.Submission.STATUS_DRAFT:
        rubric = services.get_active_rubric(problem)
    grade = None
    rubric_breakdown = None
    if submission:
        grade = submission.grades.order_by('-finalized_at', '-id').first()
        autograde = submission.autograde_runs.order_by('-created_at', '-id').first()
        if autograde:
            rubric_breakdown = (autograde.raw_output_json or {}).get('parsed', {}).get('rubric_scores')
    return render(
        request,
        'student/problem_detail.html',
        {
            'problem': problem,
            'rubric': rubric,
            'submission': submission,
            'files': submission.files.all() if submission else [],
            'grade': grade,
            'rubric_breakdown': rubric_breakdown,
            'can_edit': submission is None or submission.status == models.Submission.STATUS_DRAFT,
        },
    )


@student_required
def student_regrade(request, submission_id: int):
    submission = get_object_or_404(models.Submission, id=submission_id, student=request.user)
    if submission.status == models.Submission.STATUS_DRAFT:
        return redirect('student_problem_detail', problem_id=submission.problem_id)
    if request.method != 'POST':
        return redirect('student_problem_detail', problem_id=submission.problem_id)
    rubric = services.get_active_rubric(submission.problem)
    if rubric is None:
        return redirect('student_problem_detail', problem_id=submission.problem_id)

    services.run_autograde_openai(submission, rubric)
    best = submission.grades.order_by('-score', '-finalized_at', '-id').first()
    if best:
        submission.final_score = best.score
        submission.status = models.Submission.STATUS_GRADED
        submission.save(update_fields=['final_score', 'status'])
    return redirect('student_problem_detail', problem_id=submission.problem_id)


@student_required
def submission_upload(request, problem_id: int):
    problem = get_object_or_404(models.Problem, id=problem_id, problem_set__course__enrollments__user=request.user)
    due_at = problem.problem_set.due_at
    if due_at and timezone.now() > due_at:
        submission = models.Submission.objects.filter(problem=problem, student=request.user).first()
        if submission and submission.status == models.Submission.STATUS_DRAFT and submission.files.exists():
            services.finalize_submission(submission)
        return render(request, 'student/submission_closed.html', {'problem': problem})

    submission, _ = models.Submission.objects.get_or_create(problem=problem, student=request.user)

    if request.method == 'POST':
        form = forms.SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Replace files for this submission (one submission per problem).
            if submission.status != models.Submission.STATUS_DRAFT:
                return render(
                    request,
                    'student/submission_closed.html',
                    {'problem': problem, 'message': 'Submission already finalized.'},
                )
            submission.files.all().delete()
            files = form.cleaned_data['files']
            for index, file_obj in enumerate(files, start=1):
                models.SubmissionFile.objects.create(
                    submission=submission,
                    file=file_obj,
                    mime_type=getattr(file_obj, 'content_type', ''),
                    page_number=index,
                )
            submission.status = models.Submission.STATUS_DRAFT
            submission.save(update_fields=['status'])
            return redirect('student_problem_set_detail', problem_set_id=problem.problem_set_id)
    else:
        form = forms.SubmissionForm()
    return render(
        request,
        'student/submission_upload.html',
        {'problem': problem, 'form': form, 'submission': submission, 'files': submission.files.all()},
    )


@student_required
def submission_finalize(request, submission_id: int):
    submission = get_object_or_404(models.Submission, id=submission_id, student=request.user)
    due_at = submission.problem.problem_set.due_at
    if due_at and timezone.now() > due_at:
        if submission.status == models.Submission.STATUS_DRAFT and submission.files.exists():
            services.finalize_submission(submission)
        return redirect('student_problem_set_detail', problem_set_id=submission.problem.problem_set_id)

    if submission.status != models.Submission.STATUS_DRAFT:
        return redirect('student_problem_set_detail', problem_set_id=submission.problem.problem_set_id)

    if not submission.files.exists():
        return redirect('submission_upload', problem_id=submission.problem_id)

    services.finalize_submission(submission)
    return redirect('student_problem_set_detail', problem_set_id=submission.problem.problem_set_id)


@student_required
def submission_delete_draft(request, submission_id: int):
    submission = get_object_or_404(models.Submission, id=submission_id, student=request.user)
    if submission.status != models.Submission.STATUS_DRAFT:
        return redirect('student_problem_detail', problem_id=submission.problem_id)
    if request.method == 'POST':
        submission.files.all().delete()
        submission.delete()
        return redirect('student_problem_detail', problem_id=submission.problem_id)
    return render(request, 'student/submission_delete.html', {'submission': submission})


@professor_required
def submission_list(request, problem_set_id: int):
    ps = get_object_or_404(models.ProblemSet, id=problem_set_id, course__professor=request.user)
    submissions = (
        models.Submission.objects.filter(problem__problem_set=ps)
        .select_related('problem', 'student')
        .order_by('problem__order', 'student__email')
    )
    return render(request, 'professor/submission_list.html', {'problem_set': ps, 'submissions': submissions})


@professor_required
def submission_detail(request, submission_id: int):
    submission = get_object_or_404(
        models.Submission,
        id=submission_id,
        problem__problem_set__course__professor=request.user,
    )
    rubric = services.get_active_rubric(submission.problem)
    existing_grade = submission.grades.filter(grader_type=models.Grade.GRADER_PROFESSOR).last()
    form = forms.GradeForm(instance=existing_grade)

    if request.method == 'POST':
        form = forms.GradeForm(request.POST, instance=existing_grade)
        if form.is_valid() and rubric is not None:
            grade = form.save(commit=False)
            grade.submission = submission
            grade.rubric = rubric
            grade.grader_type = models.Grade.GRADER_PROFESSOR
            grade.grader = request.user
            grade.save()
            submission.final_score = grade.score
            submission.status = models.Submission.STATUS_GRADED
            submission.save(update_fields=['final_score', 'status'])
            return redirect('submission_detail', submission_id=submission.id)

    return render(
        request,
        'professor/submission_detail.html',
        {
            'submission': submission,
            'rubric': rubric,
            'files': submission.files.all(),
            'form': form,
        },
    )


@student_required
def appeal_create(request, submission_id: int):
    submission = get_object_or_404(models.Submission, id=submission_id, student=request.user)
    if request.method == 'POST':
        form = forms.AppealForm(request.POST)
        if form.is_valid():
            appeal = form.save(commit=False)
            appeal.submission = submission
            appeal.student = request.user
            appeal.save()
            return redirect('student_problem_set_detail', problem_set_id=submission.problem.problem_set_id)
    else:
        form = forms.AppealForm()
    return render(request, 'student/appeal_form.html', {'submission': submission, 'form': form})


@professor_required
def appeals_list(request):
    appeals = models.Appeal.objects.filter(submission__problem__problem_set__course__professor=request.user).order_by('-created_at')
    return render(request, 'professor/appeals_list.html', {'appeals': appeals})


@professor_required
def appeal_detail(request, appeal_id: int):
    appeal = get_object_or_404(
        models.Appeal,
        id=appeal_id,
        submission__problem__problem_set__course__professor=request.user,
    )
    form = forms.AppealMessageForm()
    if request.method == 'POST':
        form = forms.AppealMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.appeal = appeal
            msg.author = request.user
            msg.save()
            return redirect('appeal_detail', appeal_id=appeal.id)
    return render(request, 'professor/appeal_detail.html', {'appeal': appeal, 'form': form})
