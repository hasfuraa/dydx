import base64
import os
from io import BytesIO

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field
from typing import Literal

from openai import OpenAI

from . import models

class RubricScore(BaseModel):
    label: str
    score: float = Field(ge=0)
    notes: str | None = None
    status: Literal['correct', 'incorrect', 'partial'] = 'partial'


class GradeResult(BaseModel):
    total_score: float = Field(ge=0)
    rubric_scores: list[RubricScore]
    feedback: str


class RubricItemDraft(BaseModel):
    label: str
    points: float = Field(ge=0)


class RubricDraft(BaseModel):
    items: list[RubricItemDraft]


def _normalize_points(raw_points: list[float], total: int) -> list[int]:
    points = [max(1, int(round(p))) for p in raw_points if p is not None]
    if not points:
        return []
    sum_points = sum(points)
    if sum_points <= 0:
        return []
    if sum_points != total:
        scale = total / sum_points
        points = [max(1, int(round(p * scale))) for p in points]
        delta = total - sum(points)
        points[-1] = max(1, points[-1] + delta)
    return points


def _fallback_rubric(problem: models.Problem) -> models.Rubric:
    total = problem.max_score
    base = max(total // 3, 1)
    points = [base, base, max(total - (2 * base), 1)]
    with transaction.atomic():
        rubric = models.Rubric.objects.create(
            problem=problem,
            version=1,
            total_points=total,
        )
        for idx, pts in enumerate(points, start=1):
            models.RubricItem.objects.create(
                rubric=rubric,
                label=f"Criterion {idx}",
                points=pts,
                order=idx,
            )
    return rubric


def infer_default_rubric(
    problem: models.Problem,
    version: int = 1,
    suggestion: str | None = None,
) -> models.Rubric:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY not set')

    prompt_path = problem.prompt_pdf.path
    images = _file_to_images(prompt_path)
    if not images:
        raise RuntimeError('Could not extract images from the prompt PDF')

    suggestion_text = suggestion.strip() if suggestion else ''
    suggestion_block = f"\nProfessor suggestion:\n{suggestion_text}" if suggestion_text else ''

    content = [
        {
            'type': 'input_text',
            'text': (
                'You are creating a grading rubric for a math problem. '
                'Produce 3-7 rubric items with clear labels and point values. '
                f'The total points must sum to {problem.max_score}.'
                f'{suggestion_block}'
            ),
        }
    ]
    for image_bytes, mime in images[:5]:
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        content.append({'type': 'input_image', 'image_url': f'data:{mime};base64,{b64}'})

    client = OpenAI()
    response = client.responses.parse(
        model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini-2024-07-18'),
        input=[{'role': 'user', 'content': content}],
        text_format=RubricDraft,
    )
    result = response.output_parsed
    items = result.items if result else []

    if not items:
        raise RuntimeError('Rubric generation returned no items')

    labels = [item.label.strip() or f"Criterion {idx + 1}" for idx, item in enumerate(items)]
    points = _normalize_points([item.points for item in items], problem.max_score)
    if not points or len(points) != len(labels):
        raise RuntimeError('Rubric points could not be normalized')

    with transaction.atomic():
        rubric = models.Rubric.objects.create(
            problem=problem,
            version=version,
            total_points=problem.max_score,
        )
        for idx, (label, pts) in enumerate(zip(labels, points), start=1):
            models.RubricItem.objects.create(
                rubric=rubric,
                label=label,
                points=pts,
                order=idx,
            )
    return rubric


def get_active_rubric(problem: models.Problem) -> models.Rubric:
    return problem.rubrics.order_by('-version', '-id').first()


def run_autograde_placeholder(submission: models.Submission, rubric: models.Rubric) -> None:
    models.AutoGradeRun.objects.create(
        submission=submission,
        rubric=rubric,
        model='placeholder',
        raw_output_json={'note': 'Auto-grading not yet implemented.'},
        score=0,
    )
    models.Grade.objects.create(
        submission=submission,
        rubric=rubric,
        score=0,
        feedback='Auto-grade placeholder.',
        grader_type=models.Grade.GRADER_AUTO,
        grader=None,
    )
    submission.final_score = 0
    submission.status = models.Submission.STATUS_GRADED
    submission.save(update_fields=['final_score', 'status'])


def _file_to_images(file_path: str) -> list[tuple[bytes, str]]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return []
        pdf = pdfium.PdfDocument(file_path)
        images: list[tuple[bytes, str]] = []
        for i in range(len(pdf)):
            page = pdf[i]
            pil_image = page.render(scale=2).to_pil()
            buffer = BytesIO()
            pil_image.save(buffer, format='PNG')
            images.append((buffer.getvalue(), 'image/png'))
        return images

    with open(file_path, 'rb') as file_obj:
        if ext in {'.jpg', '.jpeg'}:
            mime = 'image/jpeg'
        elif ext == '.webp':
            mime = 'image/webp'
        elif ext == '.gif':
            mime = 'image/gif'
        else:
            mime = 'image/png'
        return [(file_obj.read(), mime)]


def _normalize_rubric_scores(
    rubric: models.Rubric, rubric_scores: list[RubricScore]
) -> tuple[list[RubricScore], float]:
    score_map = {item.label: item for item in rubric_scores}
    normalized: list[RubricScore] = []
    total = 0.0
    for rubric_item in rubric.items.all():
        incoming = score_map.get(rubric_item.label)
        raw_score = float(incoming.score) if incoming else 0.0
        max_points = float(rubric_item.points)
        status = incoming.status if incoming else 'partial'
        if status == 'correct':
            score = max_points
        elif status == 'incorrect':
            score = 0.0
        else:
            score = max(0.0, min(raw_score, max_points))
        normalized.append(
            RubricScore(
                label=rubric_item.label,
                score=score,
                notes=incoming.notes if incoming else None,
                status=status,
            )
        )
        total += score
    return normalized, total


def run_autograde_openai(submission: models.Submission, rubric: models.Rubric) -> None:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        run_autograde_placeholder(submission, rubric)
        return

    images: list[tuple[bytes, str]] = []
    # Include the problem prompt (if available) before student work.
    if submission.problem.prompt_pdf and os.path.exists(submission.problem.prompt_pdf.path):
        images.extend(_file_to_images(submission.problem.prompt_pdf.path))

    for submission_file in submission.files.all().order_by('page_number'):
        file_path = submission_file.file.path
        images.extend(_file_to_images(file_path))

    if not images:
        models.AutoGradeRun.objects.create(
            submission=submission,
            rubric=rubric,
            model='openai',
            raw_output_json={'error': 'No images available for grading.'},
            score=0,
        )
        models.Grade.objects.create(
            submission=submission,
            rubric=rubric,
            score=0,
            feedback='No images available for grading.',
            grader_type=models.Grade.GRADER_AUTO,
            grader=None,
        )
        submission.final_score = 0
        submission.status = models.Submission.STATUS_GRADED
        submission.save(update_fields=['final_score', 'status'])
        return

    rubric_items = [{'label': item.label, 'points': item.points} for item in rubric.items.all()]
    rubric_text = '\n'.join([f"- {item['label']}: {item['points']} pts" for item in rubric_items])

    content = [
        {
            'type': 'input_text',
            'text': (
                'You are grading a student solution. Use the rubric to assign scores per item and a total score. '
                'Scrutinize every part of the computation to ensure there are no issues or hidden mistakes. '
                'For each rubric item: restate the student\'s answer, recompute it, and compare. '
                'Then set status to correct, incorrect, or partial. '
                'If any arithmetic error or wrong conclusion appears, status must be incorrect. '
                'If fully correct, status must be correct and award full points. '
                'Your feedback must be consistent with the rubric scores. '
                'If you award full points for an item, describe it as correct. '
                'If you deduct points, briefly describe the mistake for that item in the rubric item notes. '
                'Total score must equal the sum of rubric item scores. '
                'Do not exceed the rubric total.'
                f'\nRubric:\n{rubric_text}'
            ),
        }
    ]
    for image_bytes, mime in images:
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        content.append({'type': 'input_image', 'image_url': f'data:{mime};base64,{b64}'})

    client = OpenAI()
    try:
        response = client.responses.parse(
            model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini-2024-07-18'),
            input=[{'role': 'user', 'content': content}],
            text_format=GradeResult,
            temperature=0,
        )
        result = response.output_parsed
        raw_text = response.output_text
        parsed = result.model_dump() if result else None
        rubric_scores = result.rubric_scores if result else []
        normalized_scores, total_score = _normalize_rubric_scores(rubric, rubric_scores)
        if normalized_scores and any(score.notes for score in normalized_scores):
            feedback_lines = []
            for score in normalized_scores:
                note = score.notes or 'No issues noted.'
                feedback_lines.append(f"{score.label} ({score.status}): {note}")
            feedback = "Rubric notes:\n" + "\n".join(feedback_lines)
        else:
            feedback = result.feedback if result else raw_text
    except Exception as exc:
        raw_text = f'Auto-grade failed: {exc}'
        total_score = 0
        parsed = None
        normalized_scores = []
        feedback = raw_text

    if parsed is not None:
        parsed['rubric_scores'] = [score.model_dump() for score in normalized_scores]
        parsed['total_score'] = total_score

    models.AutoGradeRun.objects.create(
        submission=submission,
        rubric=rubric,
        model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini-2024-07-18'),
        raw_output_json={'raw_text': raw_text, 'parsed': parsed},
        score=total_score,
    )
    models.Grade.objects.create(
        submission=submission,
        rubric=rubric,
        score=total_score,
        feedback=feedback,
        grader_type=models.Grade.GRADER_AUTO,
        grader=None,
    )
    submission.final_score = total_score
    submission.status = models.Submission.STATUS_GRADED
    submission.save(update_fields=['final_score', 'status'])


def finalize_submission(submission: models.Submission) -> None:
    rubric = get_active_rubric(submission.problem)
    submission.submitted_at = timezone.now()
    submission.status = models.Submission.STATUS_SUBMITTED
    submission.save(update_fields=['submitted_at', 'status'])
    if rubric is not None:
        run_autograde_openai(submission, rubric)
