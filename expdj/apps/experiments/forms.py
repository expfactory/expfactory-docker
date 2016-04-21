from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, TabHolder, Tab
from expdj.apps.experiments.models import Experiment, ExperimentTemplate, Battery, \
  CreditCondition
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from django.forms import ModelForm
from django import forms
from glob import glob
import os
from expdj.settings import BASE_DIR

class ExperimentTemplateForm(ModelForm):

    class Meta:
        model = ExperimentTemplate
        fields = ("name","publish","cognitive_atlas_task","reference")

    def clean(self):
        cleaned_data = super(ExperimentTemplateForm, self).clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(ExperimentTemplateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))


class ExperimentForm(ModelForm):

    class Meta:
        model = Experiment
        fields = ("include_bonus","include_catch")

    def clean(self):
        cleaned_data = super(ExperimentForm, self).clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(ExperimentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))


class BatteryForm(ModelForm):

    class Meta:
        exclude = ('owner','contributors','experiments','blacklist','bonus')
        model = Battery

    def clean(self):
        cleaned_data = super(BatteryForm, self).clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(BatteryForm, self).__init__(*args, **kwargs)

        # Dynamically add available credential files
        credential_files = [(os.path.basename(x),os.path.basename(x)) for x in glob("%s/expdj/auth/*.cred" %BASE_DIR)]
        self.fields['credentials'] = forms.ChoiceField(choices=credential_files)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))


class CreditConditionForm(ModelForm):

    class Meta:
        exclude = ('variable',)
        model = CreditCondition

    def clean(self):
        cleaned_data = super(CreditConditionForm, self).clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(CreditConditionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))
