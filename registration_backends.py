from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from registration.backends.default import DefaultBackend
from registration.forms import RegistrationForm

attrs_dict = {'class': 'required'}

class CleanUsernameField(forms.RegexField):
    """utility class to strip white space from value before validating"""
    def clean(self, value):
        return super(CleanUsernameField, self).clean(value.strip())

class CleanEmailField(forms.EmailField):
    """utility class to strip white space from value before validating"""
    def clean(self, value):
        return super(CleanEmailField, self).clean(value.strip())

class RegistrationWithName(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds first, last names,
    and replaces username and email with fields which strip whitespace before validating
    
    """
    username = CleanUsernameField(regex=r'^[\S]*$',
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_("Username"),
                                error_messages={ 'invalid': _("This value must contain only letters, numbers and underscores.") })

    email = CleanEmailField(widget=forms.TextInput(attrs=dict({'class': 'required email'},
                                maxlength=75)),
                                label=_("Email address"))
    
    first_name = forms.CharField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                maxlength=75)),
                                label=_(u'first name'))
    last_name = forms.CharField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                maxlength=75)),
                                label=_(u'last name'))
    
    # def clean_email(self):
    #         data = self.cleaned_data['email']
    #         if "fred@example.com" not in data:
    #             raise forms.ValidationError("")
    # 
    #         # Always return the cleaned data, whether you have changed it or
    #         # not.
    #         return data

    def clean(self):
        cleaned_data = self.cleaned_data
        email = cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("This email address is in use. Click \"forgotten user name or password?\" above."))
            
        debug = '%s\n' % self.errors.keys()
        debug += '%s\n' % self.errors.values()
        debug += '%s %s [%s]\n%s\n' % ( self.data['first_name'], self.data['last_name'],
            self.data['username'], self.data['email'], )
        debug += 'http://www.google.co.uk/search?&q=%s\n' % self.data['email']
        debug += 'http://icnp.clinicaltemplates.org/admin/auth/user/?q=%s\n' % self.data['username']
        
        from django.core.mail import send_mail

        send_mail('ICNP registration', debug, 'derek@snowcloud.co.uk',
            ['derek.hoy@gmail.com'], fail_silently=True)
        
        return cleaned_data
        
    
    # def save(self):
    # 
    #     new_user = super(RegistrationWithName, self).save()
    #     if new_user:
    #         new_user.first_name = self.cleaned_data['first_name']
    #         new_user.last_name = self.cleaned_data['last_name']
    #         new_user.save()
    
    def __init__(self, *args, **kwargs):
        """
        modify error message for username to be more informative
        """
        super(RegistrationWithName, self).__init__(*args, **kwargs)
        self.fields['username'].error_messages['invalid']=_("No spaces, please.")
        self.fields['username'].help_text=_('Should be one word, with no spaces or punctuation. For example, jsmith or BJones, but not jean smith, or j-smith.')


class CTRegistrationBackend(DefaultBackend):
    def get_form_class(self, request):
        return RegistrationWithName
        
    def register(self, request, **kwargs):
        new_user = super(CTRegistrationBackend, self).register(request, **kwargs)
        new_user.first_name = kwargs['first_name']
        new_user.last_name = kwargs['last_name']
        new_user.save()
        return new_user
        

