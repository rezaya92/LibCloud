import mimetypes
import os

from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Count
from django import forms
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from libcloud.models import Attachment
from libcloud.models import Content, Library, ContentType, AttachmentType
from libcloud.models import ContentTypeFeature
from .forms import ContentForm, \
    ContentFeatureFormset, AttachmentFormset
from .forms import ContentTypeFeatureFormset, ContentTypeForm, AttachmentTypeForm
from .forms import NewUserForm


def home_page_view(request):
    context = {'1':'1',
               '2':'2'}
    current_user = request.user
    if request.user.is_authenticated:
        filter_file = Q()
        filter_lib = Q()
        filter_file |= Q(creator=current_user)
        filter_lib |= Q(user=current_user)
        files = Content.objects.filter(filter_file).order_by('-id')[:5]
        libs = Library.objects.filter(filter_lib).annotate(q_count=Count('content')) \
                                 .order_by('-q_count')
        context.update({'files': files,
                        'libraries' : libs})

    return render(request=request, template_name='libcloud/intro.html',context = context)


def get_lib(request):
    context = {}
    context.update({'1':'1',
               '2':'2'})
    current_user = request.user
    if request.user.is_authenticated:
        filter_lib = Q()
        filter_lib |= Q(user=current_user)
        libs = Library.objects.filter(filter_lib).annotate(q_count=Count('content')) \
                   .order_by('-q_count')
        context.update({'libraries': libs})
    return context


def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")

            return redirect("/")
        messages.error(request, "Unsuccessful registration. Invalid information.")
        return render(request=request, template_name='libcloud/register.html', context={"register_form": form},
                      status=400)
    form = NewUserForm()
    return render(request=request, template_name='libcloud/register.html', context={"register_form": form}, status=200)


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("/")
            else:
                messages.error(request, "Invalid username or password.")
                return render(request=request, template_name="libcloud/login.html", context={"login_form": form},
                              status=401)
        else:
            messages.error(request, "Invalid username or password.")
            return render(request=request, template_name="libcloud/login.html", context={"login_form": form},
                          status=401)
    form = AuthenticationForm()
    return render(request=request, template_name="libcloud/login.html", context={"login_form": form})


class ContentView(DetailView):
    model = Content


def download_file(request, user_prefix, filename):
    if request.method == "GET":
        file_path = os.path.join(settings.MEDIA_ROOT, user_prefix, filename)
        if not os.path.exists(file_path):
            messages.error(request, f"{filename} doesn't exists.")
            return redirect("/")

        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type, status=200)
            response['Content-Disposition'] = "attachment; filename=%s" % filename
            return response
    else:
        return redirect('libcloud:download_file', user_prefix, filename)


@login_required
def create_content(request, content_type_pk=-1):
    content_type_pk = int(content_type_pk)
    if request.method == "POST":
        # print(request.POST)
        # print(request.FILES)
        content_type = ContentType.objects.get(id=content_type_pk)
        form = ContentForm(request.POST, request.FILES, prefix='content', user=request.user)
        formset_features = ContentFeatureFormset(request.POST,
                                                 prefix="feature")
        formset_attachments = AttachmentFormset(request.POST, request.FILES,
                                                prefix="attachment",
                                                form_kwargs={'content_type': content_type})

        if form.is_valid() and formset_features.is_valid() and formset_attachments.is_valid():
            try:
                with transaction.atomic():
                    content = form.save(commit=True)
                    for form1 in formset_features:
                        if form1.instance.required or form1.cleaned_data['value'] != '':
                            content_feature = form1.save(commit=False)
                            content_feature.content = content
                            content_feature.save()
                    for form1 in formset_attachments:
                        attachment = form1.save(commit=False)
                        attachment.content = content
                        attachment.save()
                    messages.info(request, "content has been created.")
            except Exception as e:
                messages.error(request, e)
                redirect("libcloud:create_content")
            pass
        else:
            messages.error(request, form.errors)
            messages.error(request, formset_features.errors)
            messages.error(request, formset_attachments.errors)
            # for form1 in formset_features:
            #     print(form1)
            #     print(form1.data)
            redirect("libcloud:create_content")
    if content_type_pk != -1:
        content_type = ContentType.objects.get(id=content_type_pk)
        form = ContentForm(prefix='content', user=request.user,
                           initial={'type': content_type})
        formset_features = ContentFeatureFormset(queryset=content_type.contenttypefeature_set.all(),
                                                 prefix="feature")
        formset_attachments = AttachmentFormset(queryset=Attachment.objects.none(),
                                                prefix="attachment",
                                                form_kwargs={'content_type': content_type})
        # print(formset_features)
        # for form1 in formset_features:
        #     print(form1.as_table())
        return render(request, 'libcloud/upload_form.html', {
            'form': form, 'formset_features': formset_features, 'formset_attachments': formset_attachments})
    else:
        form = ContentForm(prefix='content', user=request.user)
        return render(request, 'libcloud/upload_form.html', {
            'form': form, 'formset_features': None, 'formset_attachments': None}, status=200)


@login_required
def create_content_type(request):
    if request.method == "POST":
        print(request.POST)
        form = ContentTypeForm(request.POST, initial={'user': request.user}, prefix='content-type')
        formset = ContentTypeFeatureFormset(request.POST, prefix="feature")

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    content_type = form.save(commit=True)
                    form.save_m2m()
                    print(content_type.attachment_types.all())
                    for form1 in formset:
                        content_type_feature = form1.save(commit=False)
                        content_type_feature.content_type = content_type
                        content_type_feature.save()
            except Exception as e:
                messages.error(request, e)
                redirect("libcloud:create_content_type")
        else:
            messages.error(request, form.errors)
            messages.error(request, formset.errors)
            redirect("libcloud:create_content_type")
    form = ContentTypeForm(prefix='content-type', initial={'user': request.user})
    formset = ContentTypeFeatureFormset(queryset=ContentTypeFeature.objects.none(), prefix="feature")
    for form1 in formset:
        print(form1.as_table())
    return render(request, 'libcloud/contenttype_form.html', {
        'form': form, 'formset': formset})


@login_required
def my_attachment_types(request):
    if request.method == "POST":
        print(request.POST)
        form = AttachmentTypeForm(request.POST)

        if form.is_valid():
            attachment_type = form.save(commit=False)
            attachment_type.user = request.user
            attachment_type.save()
            messages.info(request, f"attachment type {attachment_type.name} has been created")
        else:
            messages.error(request, form.errors)
    form = AttachmentTypeForm()
    return render(request, 'libcloud/attachmenttype_list.html', {
        'form': form, 'attachment_types': AttachmentType.objects.filter(user=request.user)}, status=200)


def my_content_types(request):
    print(ContentType.objects.filter(user=request.user))
    return render(request, 'libcloud/contenttype_list.html', {
        'content_types': ContentType.objects.filter(user=request.user)})


def logout_request(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("/")


class AllLibrariesView(ListView):
    model = Library

    def get_queryset(self):
        return Library.objects.filter(user=self.request.user)


class EachLibraryView(DetailView):
    model = Library

    def get_queryset(self):
        return Library.objects.filter(user=self.request.user)


class LibraryForm(forms.ModelForm):

    class Meta:
        model = Library
        fields = ['name', 'content_type']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(LibraryForm, self).__init__(*args, **kwargs)
        self.fields['content_type'].queryset = ContentType.objects.filter(user=user)


class LibraryCreateView(CreateView):
    model = Library
    form_class = LibraryForm

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        return super(LibraryCreateView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MyContentView(ListView):
    model = Content

    def get_queryset(self):
        return Content.objects.filter(creator=self.request.user)


class MyContentTypeView(ListView):
    model = ContentType

    def get_queryset(self):
        return ContentType.objects.filter(user=self.request.user)


class MyAttachmentTypeView(ListView):
    model = AttachmentType

    def get_queryset(self):
        return AttachmentType.objects.filter(user=self.request.user)


class AttachmentTypeCreateView(CreateView):
    model = AttachmentType
    fields = ['name']

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        return super(AttachmentTypeCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('libcloud:my_attachment_types')


class ContentTypeCreateView(CreateView):
    model = ContentType
    fields = ['name']

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        return super(ContentTypeCreateView, self).form_valid(form)


class EachContentTypeView(DetailView):
    model = ContentType


class LibrarySelectForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = ['library']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        content_type = kwargs.pop('content_type')
        super().__init__(*args, **kwargs)
        self.fields['library'].queryset = Library.objects.filter(user=user,
                                                                 content_type=content_type)
        self.fields['library'].label_from_instance = lambda obj: "%s" % obj.name


class LibrarySelectView(UpdateView):
    form_class = LibrarySelectForm
    model = Content

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['content_type'] = Content.objects.get(pk=self.kwargs["pk"]).type
        return kwargs

    def form_valid(self, form):
        content = form.save(commit=False)
        if content.library is not None and content.library not in list(content.creator.library_set.all()):
            form.add_error('library', 'invalid library')
            return super().form_invalid(form)
        else:
            return super().form_valid(form)


class AttachmentForm(forms.ModelForm):

    class Meta:
        model = Attachment
        fields = ['type', 'file']

    def __init__(self, *args, **kwargs):
        content_type = kwargs.pop('content_type')
        self.helper = FormHelper()
        self.helper.form_tag = False
        super(AttachmentForm, self).__init__(*args, **kwargs)
        self.fields['type'].queryset = content_type.attachment_types.all()


class AttachmentCreateView(CreateView):

    model = Attachment
    form_class = AttachmentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['content_type'] = Content.objects.get(pk=self.kwargs["content_pk"]).type
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        content = Content.objects.get(pk=self.kwargs['content_pk'])
        obj.content = content
        if obj.type not in list(obj.content.type.attachment_types.all()):
            form.add_error('type', 'invalid attachment type')
            return super(AttachmentCreateView, self).form_invalid(form)
        else:
            return super().form_valid(form)
