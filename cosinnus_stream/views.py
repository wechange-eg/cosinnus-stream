# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import copy

from django.core.exceptions import PermissionDenied
from django.db.models import get_model, Q
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic.detail import DetailView

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from cosinnus.utils.permissions import get_tagged_object_filter_for_user
from cosinnus.models.group import CosinnusGroup
from cosinnus_stream.models import Stream
from cosinnus.views.mixins.group import RequireWriteMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin
from cosinnus_stream.forms import StreamForm
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy


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
    
    def get_streams(self):
        if not self.request.user.is_authenticated():
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(creator__id=self.request.user.id)
        return qs
    
    def check_permissions(self):
        if self.object and not self.object.creator == self.request.user:
            raise PermissionDenied(_('You do not have permission to access this stream.'))
        
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_permissions()
        
        self.querysets = self.get_querysets_for_stream(self.object)
        self.objects = self.get_objectset()
        self.streams = self.get_streams()
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
            of the current stream.
            Called during the getting of the querysets and before objects are extracted.
        """
        
        if stream is None:
            # objects only from user-groups for My-Stream
            if self.request.user.is_authenticated():
                self.user_group_ids = getattr(self, 'user_group_ids', CosinnusGroup.objects.get_for_user_pks(self.request.user))
                queryset = queryset.filter(group__pk__in=self.user_group_ids)
            else:
                # objects from public groups for Public Stream
                queryset = queryset.filter(group__public=True)
        else:
            # filter by group if set in stream
            if stream.group:
                queryset = queryset.filter(group__pk=stream.group.pk)
            if stream.media_tag:
                if stream.media_tag.topics:
                    q = None
                    # beware: this simple filter works because topics are built on a comma-separated
                    # integer field and have only ids from 1 to 9. as soon as there would be ids like
                    # id=12, id=1 would match that as well!
                    for topic in stream.media_tag.topics.split(','):
                        newq = Q(media_tag__topics__contains=topic)
                        q = q and q|newq or newq
                    queryset = queryset.filter(q) 
        
        return queryset
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'stream': self.object,
            'stream_objects': self.objects,
            'streams': self.streams,
        })
        return super(StreamDetailView, self).get_context_data(**kwargs)

stream_detail = StreamDetailView.as_view()


class StreamCreateView(UserFormKwargsMixin, CreateView):

    form_class = StreamForm
    model = Stream
    template_name = 'cosinnus_stream/stream_form.html'
    form_view = "add"
    
    message_success = _('Your stream was added successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        return super(StreamCreateView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        #import ipdb; ipdb.set_trace();
        print ">>post:", request.POST
        return super(StreamCreateView, self).post(request, *args, **kwargs)
    
    def get_streams(self):
        if not self.request.user.is_authenticated():
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(creator__id=self.request.user.id)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(StreamCreateView, self).get_context_data(**kwargs)
        
        model_selection = []
        for model_name in aor:
            # label for the checkbox is the app identifier translation
            app = model_name.split('.')[0].split('_')[-1]
            model_selection.append({
                'model_name': model_name,
                'app': app,
                'label': pgettext_lazy('the_app', app),
                'checked': True if (not self.object or self.object.models) else model_name in self.object.models,
            })
            
        context.update({
            'stream_model_selection': model_selection,
            'streams': self.get_streams(),
            'form_view': self.form_view,
        })
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        messages.success(self.request, self.message_success)
        return super(StreamCreateView, self).form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()

stream_create = StreamCreateView.as_view()
