# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.core.urlresolvers import reverse
from django.db import models as django_models
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus_stream.mixins import StreamManagerMixin

class StreamManager(django_models.Manager):
    
    def my_stream_unread_count(self, user):
        if not user.is_authenticated:
            return 0
        stream = self.get_my_stream_for_user(user)
        return stream.unread_count()
    
    def get_my_stream_for_user(self, user):
        # try to find the user's MyStream, if not existing, create it
        stream = None
        try:
            stream = self.model._default_manager.get(creator=user, is_my_stream__exact=True)
        except self.model.DoesNotExist:
            stream = self.model._default_manager.create(creator=user, title="_my_stream", slug="_my_stream", is_my_stream=True)
        return stream    


class Stream(StreamManagerMixin, BaseTaggableObjectModel):
    
    AUTO_RENAME_SLUG_ON_SAVE = False
    
    class Meta(BaseTaggableObjectModel.Meta):
        verbose_name = _('Stream')
        verbose_name_plural = _('Streams')
        ordering = ['created']
    
    models = django_models.CharField(_('Models'), blank=True, null=True, max_length=255)
    is_my_stream = django_models.BooleanField(default=False)
    last_seen = django_models.DateTimeField(_('Last seen'), default=None, blank=True, null=True)
    
    objects = StreamManager()
    
    def set_last_seen(self, when=None):
        """ Set the last seen datetime for this stream. 
            Sets the datetime to now() if no argument is passed.
        """
        self.last_seen = when or now()
        if self.pk:
            self.save()
    
    @property
    def last_seen_safe(self):
        last_seen = self.last_seen or datetime.datetime(1990, 1, 1)
        return last_seen
    
    def get_absolute_url(self):
        kwargs = {'slug': self.slug}
        return reverse('cosinnus:stream', kwargs=kwargs)
    
    # def unread_count() is in the StreamManagerMixin!
    
""" We swap the unique together field for group for creator. Group is no longer required, but creator is. """
Stream._meta.get_field('group').blank = True
Stream._meta.get_field('group').null = True
Stream._meta.get_field('creator').blank = False
Stream._meta.get_field('creator').null = False
Stream._meta.unique_together = (('creator', 'slug'),)

    


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_stream import cosinnus_app
    cosinnus_app.register()
