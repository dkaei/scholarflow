from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course, Enrolment
from .models import User, StatusUpdate


def _is_teacher(user) -> bool:
    return getattr(user, "role", None) == User.Role.TEACHER


class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create a password"}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm your password"}),
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["username", "display_name", "email", "role", "bio"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Choose a username"}),
            "display_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your display name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell us a little about yourself"}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["display_name", "email", "bio"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Display name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "About you"}),
        }


class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StatusUpdate
        fields = ["text", "image"]
        labels = {
            "text": "Message",
            "image": "Image (optional)",
        }
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Share an update..."
            }),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_text(self):
        text = (self.cleaned_data.get("text") or "").strip()
        if not text:
            raise forms.ValidationError("Please enter a status update.")
        return text


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    return redirect("user-profile", username=request.user.username)


@login_required
def user_profile(request, username: str):
    profile_user = get_object_or_404(User, username=username)

    active_courses = (
        Enrolment.objects.filter(student=profile_user, status=Enrolment.Status.ACTIVE)
        .select_related("course", "course__teacher")
        .order_by("-created_at")
    )

    teaching_courses = (
        Course.objects.filter(teacher=profile_user)
        .order_by("-created_at")
        if profile_user.role == User.Role.TEACHER
        else Course.objects.none()
    )

    status_form = None
    if request.user == profile_user:
        if request.method == "POST":
            status_form = StatusUpdateForm(request.POST, request.FILES)
            if status_form.is_valid():
                status = status_form.save(commit=False)
                status.user = request.user
                status.save()
                return redirect("user-profile", username=request.user.username)
        else:
            status_form = StatusUpdateForm()

    status_updates = profile_user.status_updates.all()

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "active_courses": active_courses,
            "teaching_courses": teaching_courses,
            "status_updates": status_updates,
            "status_form": status_form,
        },
    )


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("user-profile", username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def user_search(request):
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")

    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip().upper()
    course_id = (request.GET.get("course") or "").strip()

    qs = User.objects.filter(role__in=[User.Role.STUDENT, User.Role.TEACHER]).order_by("username")

    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(display_name__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )

    if role in (User.Role.STUDENT, User.Role.TEACHER):
        qs = qs.filter(role=role)

    teacher_courses = Course.objects.filter(teacher=request.user).order_by("-created_at")
    selected_course = None

    if course_id.isdigit():
        selected_course = teacher_courses.filter(id=int(course_id)).first()
        if selected_course:
            qs = qs.filter(
                enrolments__course=selected_course,
                enrolments__status=Enrolment.Status.ACTIVE,
            ).distinct()

    qs = qs[:50]

    return render(
        request,
        "accounts/search.html",
        {
            "items": qs,
            "q": q,
            "role": role,
            "teacher_courses": teacher_courses,
            "selected_course": selected_course,
        },
    )