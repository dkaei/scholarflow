from django.urls import path
from . import views
from .api_views import CourseListAPIView, CourseDetailAPIView, CourseLessonListAPIView

urlpatterns = [
    path("", views.course_list, name="course-list"),
    path("<int:course_id>/", views.course_detail, name="course-detail"),
    path("<int:course_id>/enrol/", views.enrol_course, name="course-enrol"),
    path("<int:course_id>/feedback/", views.leave_feedback, name="course-feedback"),

    path("teacher/dashboard/", views.teacher_dashboard, name="teacher-dashboard"),
    path("teacher/courses/create/", views.teacher_course_create, name="teacher-course-create"),
    path("teacher/courses/<int:course_id>/", views.teacher_course_manage, name="teacher-course-manage"),
    path("teacher/courses/<int:course_id>/enrolments/<int:enrolment_id>/", views.teacher_enrolment_update, name="teacher-enrolment-update"),
    path("teacher/courses/<int:course_id>/materials/upload/", views.teacher_material_upload, name="teacher-material-upload"),
    path("teacher/courses/<int:course_id>/lessons/create/", views.teacher_lesson_create, name="teacher-lesson-create"),
    path("teacher/courses/<int:course_id>/toggle-visibility/", views.teacher_course_toggle_visibility, name="teacher-course-toggle-visibility"),
    path("teacher/courses/<int:course_id>/delete/", views.teacher_course_delete, name="teacher-course-delete"),

    path("teacher/courses/<int:course_id>/lessons/<int:lesson_id>/edit/", views.teacher_lesson_edit, name="teacher-lesson-edit"),
    path("teacher/courses/<int:course_id>/lessons/<int:lesson_id>/move-up/", views.teacher_lesson_move_up, name="teacher-lesson-move-up"),
    path("teacher/courses/<int:course_id>/lessons/<int:lesson_id>/move-down/", views.teacher_lesson_move_down, name="teacher-lesson-move-down"),
    path("teacher/courses/<int:course_id>/materials/<int:material_id>/edit/", views.teacher_material_edit, name="teacher-material-edit"),
    path("teacher/courses/<int:course_id>/materials/<int:material_id>/move-up/", views.teacher_material_move_up, name="teacher-material-move-up"),
    path("teacher/courses/<int:course_id>/materials/<int:material_id>/move-down/", views.teacher_material_move_down, name="teacher-material-move-down"),
    path("<int:course_id>/materials/<int:material_id>/view/", views.material_view, name="material-view"),
    path("<int:course_id>/materials/<int:material_id>/download/", views.material_download, name="material-download"),
    path("teacher/courses/<int:course_id>/edit/", views.teacher_course_edit, name="teacher-course-edit"),

    path("api/courses/", CourseListAPIView.as_view(), name="api-course-list"),
    path("api/courses/<int:course_id>/", CourseDetailAPIView.as_view(), name="api-course-detail"),
    path("api/courses/<int:course_id>/lessons/", CourseLessonListAPIView.as_view(), name="api-course-lessons"),
]