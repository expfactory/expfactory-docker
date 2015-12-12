from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, TabHolder, Tab
from expdj.apps.turk.models import HIT
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from django.forms import ModelForm
from django import forms


class HITForm(ModelForm):

    class Meta:
        model = HIT
        fields = ("title","description","keywords","reward","lifetime_in_seconds",
                  "assignment_duration_in_seconds","max_assignments",
                  "auto_approval_delay_in_seconds")

    def clean(self):
        cleaned_data = super(HITForm, self).clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(HITForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))
