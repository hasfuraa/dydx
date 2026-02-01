# Project Plan: Math Grading Web App (MVP)

Date: 2026-02-01

## Goals
- Provide a web app where professors create classes, problem sets, and problems (PDF prompts).
- Students upload solutions as a PDF or multiple images, with one submission allowed per problem (replacement permitted until due date).
- Auto-grade using an LLM with a rubric inferred at problem creation time and editable by the professor.
- Provide professor override and appeal workflow.
- After auth, land users on role-specific dashboards.

## Product Decisions (from requirements)
- Single university, single instructor per class.
- One submission per student per problem; replacement allowed before due date.
- Rubric-based grading; inferred rubric shown at upload and editable before release.
- Solutions can be multi-image or PDF.
- Reliability, integrity, and cost optimizations deferred for MVP.

## Core User Flows
### Professor
1. Create class.
2. Add students (bulk import or invite via email).
3. Create problem set with due date.
4. Create problem: upload prompt PDF, set max score.
5. System infers rubric; professor edits and confirms.
6. Monitor dashboard: submission progress, grade stats.
7. Review submissions, override grades.
8. Handle appeals.

### Student
1. Join class (invite or enrollment).
2. View dashboard with upcoming due dates.
3. Open problem set, upload solution (PDF or images).
4. Replace submission before due date.
5. View grades and feedback; submit appeal if needed.

## Data Model (MVP)
### Users
- users: id, name, email, role (student|professor), created_at

### Classes & Enrollment
- classes: id, title, term, professor_id, created_at
- enrollments: id, class_id, user_id, role_in_class (student), status (active)

### Problem Sets & Problems
- problem_sets: id, class_id, title, release_at, due_at, created_at
- problems: id, problem_set_id, title, prompt_pdf_url, max_score, order, created_at

### Rubrics
- rubrics: id, problem_id, version, total_points, created_at
- rubric_items: id, rubric_id, label, points, order

### Submissions (single submission, replace before due date)
- submissions: id, problem_id, student_id, submitted_at, status (submitted|graded), final_score
- submission_files: id, submission_id, file_url, mime_type, page_number

### Grading
- autograde_runs: id, submission_id, rubric_id, model, raw_output_json, score, created_at
- grades: id, submission_id, rubric_id, score, feedback, grader_type (auto|professor), grader_id, finalized_at

### Appeals
- appeals: id, submission_id, student_id, reason, status (open|closed), created_at
- appeal_messages: id, appeal_id, author_id, message, created_at

## Business Rules
- One submission row per student per problem; replacement overwrites submission_files until due date.
- Final score resolution: if a professor grade exists, it overrides auto grade.
- Auto-grade run uses the rubric version active at the time of submission grading.
- Rubric edits after release increment rubric version; new submissions use latest version.

## Dashboards (Landing Page After Auth)
### Professor Dashboard
Primary goals: monitor progress, spot grading issues, take action quickly.

Widgets:
- Active Classes
  - Class name, term
  - % submissions per problem set: (submitted / enrolled) by problem set
  - Next due date
- Submission Progress (per class)
  - Problem set list with progress bars
  - Counts: submitted, not submitted, graded, needs review
- Grade Statistics (per class or overall)
  - Average/median score per problem set
  - Score distribution snapshot (bins)
  - Lowest/highest scoring problems
- Appeals Queue
  - Open appeals count, latest activity
- Recent Activity
  - New submissions, new appeals, grades overridden

Quick actions:
- Create class, create problem set, add students, jump to review queue.

### Student Dashboard
Primary goals: know what is due, submit work, see grades.

Widgets:
- Upcoming Deadlines
  - Problem sets with due date and time remaining
- My Submissions
  - Submitted/Not submitted per problem
  - Replace submission button if before due date
- Grades & Feedback
  - Latest grades, links to feedback
- Class Overview
  - Instructor name, office hours link (optional)

## API Surface (MVP)
- Auth: sign in/out, basic roles
- Professor: CRUD classes, enrollments, problem sets, problems, rubrics; view/override grades; appeals
- Student: list classes/assignments, submit/replace, view grades, file appeals

## UI Pages (MVP)
- Auth: login
- Dashboard: role-specific
- Class view: roster (professor), assignments list
- Problem set view: problem list
- Problem view: prompt, submission upload, grade
- Appeals view: list + detail

## Implementation Plan (Phased)
### Phase 0: Repo + Baseline
- Initialize git repo
- Choose stack (suggestion: Next.js + Postgres + Prisma + S3-compatible storage)
- Set up environment + linting

### Phase 1: Core Data + Auth
- Define schema + migrations
- Implement auth and roles
- Basic class creation and enrollment

### Phase 2: Problems + Rubrics
- Problem set and problem CRUD
- PDF prompt upload
- Inferred rubric generation + edit UI

### Phase 3: Submissions + Storage
- Student submission upload (PDF/images)
- Replacement before due date
- Submission listing for professor

### Phase 4: Auto-Grading + Override
- Queue auto-grade job
- Store autograde runs
- Professor override + final grade logic

### Phase 5: Appeals + Dashboards
- Appeals workflow
- Role-based dashboards with stats

## Open Questions (to resolve later)
- Preferred tech stack and hosting?
- Enrollment method: invite, CSV upload, or code?
- Rubric inference prompts and grading prompt style?
- File storage provider (S3, GCS, local for dev)?
- SLA for grading turnaround?

