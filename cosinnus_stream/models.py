# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.tagged import BaseTaggableObjectModel
from django.core.urlresolvers import reverse


class Stream(BaseTaggableObjectModel):
    
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
