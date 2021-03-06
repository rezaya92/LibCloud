import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Model
from django.urls import reverse


def get_sentinel_user():
    return User.objects.get_or_create(username='deleted')[0]


def get_content_upload_path(instance, filename):
    return os.path.join(
        "user_%s" % instance.creator.username, filename)


class AttachmentType(Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(blank=False, max_length=40)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return " " + self.name


class ContentType(Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(blank=False, max_length=40)
    attachment_types = models.ManyToManyField(AttachmentType, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('libcloud:each_content_type', kwargs={'pk': self.pk})


class ContentTypeFeature(Model):
    class FeatureType(models.IntegerChoices):
        Number = 1
        String = 2
        Boolean = 3
        # TODO

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    type = models.IntegerField(choices=FeatureType.choices)
    required = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Library(Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    content_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse('libcloud:each_library', kwargs={'pk': self.pk})


class Content(Model):
    creator = models.ForeignKey(User, on_delete=models.SET(get_sentinel_user))
    type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_content_upload_path)
    library = models.ForeignKey(to=Library, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def filename(self):
        return os.path.basename(self.file.name)

    def get_absolute_url(self):
        return reverse('libcloud:content', kwargs={'pk': self.pk})

    def clean(self):
        super().clean()
        if self.library is not None:
            if self.library.content_type != self.type:
                raise ValidationError("chosen library has a different content type")


class ContentFeature(Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    feature_type = models.ForeignKey(ContentTypeFeature, on_delete=models.CASCADE, null=True)
    value = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def get_attachment_upload_path(instance, filename):
    return "_".join(["%s" % os.path.splitext(instance.content.file.name)[0], filename])


class Attachment(Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    type = models.ForeignKey(AttachmentType, on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_attachment_upload_path)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('libcloud:content', kwargs={'pk': self.content.pk})

    def filename(self):
        return os.path.basename(self.file.name)
