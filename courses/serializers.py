from rest_framework import serializers

from .models import Course, Lesson, CourseMaterial


class CourseMaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CourseMaterial
        fields = [
            "id",
            "title",
            "material_type",
            "order",
            "file_url",
            "created_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        elif obj.file:
            return obj.file.url
        return None


class LessonSerializer(serializers.ModelSerializer):
    materials = CourseMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "order",
            "materials",
        ]


class CourseListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    material_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "is_visible",
            "created_at",
            "teacher_name",
            "lesson_count",
            "material_count",
        ]

    def get_teacher_name(self, obj):
        return obj.teacher.display_name or obj.teacher.username

    def get_lesson_count(self, obj):
        return obj.lessons.count()

    def get_material_count(self, obj):
        return obj.materials.count()


class CourseDetailSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "is_visible",
            "created_at",
            "teacher_name",
            "lessons",
        ]

    def get_teacher_name(self, obj):
        return obj.teacher.display_name or obj.teacher.username