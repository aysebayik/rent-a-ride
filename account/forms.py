from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.forms import DateInput

from RAR.models import CarDealer, Branch

User = get_user_model()

USER_TYPES = (
    ('customer', 'Customer'),
    ('car_dealer', 'Car Dealer'),
)


# class RegisterForm(UserCreationForm):
#     first_name = forms.CharField(max_length=100, help_text='First Name')
#     last_name = forms.CharField(max_length=100, help_text='Last Name')
#     email = forms.EmailField(max_length=150, help_text='Email')
#
#     class Meta:
#         model = User
#         fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class CustomerRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, help_text='First Name',widget=forms.TextInput)
    last_name = forms.CharField(max_length=100, help_text='Last Name',widget=forms.TextInput)
    email = forms.EmailField(max_length=150, help_text='Email',widget=forms.EmailInput)
    birthDate = forms.DateField(widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    licenseId = forms.IntegerField()

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class CarDealerRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, help_text='First Name',widget=forms.TextInput)
    last_name = forms.CharField(max_length=100, help_text='Last Name',widget=forms.TextInput)
    email = forms.EmailField(max_length=150, help_text='Email',widget=forms.EmailInput)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class PasswordResetRequestForm(forms.Form):
    email_or_username = forms.CharField(label=("Email Or Username"), max_length=254)


class RoleChooseForm(forms.Form):
    type = forms.ChoiceField(choices=USER_TYPES, help_text='User Type')
