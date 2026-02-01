from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory

from . import models


class ClassForm(forms.ModelForm):
    class Meta:
        model = models.Class
        fields = ['title', 'term']


class ProblemSetForm(forms.ModelForm):
    class Meta:
        model = models.ProblemSet
        fields = ['title', 'release_at', 'due_at']
        widgets = {
            'release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class ProblemForm(forms.ModelForm):
    class Meta:
        model = models.Problem
        fields = ['title', 'prompt_pdf', 'max_score', 'order']


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    default_error_messages = {
        'required': 'Please select at least one file.',
        'invalid': 'No file was submitted.',
    }

    def to_python(self, data):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return list(data)
        return [data]

    def validate(self, data):
        if self.required and not data:
            raise ValidationError(self.error_messages['required'], code='required')
        for item in data:
            super().validate(item)


class SubmissionForm(forms.Form):
    files = MultipleFileField(
        widget=MultiFileInput(attrs={'multiple': True}),
        required=True,
        help_text='Upload a PDF or one or more images.',
    )


class GradeForm(forms.ModelForm):
    class Meta:
        model = models.Grade
        fields = ['score', 'feedback']


class AppealForm(forms.ModelForm):
    class Meta:
        model = models.Appeal
        fields = ['reason']


class AppealMessageForm(forms.ModelForm):
    class Meta:
        model = models.AppealMessage
        fields = ['message']


class StudentSignUpForm(forms.Form):
    email = forms.EmailField()
    username = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput)


RubricItemFormSet = modelformset_factory(
    models.RubricItem,
    fields=['label', 'points', 'order'],
    extra=1,
    can_delete=True,
)
