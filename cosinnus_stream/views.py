# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic.detail import DetailView

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus_stream.models import Stream
from cosinnus.views.mixins.user import UserFormKwargsMixin
from cosinnus_stream.forms import StreamForm
from django.contrib import messages
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy, reverse
from cosinnus.templatetags.cosinnus_tags import has_write_access
from cosinnus.core.decorators.views import redirect_to_403


class StreamDetailView(DetailView):
    model = Stream
    template_name = 'cosinnus_stream/stream_detail.html'
    
    def dispatch(self, request, *args, **kwargs):
        return super(StreamDetailView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """ Allow queries without slug or pk """
        if self.pk_url_kwarg in self.kwargs or self.slug_url_kwarg in self.kwargs:
            self.object = super(StreamDetailView, self).get_object(queryset)
        
        if not hasattr(self, 'object'):
            # no object supplied means we want to access the "MyStream"
            # for guests, return a virtual stream
            if not self.request.user.is_authenticated():
                self.object = self.model(is_my_stream=True)
            else:
                self.object = self.model._default_manager.get_my_stream_for_user(self.request.user)
        return self.object
    
    def get_streams(self):
        if not self.request.user.is_authenticated():
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(creator__id=self.request.user.id, is_my_stream__exact=False)
        return qs
    
    def check_permissions(self):
        if self.object and hasattr(self.object, 'creator') and not self.object.creator == self.request.user:
            raise PermissionDenied(_('You do not have permission to access this stream.'))
        
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_permissions()
        
        self.objects = self.object.get_stream_objects_for_user(self.request.user)
        self.streams = self.get_streams()
        
        # save last_seen date and set it to current
        self.last_seen = self.object.last_seen_safe
        if request.user.is_authenticated():
            self.object.set_last_seen()
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'total_count': self.object.total_count,
            'has_more': self.object.has_more,
            'has_more_count': max(0, self.object.total_count - len(self.objects)),
            'last_seen': self.last_seen,
            'stream': self.object,
            'stream_objects': self.objects,
            'streams': self.streams,
        })
        return super(StreamDetailView, self).get_context_data(**kwargs)

stream_detail = StreamDetailView.as_view()


class StreamFormMixin(object):
    
    form_class = StreamForm
    model = Stream
    template_name = 'cosinnus_stream/stream_form.html'
    
    
    def get_streams(self):
        if not self.request.user.is_authenticated():
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(creator__id=self.request.user.id, is_my_stream__exact=False)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(StreamFormMixin, self).get_context_data(**kwargs)
        
        model_selection = []
        for model_name in aor:
            # label for the checkbox is the app identifier translation
            app = model_name.split('.')[0].split('_')[-1]
            model_selection.append({
                'model_name': model_name,
                'app': app,
                'label': pgettext_lazy('the_app', app),
                'checked': True if (not self.object or not self.object.models) else model_name in self.object.models,
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
        return super(StreamFormMixin, self).form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class StreamCreateView(UserFormKwargsMixin, StreamFormMixin, CreateView):

    form_view = "add"
    message_success = _('Your stream was added successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        return super(StreamCreateView, self).dispatch(request, *args, **kwargs)
    

stream_create = StreamCreateView.as_view()


class StreamUpdateView(UserFormKwargsMixin, StreamFormMixin, UpdateView):

    form_view = "edit"
    message_success = _('Your stream was updated successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        if not has_write_access(request.user, self.get_object()):
            return redirect_to_403(request)
        return super(StreamUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        if hasattr(self, 'object'):
            return self.object
        return super(StreamUpdateView, self).get_object(queryset)

stream_update = StreamUpdateView.as_view()



class StreamDeleteView(UserFormKwargsMixin, DeleteView):

    model = Stream
    message_success = _('Your stream was deleted successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        
        self.object = self.get_object()
        if not has_write_access(request.user, self.object):
            return redirect_to_403(request)
        
        if self.object.is_my_stream:
            messages.error(request, _('You cannot delete the default stream!'))
            return HttpResponseRedirect(reverse('cosinnus:my_stream'))
        
        return super(StreamDeleteView, self).dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return reverse('cosinnus:my_stream')

stream_delete = StreamDeleteView.as_view()

