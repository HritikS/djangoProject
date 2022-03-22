from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile

from ads.humanize import naturalsize
from ads.models import Ad


class CreateForm(forms.ModelForm):
    max_upload_limit = 2 * 1024 * 1024
    max_upload_limit_text = naturalsize(max_upload_limit)

    picture = forms.ImageField(required=False, label='File to Upload <= '+max_upload_limit_text)

    class Meta:
        model = Ad
        fields = ['title', 'price', 'text', 'picture']

    def clean(self):
        cleaned_data = super().clean()
        pic = cleaned_data.get('picture')
        if not pic:
            return
        if len(pic) > self.max_upload_limit:
            self.add_error('picture', "File must be < "+self.max_upload_limit_text+" bytes")

    def save(self, commit=True):
        instance = super(CreateForm, self).save(commit=False)
        f = instance.picture

        if isinstance(f, InMemoryUploadedFile):
            bytearr = f.read()
            instance.content_type = f.content_type
            instance.picture = bytearr

        if commit:
            instance.save()

        return instance


class CommentForm(forms.Form):
    comment = forms.CharField(required=True, max_length=256, min_length=3, strip=True)
