# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


cosinnus_root_patterns = patterns('',
                                   
    url(r'^stream/(?P<slug>[^/]+)/$', 'cosinnus_stream.views.stream_detail', name='stream'),
    url(r'^stream/(?P<slug>[^/]+)/edit/$', 'cosinnus_stream.views.stream_update', name='edit_stream'),
    url(r'^stream/$', 'cosinnus_stream.views.stream_detail', name='my_stream'),
    url(r'^stream/create$', 'cosinnus_stream.views.stream_create', name='create_stream'),
)


cosinnus_group_patterns = patterns('cosinnus_stream.views',
)

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
