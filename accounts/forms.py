from django import forms
from .models import User


class SuperwiserCreatinForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput )

    confirm_password = forms.CharField( widget=forms.PasswordInput)

    class Meta:
        model = User

        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'password',
            'confirm_password',
        ]
    def clean(self):
    
            cleaned_data = super().clean()
    
            password = cleaned_data.get("password")
            confirm_password = cleaned_data.get("confirm_password")
    
            if password and confirm_password and password != confirm_password:
                raise forms.ValidationError("Passwords do not match." )
    
            return cleaned_data

class WorkerCreationForm(forms.ModelForm):
    password = forms.CharField( widget = forms.PasswordInput)
    confirm_password = forms.CharField(widget = forms.PasswordInput)

    class Meta:
        model = User

        fields = [
            'username' ,
            'first_name',
            'last_name' ,
            'email',
            'phone_number' ,
            'password',
            'confirm_password',

        ]
    def clean(self):
                
            cleaned_data = super().clean()
            password = cleaned_data.get("password")
            confirm_password = cleaned_data.get("confirm_password")
            if password != confirm_password:
                raise forms.ValidationError( "Passwords do not match." )
    
            return cleaned_data


class WorkerUpdateForm(forms.ModelForm):
    class Meta:
        model = User

        fields = [
            'first_name' ,
            'last_name' ,
            'email' ,
            'phone_number',
        ]

        