from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('prof/admin-reset/', views.admin_password_reset, name='admin_password_reset'),

    # Professor routes
    path('prof/classes/', views.class_list, name='class_list'),
    path('prof/classes/new/', views.class_create, name='class_create'),
    path('prof/classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('prof/classes/<int:class_id>/enroll/', views.enrollment_add, name='enrollment_add'),
    path('prof/classes/<int:class_id>/problem-sets/new/', views.problem_set_create, name='problem_set_create'),
    path('prof/problem-sets/<int:problem_set_id>/', views.problem_set_detail, name='problem_set_detail'),
    path('prof/problem-sets/<int:problem_set_id>/problems/new/', views.problem_create, name='problem_create'),
    path('prof/problem-sets/<int:problem_set_id>/submissions/', views.submission_list, name='submission_list'),
    path('prof/problems/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('prof/problems/<int:problem_id>/delete/', views.problem_delete, name='problem_delete'),
    path('prof/problems/<int:problem_id>/prompt-preview/', views.problem_prompt_preview, name='problem_prompt_preview'),
    path('prof/problems/<int:problem_id>/rubric/', views.rubric_edit, name='rubric_edit'),
    path('prof/problems/<int:problem_id>/rubric/regenerate/', views.rubric_regenerate, name='rubric_regenerate'),
    path('prof/submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('prof/appeals/', views.appeals_list, name='appeals_list'),
    path('prof/appeals/<int:appeal_id>/', views.appeal_detail, name='appeal_detail'),

    # Student routes
    path('student/classes/', views.student_class_list, name='student_class_list'),
    path('student/classes/<int:class_id>/', views.student_class_detail, name='student_class_detail'),
    path('student/problem-sets/<int:problem_set_id>/', views.student_problem_set_detail, name='student_problem_set_detail'),
    path('student/problems/<int:problem_id>/', views.student_problem_detail, name='student_problem_detail'),
    path('student/problems/<int:problem_id>/submit/', views.submission_upload, name='submission_upload'),
    path('student/submissions/<int:submission_id>/regrade/', views.student_regrade, name='student_regrade'),
    path('student/submissions/<int:submission_id>/finalize/', views.submission_finalize, name='submission_finalize'),
    path('student/submissions/<int:submission_id>/delete-draft/', views.submission_delete_draft, name='submission_delete_draft'),
    path('student/submissions/<int:submission_id>/appeal/', views.appeal_create, name='appeal_create'),
    path('student/password-change/', views.student_password_change, name='student_password_change'),
]
