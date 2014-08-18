# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import copy

from django.db.models import get_model
from django.views.generic.detail import DetailView

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from cosinnus.utils.permissions import get_tagged_object_filter_for_user
from cosinnus.models.group import CosinnusGroup
from cosinnus_stream.models import Stream


class StreamDetailView(DetailView):
    model = Stream
    template_name = 'cosinnus_stream/stream_detail.html'
    
    
    def dispatch(self, request, *args, **kwargs):
        return super(StreamDetailView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """ Allow queries without slug or pk """
        if self.pk_url_kwarg in self.kwargs or self.slug_url_kwarg in self.kwargs:
            return super(StreamDetailView, self).get_object(queryset)
        return None
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.querysets = self.get_querysets_for_stream(self.object)
        self.objects = self.get_objectset()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    def get_objectset(self):
        def get_sort_key(item):
            return item[1].sort_key

        stream = self.object
        limit = 30
        count = 0
        start = 0
        slice_len = 10
        
        """ We sample the first-sorted item from each of the querysets in each run,
            determining which of them is the overall-first-sorted.
            We slice the querysets to reduce database hits during this sampling and only
            evaluate a new slice as soon as we need to access older items from that queryset """
        
        # build iterator setlist to split-iterate over querysets
        setlist = {}
        for queryset in self.querysets:
            setlist[queryset.model.__name__] = {
                'qs': queryset,
                'objs': [],
                'offset': start
            } 
            
        objects = []
        
        while count < limit:
            first_items = {}
            for key, cur_set in copy(setlist).items():
                # if obj list in set is empty, sample new items from qs
                if not cur_set['objs']:
                    from_index = cur_set['offset']
                    cur_set['objs'] = list(cur_set['qs'][from_index:from_index+slice_len])
                    cur_set['offset'] = from_index+slice_len
                    if not cur_set['objs']:
                        # if queryset has no more items, remove it from the setlist of compilable sets
                        del setlist[key]
                        continue
                # objs now guaranteed to contain an item
                first_items[key] = cur_set['objs'][0]
            
            # stop collecting if all querysets are exhausted
            if not first_items:
                break
            
            # sort the list of each queryset's first item to get the very first
            # remove it from the set and add it to the final items
            first_item = sorted(first_items.iteritems(), key=get_sort_key, reverse=True)[0]
            setlist[first_item[0]]['objs'].pop(0)
            objects.append(first_item[1])
            
            count = len(objects)
        
        return objects
    
    def get_querysets_for_stream(self, stream):
        """ Returns all (still-lazy) querysets for models that will appear 
            in the current stream """
        querysets = []
        # [u'cosinnus_etherpad.Etherpad', u'cosinnus_event.Event', u'cosinnus_file.FileEntry', 'cosinnus_todo.TodoEntry']
        for registered_model in aor:
            Renderer = aor[registered_model]
            
            # filter out unwanted model types if set in the Stream
            if stream and stream.models and registered_model not in stream.models.split(','):
                continue
            
            app_label, model_name = registered_model.split('.')
            model_class = get_model(app_label, model_name)
            
            # get base collection of models for that type
            if BaseHierarchicalTaggableObjectModel in model_class.__bases__:
                queryset = model_class._default_manager.filter(is_container=False)
            else:
                queryset = model_class._default_manager.all()
            
            # filter for read permissions for user
            queryset = queryset.filter(get_tagged_object_filter_for_user(self.request.user))
            # filter for stream
            queryset = self.filter_queryset_for_stream(queryset, stream)
            # sorting
            queryset = self.sort_queryset(queryset, stream)
            querysets.append(queryset)
            
        return querysets
    
    def sort_queryset(self, queryset, stream):
        queryset = queryset.order_by('-created')
        return queryset
    
    def filter_queryset_for_stream(self, queryset, stream=None):
        """ Filter a BaseTaggableObjectModel-queryset depending on the settings 
            of the current stream """
        
        # objects only from user-groups for My-Stream
        if stream is None:
            self.user_group_ids = getattr(self, 'user_group_ids', CosinnusGroup.objects.get_for_user_pks(self.request.user))
            queryset = queryset.filter(group__pk__in=self.user_group_ids)
        else:
            if stream.group:
                queryset = queryset.filter(group__pk=stream.group.pk)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'stream': self.object,
            'stream_objects': self.objects,
        })
        return super(StreamDetailView, self).get_context_data(**kwargs)

stream_detail = StreamDetailView.as_view()
