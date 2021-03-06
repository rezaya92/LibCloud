from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Create your forms here.
from django.forms import ModelForm, Form, formset_factory, inlineformset_factory, modelformset_factory, \
    BaseModelFormSet, Field, TextInput

from libcloud.models import ContentType, ContentTypeFeature, AttachmentType, Content, ContentFeature, Library, \
    Attachment


class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ContentTypeForm(ModelForm):
    class Meta:
        model = ContentType
        fields = ("name", "attachment_types")
        labels = {
            'name': _('Content type name'),
        }
        widgets = {
            'attachment_types': forms.CheckboxSelectMultiple,
        }

    prefix = 'content-type'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = kwargs["initial"]['user']
        self.fields['attachment_types'].queryset = AttachmentType.objects.filter(user=self.user)

    def save(self, commit=True):
        content_type = super().save(commit=False)
        content_type.user = self.user
        if commit:
            content_type.save()
        return content_type


class ContentTypeFeatureForm(ModelForm):
    class Meta:
        model = ContentTypeFeature
        fields = ("name", "type", "required")

    prefix = 'feature'

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline justify-content-center'
        self.helper.field_template = 'libcloud/layout/inline_field.html'
        self.helper.form_tag = False
        super().__init__(*args, **kwargs)

        self.fields["name"].widget.attrs['required'] = 'required'
        self.fields["type"].widget.attrs['required'] = 'required'


class AttachmentTypeForm(ModelForm):
    class Meta:
        model = AttachmentType
        fields = ("name",)
        labels = {
            'name': _('New Attachment type'),
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline justify-content-center'
        self.helper.field_template = 'libcloud/layout/inline_field.html'
        # self.helper.form_tag = False
        super().__init__(*args, **kwargs)


class ContentForm(ModelForm):
    class Meta:
        model = Content
        fields = ("type", "file", "library")
        labels = {
            'type': _('Content type'),
        }

    prefix = 'content'

    def __init__(self, *args, user, **kwargs, ):
        super().__init__(*args, **kwargs)

        self.user = user
        self.fields['type'].queryset = ContentType.objects.filter(user=self.user)
        self.fields['type'].label_from_instance = lambda obj: "%s" % obj.name

        if 'type' in self.initial:
            self.fields['library'].queryset = self.initial['type'].library_set.all()
        else:
            self.fields['library'].queryset = Library.objects.filter(user=self.user)
        self.fields['library'].label_from_instance = lambda obj: "%s" % obj.name

    def save(self, commit=True):
        content = super().save(commit=False)
        content.creator = self.user
        if commit:
            content.save()
        return content


class ContentFeatureForm(ModelForm):
    class Meta:
        model = ContentTypeFeature
        # exclude = ("name", "type", "required")
        fields = ("id",)

    name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'size': 8}))
    type = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'size': 5}))
    required = forms.CharField(max_length=10, widget=forms.HiddenInput())

    prefix = 'feature'

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline justify-content-center'
        self.helper.field_template = 'libcloud/layout/inline_field.html'
        self.helper.form_tag = False
        super().__init__(*args, **kwargs)

        # if self.is_bound:
        if self.instance.type == ContentTypeFeature.FeatureType.String:
            self.fields["value"] = forms.CharField(max_length=50, required=self.instance.required)
            # self.fields["value"].label = f"value ({self.instance.get_type_display()})"
        elif self.instance.type == ContentTypeFeature.FeatureType.Number:
            # self.fields["value"] = forms.CharField(max_length=50, widget=TextInput(attrs={'type':'number'}))
            self.fields["value"] = forms.FloatField(required=self.instance.required)
            # self.fields["value"].label = f"value ({self.instance.get_type_display()})"
        elif self.instance.type == ContentTypeFeature.FeatureType.Boolean:
            self.fields["value"] = forms.ChoiceField(choices=(('', '----'),
                                                              ("1", "True"),
                                                              ("2", "False")),
                                                     required=self.instance.required)

        self.fields["name"].widget.attrs['readonly'] = True
        self.fields["type"].widget.attrs['readonly'] = True
        self.fields["required"].widget.attrs['readonly'] = True

        if self.instance.required:
            self.fields["value"].widget.attrs['required'] = 'required'

        self.fields["name"].initial = self.instance.name
        self.fields["type"].initial = self.instance.get_type_display()
        self.fields["required"].initial = "Required" if self.instance.required else " Optional"

    def save(self, commit=True):
        content_feature = ContentFeature(feature_type=self.instance, value=self.cleaned_data['value'])
        return content_feature


class AttachmentForm(ModelForm):
    class Meta:
        model = Attachment
        fields = ("type", "file")

    prefix = 'attachment'

    def __init__(self, *args, content_type, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline justify-content-center'
        self.helper.field_template = 'libcloud/layout/inline_field.html'
        self.helper.form_tag = False
        super().__init__(*args, **kwargs)

        self.fields['type'].queryset = content_type.attachment_types.all()
        self.fields["type"].widget.attrs['required'] = 'required'
        self.fields["file"].widget.attrs['required'] = 'required'


ContentTypeFeatureFormset = modelformset_factory(ContentTypeFeature, form=ContentTypeFeatureForm, extra=1,
                                                 absolute_max=20, max_num=20)

ContentFeatureFormset = modelformset_factory(ContentTypeFeature, form=ContentFeatureForm,
                                             extra=0,
                                             absolute_max=20, max_num=20)

AttachmentFormset = modelformset_factory(Attachment, form=AttachmentForm, extra=1,
                                         absolute_max=20, max_num=20)
