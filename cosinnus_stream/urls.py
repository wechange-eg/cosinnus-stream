# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal


# user management not allowed in integrated mode
if not is_integrated_portal():
    cosinnus_root_patterns = patterns('',
                                       
        url(r'^activities/create/$', 'cosinnus_stream.views.stream_create', name='create_stream'),
        url(r'^activities/all/', 'cosinnus_stream.views.stream_detail', name='stream_public', kwargs={'is_all_portals': True}),
        url(r'^activities/(?P<slug>[^/]+)/$', 'cosinnus_stream.views.stream_detail', name='stream'),
        url(r'^activities/(?P<slug>[^/]+)/edit/$', 'cosinnus_stream.views.stream_update', name='edit_stream'),
        url(r'^activities/(?P<slug>[^/]+)/delete/$', 'cosinnus_stream.views.stream_delete', name='delete_stream'),
        url(r'^activities/$', 'cosinnus_stream.views.stream_detail', name='my_stream'),
    )
else:
    cosinnus_root_patterns = []

cosinnus_group_patterns = patterns('cosinnus_stream.views',
)

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
