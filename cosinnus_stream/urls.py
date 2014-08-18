# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


cosinnus_root_patterns = patterns('',
                                   
    url(r'^stream/(?P<slug>[^/]+)/$', 'cosinnus_stream.views.stream_detail', name='stream'),
    url(r'^stream/$', 'cosinnus_stream.views.stream_detail', name='my_stream'),
                                                                    
)


cosinnus_group_patterns = patterns('cosinnus_stream.views',
)

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
