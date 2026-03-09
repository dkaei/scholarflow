from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.http import HttpResponseForbidden, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import mimetypes
import os

from notifications.models import Notification
from .models import Course, CourseFeedback, CourseMaterial, Enrolment, Lesson
from .services import can_access_course


def _is_teacher(user):
    return getattr(user, "role", None) == "TEACHER"

def _is_student(user):
    return getattr(user, "role", None) == "STUDENT"


class CourseEditForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Course title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Course overview / description"}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Lesson 1: Introduction"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class LessonEditForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lesson title"}),
        }


class MaterialUploadForm(forms.ModelForm):

    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.none(),
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = CourseMaterial
        fields = ["lesson", "title", "order", "file"]
        widgets = {
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Welcome video"
            }),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)

        if course:
            self.fields["lesson"].queryset = course.lessons.order_by("order", "id")

    def clean_lesson(self):
        lesson = self.cleaned_data.get("lesson")
        if not lesson:
            raise forms.ValidationError("Please select a lesson.")
        return lesson

class MaterialEditForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Material title"}),
        }


class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Introduction to Web Development"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "What will students learn in this course?"}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = CourseFeedback
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "What worked well? What could be improved?"}),
        }

    def clean_rating(self):
        rating = self.cleaned_data["rating"]
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating


def _guess_material_type(filename: str) -> str:
    filename = (filename or "").lower()
    if filename.endswith((".mp4", ".webm", ".mov", ".ogg")):
        return "video"
    if filename.endswith(".pdf"):
        return "pdf"
    if filename.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
        return "image"
    return "file"

@login_required
def material_view(request, course_id, material_id):
    course = get_object_or_404(Course, id=course_id)
    material = get_object_or_404(CourseMaterial, id=material_id, course=course)

    if not can_access_course(request.user, course):
        return HttpResponseForbidden("You do not have access to this material.")

    if not material.file:
        raise Http404("File not found.")

    filename = os.path.basename(material.file.name)
    mime_type, _ = mimetypes.guess_type(filename)

    return FileResponse(
        material.file.open("rb"),
        content_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@login_required
def material_download(request, course_id, material_id):
    course = get_object_or_404(Course, id=course_id)
    material = get_object_or_404(CourseMaterial, id=material_id, course=course)

    if not can_access_course(request.user, course):
        return HttpResponseForbidden()

    if not material.file:
        raise Http404()

    filename = os.path.basename(material.file.name)

    return FileResponse(
        material.file.open("rb"),
        as_attachment=True,
        filename=filename
    )


def _renumber_lessons(course):
    lessons = course.lessons.order_by("order", "id")
    for index, lesson in enumerate(lessons, start=1):
        if lesson.order != index:
            lesson.order = index
            lesson.save(update_fields=["order"])


def _renumber_materials(lesson):
    materials = lesson.materials.order_by("order", "id")
    for index, material in enumerate(materials, start=1):
        if material.order != index:
            material.order = index
            material.save(update_fields=["order"])


def _move_lesson(course, lesson, direction):
    lessons = list(course.lessons.order_by("order", "id"))
    idx = next((i for i, item in enumerate(lessons) if item.id == lesson.id), None)
    if idx is None:
        return

    if direction == "up" and idx > 0:
        lessons[idx], lessons[idx - 1] = lessons[idx - 1], lessons[idx]
    elif direction == "down" and idx < len(lessons) - 1:
        lessons[idx], lessons[idx + 1] = lessons[idx + 1], lessons[idx]
    else:
        return

    for index, item in enumerate(lessons, start=1):
        if item.order != index:
            item.order = index
            item.save(update_fields=["order"])


def _move_material(lesson, material, direction):
    materials = list(lesson.materials.order_by("order", "id"))
    idx = next((i for i, item in enumerate(materials) if item.id == material.id), None)
    if idx is None:
        return

    if direction == "up" and idx > 0:
        materials[idx], materials[idx - 1] = materials[idx - 1], materials[idx]
    elif direction == "down" and idx < len(materials) - 1:
        materials[idx], materials[idx + 1] = materials[idx + 1], materials[idx]
    else:
        return

    for index, item in enumerate(materials, start=1):
        if item.order != index:
            item.order = index
            item.save(update_fields=["order"])


@login_required
def course_list(request):
    q = (request.GET.get("q") or "").strip()

    if _is_teacher(request.user):
        courses = Course.objects.select_related("teacher").order_by("-created_at")
    else:
        courses = Course.objects.select_related("teacher").filter(is_visible=True).order_by("-created_at")

    if q:
        courses = courses.filter(title__icontains=q)

    my_enrolments = {}
    if _is_student(request.user):
        my_enrolments = {
            e.course_id: e
            for e in Enrolment.objects.filter(student=request.user).select_related("course")
        }

    return render(
        request,
        "courses/course_list.html",
        {
            "courses": courses,
            "my_enrolments": my_enrolments,
            "q": q,
        },
    )


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course.objects.select_related("teacher"), id=course_id)
    enrolment = None

    if _is_student(request.user):
        enrolment = Enrolment.objects.filter(course=course, student=request.user).first()

    show_learning_area = can_access_course(request.user, course)

    # lessons grouped with materials
    lessons = (
        Lesson.objects.filter(course=course)
        .prefetch_related("materials")
        .order_by("order", "id")
    ) if show_learning_area else Lesson.objects.none()

    materials = CourseMaterial.objects.filter(course=course).order_by("created_at") if show_learning_area else CourseMaterial.objects.none()

    can_open_study_room = show_learning_area

    feedbacks = (
        CourseFeedback.objects
        .filter(course=course)
        .select_related("student")
        .order_by("-created_at")
    )

    return render(request, "courses/course_detail.html", {
        "course": course,
        "enrolment": enrolment,
        "materials": materials,
        "lessons": lessons,
        "feedbacks": feedbacks,
        "show_learning_area": show_learning_area,
        "can_open_study_room": can_open_study_room,
    })


@login_required
def enrol_course(request, course_id):
    if not _is_student(request.user):
        return HttpResponseForbidden("Students only.")

    course = get_object_or_404(Course, id=course_id)
    enrolment, created = Enrolment.objects.get_or_create(course=course, student=request.user)

    if enrolment.status == Enrolment.Status.BLOCKED:
        return HttpResponseForbidden("You cannot enrol in this course.")

    if enrolment.status in [Enrolment.Status.REJECTED, Enrolment.Status.REMOVED]:
        enrolment.status = Enrolment.Status.PENDING
        enrolment.remark = ""
        enrolment.save(update_fields=["status", "remark"])
        return redirect("course-detail", course_id=course.id)

    if created:
        enrolment.status = Enrolment.Status.PENDING
        enrolment.save(update_fields=["status"])

    return redirect("course-detail", course_id=course.id)


@login_required
def leave_feedback(request, course_id):
    if not _is_student(request.user):
        return HttpResponseForbidden("Students only.")

    course = get_object_or_404(Course, id=course_id)
    enrolment = Enrolment.objects.filter(course=course, student=request.user, status=Enrolment.Status.ACTIVE).first()
    if not enrolment:
        return HttpResponseForbidden("Only active enrolled students can leave feedback.")

    if CourseFeedback.objects.filter(course=course, student=request.user).exists():
        return HttpResponseForbidden("You already left feedback for this course.")

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.course = course
            feedback.student = request.user
            feedback.save()
            return redirect("course-detail", course_id=course.id)
    else:
        form = FeedbackForm()

    return render(request, "courses/feedback_form.html", {"course": course, "form": form})


@login_required
def teacher_dashboard(request):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")
    return redirect("home")


@login_required
def teacher_course_create(request):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    if request.method == "POST":
        form = CourseCreateForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.is_visible = False
            course.save()

            # default first lesson
            Lesson.objects.create(
                course=course,
                title="Lesson 1",
                order=1,
            )

            return redirect("teacher-course-manage", course_id=course.id)
    else:
        form = CourseCreateForm()

    return render(request, "courses/course_create.html", {"form": form})


@login_required
def teacher_course_edit(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    if request.method == "POST":
        form = CourseEditForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect("teacher-course-manage", course_id=course.id)
    else:
        form = CourseEditForm(instance=course)

    return render(
        request,
        "courses/course_edit.html",
        {
            "course": course,
            "form": form,
        },
    )


@login_required
def teacher_course_manage(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    q = (request.GET.get("q") or "").strip()

    pending_enrolments = (
        Enrolment.objects.filter(course=course, status=Enrolment.Status.PENDING)
        .select_related("student")
        .order_by("-created_at")
    )

    active_enrolments = (
        Enrolment.objects.filter(course=course, status=Enrolment.Status.ACTIVE)
        .select_related("student")
        .order_by("student__username")
    )

    if q:
        active_enrolments = active_enrolments.filter(
            Q(student__username__icontains=q)
            | Q(student__display_name__icontains=q)
            | Q(student__email__icontains=q)
        )

    lessons = course.lessons.prefetch_related("materials").order_by("order", "id")
    lesson_form = LessonForm(initial={"order": (course.lessons.aggregate(m=Max("order")).get("m") or 0) + 1})

    return render(
        request,
        "courses/course_manage.html",
        {
            "course": course,
            "pending_enrolments": pending_enrolments,
            "active_enrolments": active_enrolments,
            "lessons": lessons,
            "lesson_form": lesson_form,
            "q": q,
        },
    )


@login_required
def teacher_enrolment_update(request, course_id, enrolment_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    enrolment = get_object_or_404(Enrolment, id=enrolment_id, course=course)

    action = request.POST.get("action")
    remark = (request.POST.get("remark") or "").strip()

    if action == "approve":
        enrolment.status = Enrolment.Status.ACTIVE
        enrolment.remark = ""
        Notification.objects.create(
            user=enrolment.student,
            message=f"You have been accepted into {course.title}.",
            link=redirect("course-detail", course_id=course.id).url,
        )
    elif action == "reject":
        enrolment.status = Enrolment.Status.REJECTED
        enrolment.remark = remark
        Notification.objects.create(
            user=enrolment.student,
            message=f"Your request for {course.title} was rejected.",
            link=redirect("course-detail", course_id=course.id).url,
        )
    elif action == "block":
        enrolment.status = Enrolment.Status.BLOCKED
        enrolment.remark = remark
        Notification.objects.create(
            user=enrolment.student,
            message=f"You were blocked from {course.title}.",
            link=redirect("course-detail", course_id=course.id).url,
        )
    elif action == "remove":
        enrolment.status = Enrolment.Status.REMOVED
        enrolment.remark = remark
        Notification.objects.create(
            user=enrolment.student,
            message=f"You were removed from {course.title}.",
            link=redirect("course-detail", course_id=course.id).url,
        )

    enrolment.save(update_fields=["status", "remark"])
    return redirect("teacher-course-manage", course_id=course.id)


@login_required
def teacher_material_upload(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    if request.method == "POST":
        form = MaterialUploadForm(request.POST, request.FILES, course=course)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.uploaded_by = request.user
            material.material_type = _guess_material_type(material.file.name)
            material.save()
            return redirect("teacher-course-manage", course_id=course.id)
    else:
        initial = {}
        lesson_id = request.GET.get("lesson")
        if lesson_id and lesson_id.isdigit():
            initial["lesson"] = Lesson.objects.filter(course=course, id=int(lesson_id)).first()
        form = MaterialUploadForm(course=course, initial=initial)

    return render(
        request,
        "courses/material_upload.html",
        {
            "course": course,
            "form": form,
        },
    )

@login_required
def teacher_material_edit(request, course_id, material_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    material = get_object_or_404(CourseMaterial, id=material_id, course=course)

    if request.method == "POST":
        form = MaterialEditForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            return redirect("teacher-course-manage", course_id=course.id)
    else:
        form = MaterialEditForm(instance=material)

    return render(request, "courses/material_edit.html", {
        "course": course,
        "material": material,
        "form": form,
    })


@login_required
def teacher_lesson_move_up(request, course_id, lesson_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    if request.method == "POST":
        _move_lesson(course, lesson, "up")
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False}, status=405)


@login_required
def teacher_lesson_move_down(request, course_id, lesson_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    if request.method == "POST":
        _move_lesson(course, lesson, "down")
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False}, status=405)


@login_required
def teacher_material_move_up(request, course_id, material_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    material = get_object_or_404(CourseMaterial, id=material_id, course=course)

    if request.method == "POST":
        _move_material(material.lesson, material, "up")
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False}, status=405)


@login_required
def teacher_material_move_down(request, course_id, material_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    material = get_object_or_404(CourseMaterial, id=material_id, course=course)

    if request.method == "POST":
        _move_material(material.lesson, material, "down")
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False}, status=405)


@login_required
def teacher_lesson_create(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if title:
            next_order = (course.lessons.aggregate(m=Max("order")).get("m") or 0) + 1
            Lesson.objects.create(
                course=course,
                title=title,
                order=next_order,
            )

    return redirect("teacher-course-manage", course_id=course.id)

@login_required
def teacher_lesson_edit(request, course_id, lesson_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    if request.method == "POST":
        form = LessonEditForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect("teacher-course-manage", course_id=course.id)
    else:
        form = LessonEditForm(instance=lesson)

    return render(request, "courses/lesson_edit.html", {
        "course": course,
        "lesson": lesson,
        "form": form,
    })


@login_required
def teacher_course_toggle_visibility(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    course.is_visible = not course.is_visible
    course.save(update_fields=["is_visible"])
    return redirect("teacher-course-manage", course_id=course.id)


@login_required
def teacher_course_delete(request, course_id):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    if request.method == "POST":
        course.delete()
        return redirect("home")

    return render(request, "courses/course_delete.html", {"course": course})