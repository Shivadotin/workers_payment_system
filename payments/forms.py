import re
from django import forms
from .models import BankDetails


class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = BankDetails
        fields = ['account_holder_name', 'account_number', 'ifsc', 'upi_id']

    def clean_account_number(self):
        number = self.cleaned_data['account_number'].strip()
        if not number.isdigit() or not (9 <= len(number) <= 18):
            raise forms.ValidationError("Enter a valid account number (9 to 18 digits).")
        return number

    def clean_ifsc(self):
        ifsc = self.cleaned_data['ifsc'].strip().upper()
        if not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', ifsc):
            raise forms.ValidationError("Enter a valid IFSC code, for example SBIN0001234.")
        return ifsc

    def clean_upi_id(self):
        upi = (self.cleaned_data.get('upi_id') or '').strip()
        if upi and not re.fullmatch(r'[\w.\-]{2,}@[A-Za-z]{2,}', upi):
            raise forms.ValidationError("Enter a valid UPI ID, for example name@upi.")
        return upi or None