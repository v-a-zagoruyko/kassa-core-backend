from django import forms

from .models import Store
from .widgets import AddressDadataWidget


class StoreAdminForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].widget = AddressDadataWidget()
        self.fields["address"].required = True
