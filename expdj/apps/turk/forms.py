from crispy_forms.bootstrap import (AppendedText, FormActions, PrependedText,
                                    StrictButton, Tab, TabHolder)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (HTML, Button, Div, Field, Hidden, Layout, Row,
                                 Submit)
from django import forms
from django.forms import ModelForm

from expdj.apps.turk.models import HIT


class HITForm(ModelForm):

    class Meta:
        model = HIT
        fields = (
            "title",
            "description",
            "sandbox",
            "keywords",
            "reward",
            "lifetime_in_hours",
            "assignment_duration_in_hours",
            "max_assignments",
            "auto_approval_delay_in_seconds",
            "qualification_number_hits_approved",
            "qualification_percent_assignments_approved",
            "qualification_adult",
            "qualification_locale",
            "qualification_custom",
            "qualification_custom_operator",
            "qualification_custom_value")

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


class WorkerContactForm(forms.Form):
    subject = forms.CharField(label="Subject")
    message = forms.CharField(widget=forms.Textarea, label="Message")

    def __init__(self, *args, **kwargs):
        super(WorkerContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout()
        self.helper.add_input(Submit("submit", "Send"))
