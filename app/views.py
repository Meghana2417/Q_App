from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q
import random

from .models import Post, Reply, Tag, TemporaryUser, Reaction, ReplyReaction
from .serializers import PostListSerializer, PostDetailSerializer, ReplySerializer, TagSerializer, TemporaryUserSerializer
from .permissions import CanPostAnonymous

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.prefetch_related('tags', 'reactions').all()
    permission_classes = [CanPostAnonymous]

    def get_serializer_class(self):
        if self.action in ['list', 'recommended', 'random_feed', 'mixed_feed']:
            return PostListSerializer
        return PostDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            # default: order by newest first
            return queryset.order_by('-created_at')
        return queryset

    def perform_create(self, serializer):
        temp_token = self.request.data.get('temp_token') or self.request.headers.get('X-Temp-Token')
        hide_identity = self.request.data.get('hide_identity', False)
        with transaction.atomic():
            if self.request.user.is_authenticated:
                serializer.save(author=self.request.user, hide_identity=hide_identity)
            elif temp_token:
                temp_user, _ = TemporaryUser.objects.get_or_create(token=temp_token)
                serializer.save(temp_author=temp_user, hide_identity=hide_identity)
            else:
                temp_user = TemporaryUser.objects.create()
                serializer.save(temp_author=temp_user, hide_identity=True)

    # -----------------------------
    # 🌀 Random Feed for Homepage
    # -----------------------------
    @action(detail=False, methods=['get'])
    def random_feed(self, request):
        count = Post.objects.count()
        sample_size = min(10, count)
        if count == 0:
            return Response([])
        random_indices = random.sample(range(count), sample_size)
        posts = list(Post.objects.all()[0:count])
        posts = [posts[i] for i in random_indices]
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    # -----------------------------
    # 🤖 Personalized Recommendations
    # -----------------------------
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        user = request.user
        temp_token = request.headers.get('X-Temp-Token')
        if user.is_authenticated:
            reacted_posts = Reaction.objects.filter(user=user).values_list('post', flat=True)
        elif temp_token:
            temp_user, _ = TemporaryUser.objects.get_or_create(token=temp_token)
            reacted_posts = Reaction.objects.filter(temp_user=temp_user).values_list('post', flat=True)
        else:
            return self.random_feed(request)

        related_tags = Tag.objects.filter(posts__in=reacted_posts).distinct()
        recommended_posts = Post.objects.filter(tags__in=related_tags).exclude(id__in=reacted_posts).distinct()

        if not recommended_posts.exists():
            return self.random_feed(request)

        serializer = self.get_serializer(recommended_posts.order_by('?')[:10], many=True)
        return Response(serializer.data)

    # -----------------------------
    # 🧩 Mixed Feed (Random + Recommended)
    # -----------------------------
    @action(detail=False, methods=['get'])
    def mixed_feed(self, request):
        random_feed_response = self.random_feed(request)
        recommended_feed_response = self.recommended(request)

        random_posts = random_feed_response.data if isinstance(random_feed_response.data, list) else []
        recommended_posts = recommended_feed_response.data if isinstance(recommended_feed_response.data, list) else []

        mixed_posts = list({post['id']: post for post in (random_posts + recommended_posts)}.values())
        random.shuffle(mixed_posts)

        return Response(mixed_posts[:20])

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        post = self.get_object()
        temp_token = request.data.get('temp_token') or request.headers.get('X-Temp-Token')
        if request.user.is_authenticated:
            obj, created = Reaction.objects.get_or_create(post=post, user=request.user)
            if not created:
                obj.delete()
                return Response({'status': 'removed'})
            return Response({'status': 'added'})
        elif temp_token:
            temp_user, _ = TemporaryUser.objects.get_or_create(token=temp_token)
            obj, created = Reaction.objects.get_or_create(post=post, temp_user=temp_user)
            if not created:
                obj.delete()
                return Response({'status': 'removed'})
            return Response({'status': 'added'})
        return Response({'detail': 'temp_token required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[CanPostAnonymous])
    def save(self, request, pk=None):
        post = self.get_object()
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required to save posts.'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user in post.saved_by.all():
            post.saved_by.remove(request.user)
            return Response({'status': 'unsaved'})
        post.saved_by.add(request.user)
        return Response({'status': 'saved'})

class ReplyViewSet(viewsets.ModelViewSet):
    queryset = Reply.objects.select_related('post').all()
    serializer_class = ReplySerializer
    permission_classes = [CanPostAnonymous]

    def perform_create(self, serializer):
        temp_token = self.request.data.get('temp_token') or self.request.headers.get('X-Temp-Token')
        hide_identity = self.request.data.get('hide_identity', False)
        with transaction.atomic():
            if self.request.user.is_authenticated:
                serializer.save(author=self.request.user, hide_identity=hide_identity)
            elif temp_token:
                temp_user, _ = TemporaryUser.objects.get_or_create(token=temp_token)
                serializer.save(temp_author=temp_user, hide_identity=hide_identity)
            else:
                temp_user = TemporaryUser.objects.create()
                serializer.save(temp_author=temp_user, hide_identity=True)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        reply = self.get_object()
        reaction = request.data.get('reaction')
        if reaction not in ['helpful', 'not_satisfied']:
            return Response({'detail': 'invalid reaction'}, status=status.HTTP_400_BAD_REQUEST)
        temp_token = request.data.get('temp_token') or request.headers.get('X-Temp-Token')
        if request.user.is_authenticated:
            obj, created = ReplyReaction.objects.get_or_create(reply=reply, user=request.user, reaction=reaction)
            if not created:
                obj.delete()
                return Response({'status': 'removed'})
            return Response({'status': 'added'})
        elif temp_token:
            temp_user, _ = TemporaryUser.objects.get_or_create(token=temp_token)
            obj, created = ReplyReaction.objects.get_or_create(reply=reply, temp_user=temp_user, reaction=reaction)
            if not created:
                obj.delete()
                return Response({'status': 'removed'})
            return Response({'status': 'added'})
        return Response({'detail': 'temp_token required'}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import DiscussionRoom, DiscussionMessage
from .serializers import DiscussionRoomSerializer, DiscussionMessageSerializer


# Create a discussion room
class CreateRoomView(generics.CreateAPIView):
    queryset = DiscussionRoom.objects.all()
    serializer_class = DiscussionRoomSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class RoomListView(generics.ListAPIView):
    queryset = DiscussionRoom.objects.all().order_by('-created_at')
    serializer_class = DiscussionRoomSerializer


class RoomDetailView(generics.RetrieveAPIView):
    queryset = DiscussionRoom.objects.all()
    serializer_class = DiscussionRoomSerializer


# Mark interested (like button)
class ToggleInterestedView(generics.GenericAPIView):
    queryset = DiscussionRoom.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        room = self.get_object()
        user = request.user

        if user in room.likes.all():
            room.likes.remove(user)
            return Response({"message": "Interest removed"})
        else:
            room.likes.add(user)
            return Response({"message": "Interested"})


# Notify Me
class ToggleNotifyView(generics.GenericAPIView):
    queryset = DiscussionRoom.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        room = self.get_object()
        user = request.user

        if user in room.notify_users.all():
            room.notify_users.remove(user)
            return Response({"message": "Removed from notifications"})
        else:
            room.notify_users.add(user)
            return Response({"message": "You will be notified"})


# Start Room (Admin/User who created)
class StartRoomView(generics.GenericAPIView):
    queryset = DiscussionRoom.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        room = self.get_object()

        if room.created_by != request.user:
            return Response({"error": "Only creator can start"}, status=403)

        room.status = "active"
        room.save()

        return Response({"message": "Room started"})


# End Room
class EndRoomView(generics.GenericAPIView):
    queryset = DiscussionRoom.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        room = self.get_object()

        if room.created_by != request.user:
            return Response({"error": "Only creator can end"}, status=403)

        room.status = "ended"
        room.save()

        return Response({"message": "Room ended"})


# Send messages
class SendMessageView(generics.CreateAPIView):
    serializer_class = DiscussionMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        room = DiscussionRoom.objects.get(id=self.kwargs['room_id'])
        serializer.save(sender=self.request.user, room=room)


# accounts/views.py

from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import SignupSerializer, LoginSerializer, AnonymousLoginSerializer
from .models import TemporaryUser


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class SignupView(GenericAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "message": "Account created",
            "tokens": tokens,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response({
            "message": "Login successful",
            "tokens": tokens,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        })


class AnonymousLoginView(GenericAPIView):
    serializer_class = AnonymousLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        temp_user = serializer.save()

        # Create a fake user object for JWT identity
        refresh = RefreshToken()
        refresh["anon_user_id"] = temp_user.id
        refresh["type"] = "anonymous"

        return Response({
            "message": "Anonymous session created",
            "anon_user_id": temp_user.id,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        })




from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import F
from .models import Story
from .serializers import StorySerializer

# CREATE + LIST STORIES
class StoryListCreateView(generics.ListCreateAPIView):
    queryset = Story.objects.all().order_by("-created_at")
    serializer_class = StorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Story.objects.all().order_by("-created_at")
        category = self.request.query_params.get("category")

        if category:
            queryset = queryset.filter(category=category)

        return queryset


# RETRIEVE SINGLE STORY + INCREASE READ COUNT
class StoryDetailView(generics.RetrieveAPIView):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        story = self.get_object()
        
        Story.objects.filter(id=story.id).update(reads_count=F('reads_count') + 1)

        return super().get(request, *args, **kwargs)


# LIKE A STORY
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def like_story(request, story_id):
    try:
        Story.objects.filter(id=story_id).update(likes_count=F("likes_count") + 1)
        return Response({"message": "Liked"})
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)
