from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *

router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'posts', PostViewSet, basename='posts')
router.register(r'replies', ReplyViewSet, basename='replies')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/create/', CreateRoomView.as_view()),
    path('api/rooms/', RoomListView.as_view()),
    path('api/rooms/<int:pk>/', RoomDetailView.as_view()),
    path('api/rooms/<int:pk>/interested/', ToggleInterestedView.as_view()),
    path('api/rooms/<int:pk>/notify/', ToggleNotifyView.as_view()),
    path('api/rooms/<int:pk>/start/', StartRoomView.as_view()),
    path('api/rooms/<int:pk>/end/', EndRoomView.as_view()),
    path('api/rooms/<int:room_id>/send/', SendMessageView.as_view()),
    path("api/signup/", SignupView.as_view(), name="signup"),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/anonymous-login/", AnonymousLoginView.as_view(), name="anonymous-login"),
    path("api/stories/", StoryListCreateView.as_view(), name="story-list"),
    path("api/stories/<int:pk>/", StoryDetailView.as_view(), name="story-detail"),
    path("api/stories/<int:story_id>/like/", like_story, name="story-like"),


]