from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["street", "city", "state", "pin_code", "country", "phone", "is_default"]
