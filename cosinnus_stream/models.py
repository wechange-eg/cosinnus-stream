# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models as django_models
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus_stream.mixins import StreamManagerMixin


class Stream(StreamManagerMixin, BaseTaggableObjectModel):
    
    class Meta(BaseTaggableObjectModel.Meta):
        verbose_name = _('Stream')
        verbose_name_plural = _('Streams')
    
    models = django_models.CharField(_('Models'), blank=True, null=True, max_length=255)
    is_my_stream = django_models.BooleanField(default=False)
    
    
    def get_absolute_url(self):
        kwargs = {'slug': self.slug}
        return reverse('cosinnus:stream', kwargs=kwargs)

    
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
