from crispy_forms.bootstrap import (AppendedText, FormActions, PrependedText,
                                    StrictButton, Tab, TabHolder)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (HTML, Button, Div, Field, Hidden, Layout, Row,
                                 Submit)
from django import forms
from django.contrib.auth.forms import (PasswordChangeForm, UserChangeForm,
                                       UserCreationForm)
from django.contrib.auth.models import User


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):

        super(UserCreateForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()


class UserEditForm(UserChangeForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super(UserChangeForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def clean_password(self):
        return ""

    def __init__(self, *args, **kwargs):

        super(UserEditForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
