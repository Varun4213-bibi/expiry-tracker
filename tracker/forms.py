from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Item, UserProfile, NGOProfile

class ExpiryDateOCRForm(forms.Form):
    image = forms.ImageField(label="Upload Expiry Date Photo")

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'barcode', 'expiry_date', 'notes']  # Add/remove fields as needed
        exclude = ['user']  # User is set automatically in view
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label="First Name")
    last_name = forms.CharField(max_length=30, required=False, label="Last Name")
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = UserProfile
        fields = ['email_reminders_enabled', 'push_reminders_enabled']
        widgets = {
            'email_reminders_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_reminders_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.save()
        if commit:
            profile.save()
        return profile
class NGORegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Username")
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirm Password")
    
    class Meta:
        model = NGOProfile
        fields = ['organization_name', 'contact_person', 'phone', 'address', 'city', 'state', 'pincode', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

    def save(self, commit=True):
        ngo_profile = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['contact_person']
        )
        ngo_profile.user = user
        ngo_profile.is_verified = False  # NGO needs admin verification
        if commit:
            ngo_profile.save()
        return ngo_profile

class NGOLoginForm(forms.Form):
    username = forms.CharField(max_length=150, required=True, label="Username")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Password")

class NGOProfileForm(forms.ModelForm):
    class Meta:
        model = NGOProfile
        fields = ['organization_name', 'contact_person', 'phone', 'address', 'city', 'state', 'pincode', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

        