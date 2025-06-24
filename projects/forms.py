from django import forms
from .models import Project, ProjectPicture, Comment, Rating, Donation

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'details', 'category', 
            'tags', 'total_target', 'end_time'
        ]
        widgets = {
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class ProjectPictureForm(forms.ModelForm):
    class Meta:
        model = ProjectPicture
        fields = ['image']

class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Comment
        fields = ['content', 'parent_id']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3})
        }

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['value']

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'min': 10})
        }