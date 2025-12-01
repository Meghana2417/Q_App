# accounts/models.py

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid


# -------------------------------
# Custom User Manager
# -------------------------------

class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None):
        if not email:
            raise ValueError("Email required")

        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, full_name, password):
        user = self.create_user(email, full_name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


# -------------------------------
# User Model
# -------------------------------

class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return self.email


# -------------------------------
# Profile Model
# -------------------------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=150, blank=True)
    avatar = models.URLField(blank=True)
    is_anonymous_by_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or self.user.email


# -------------------------------
# Temporary / Anonymous User
# -------------------------------

class TemporaryUser(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    display_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"temp:{self.display_name or str(self.token)[:8]}"


# -------------------------------
# Tag
# -------------------------------

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# -------------------------------
# Post Model
# -------------------------------

class Post(models.Model):
    POST_TYPE_CHOICES = (("problem", "Problem"), ("journey", "Journey"))

    title = models.CharField(max_length=255)
    description = models.TextField()

    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    temp_author = models.ForeignKey(TemporaryUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')

    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default="problem")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    hide_identity = models.BooleanField(default=False)
    saved_by = models.ManyToManyField(User, blank=True, related_name='saved_posts')

    class Meta:
        ordering = ['-created_at']

    def author_display_name(self):
        if self.hide_identity:
            return "Anonymous"
        if self.author:
            return self.author.profile.display_name or self.author.email
        if self.temp_author:
            return self.temp_author.display_name or "Anonymous"
        return "Anonymous"

    def __str__(self):
        return f"{self.title[:40]} - {self.post_type}"


# -------------------------------
# Reply Model
# -------------------------------

class Reply(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()

    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    temp_author = models.ForeignKey(TemporaryUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    hide_identity = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def author_display_name(self):
        if self.hide_identity:
            return "Anonymous"
        if self.author:
            return self.author.profile.display_name or self.author.email
        if self.temp_author:
            return self.temp_author.display_name or "Anonymous"
        return "Anonymous"

    def __str__(self):
        return self.content[:60]


# -------------------------------
# Post Reaction
# -------------------------------

class Reaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    temp_user = models.ForeignKey(TemporaryUser, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('post', 'user'),
            ('post', 'temp_user'),
        )


# -------------------------------
# Reply Reaction
# -------------------------------

class ReplyReaction(models.Model):
    REACTION_CHOICES = (('helpful', 'Helpful'), ('not_satisfied', 'Not satisfied'))

    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    temp_user = models.ForeignKey(TemporaryUser, null=True, blank=True, on_delete=models.CASCADE)

    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('reply', 'user'),
            ('reply', 'temp_user', 'reaction'),
        )


# -------------------------------
# Discussion System
# -------------------------------

class DiscussionRoom(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    )

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_rooms")
    topic = models.CharField(max_length=255)
    description = models.TextField()
    start_datetime = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    likes = models.ManyToManyField(User, related_name="interested_rooms", blank=True)
    notify_users = models.ManyToManyField(User, related_name="notify_rooms", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic


class DiscussionMessage(models.Model):
    room = models.ForeignKey(DiscussionRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} - {self.room.topic}"



from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import Truncator

User = get_user_model()


class Story(models.Model):

    CATEGORY_CHOICES = [
        ("depression", "Overcame Depression"),
        ("relationship", "Fixed My Relationship"),
        ("study", "Study Success Journey"),
        ("addiction", "Quit Addiction"),
        ("career", "Career Failures → Success"),
        ("friendship", "Friendship Breakups"),
        ("motivation", "Motivation"),
        ("growth", "Personal Growth"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stories"
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    
    anonymous = models.BooleanField(default=False)

    likes_count = models.PositiveIntegerField(default=0)  
    reads_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def snippet(self):
        return Truncator(self.description).chars(150)

    def author_name(self):
        if self.anonymous or not self.user:
            return "Anonymous"
        return self.user.email

    def __str__(self):
        return self.title
