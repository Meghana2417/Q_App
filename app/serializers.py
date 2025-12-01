from rest_framework import serializers
from .models import Profile, TemporaryUser, Tag, Post, Reply, Reaction, ReplyReaction

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class TemporaryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryUser
        fields = ['token', 'display_name', 'created_at']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['display_name', 'avatar', 'is_anonymous_by_default']

class PostListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author_display = serializers.CharField(source='author_display_name', read_only=True)
    reaction_count = serializers.IntegerField(source='reactions.count', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'post_type', 'author_display', 'hide_identity', 'tags', 'reaction_count', 'created_at']

class PostDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author_display = serializers.CharField(source='author_display_name', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'post_type', 'author_display', 'hide_identity', 'tags', 'created_at', 'updated_at']

class ReplySerializer(serializers.ModelSerializer):
    author_display = serializers.CharField(source='author_display_name', read_only=True)

    class Meta:
        model = Reply
        fields = ['id', 'post', 'content', 'author_display', 'hide_identity', 'created_at']

from rest_framework import serializers
from .models import DiscussionRoom, DiscussionMessage

class DiscussionRoomSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    likes_count = serializers.SerializerMethodField()
    notify_count = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionRoom
        fields = "__all__"

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_notify_count(self, obj):
        return obj.notify_users.count()


class DiscussionMessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField()

    class Meta:
        model = DiscussionMessage
        fields = "__all__"


from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, TemporaryUser


class SignupSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "confirm_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            password=validated_data["password"]
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        data["user"] = user
        return data


class AnonymousLoginSerializer(serializers.Serializer):
    device_id = serializers.CharField()

    def create(self, validated_data):
        temp_user, created = TemporaryUser.objects.get_or_create(
            device_id=validated_data["device_id"]
        )
        return temp_user



from rest_framework import serializers
from .models import Story

class StorySerializer(serializers.ModelSerializer):
    snippet = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id", "title", "description", "snippet",
            "category", "anonymous", "author",
            "likes_count", "reads_count", "created_at"
        ]
        read_only_fields = ["likes_count", "reads_count"]

    def get_snippet(self, obj):
        return obj.snippet()

    def get_author(self, obj):
        return obj.author_name()

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)
