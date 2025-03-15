from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your review here...'}),
            'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),  
        }
# -------------------------------------------------------------------------------------------------------------