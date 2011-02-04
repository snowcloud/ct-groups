from copy import copy

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import get_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from wiki.forms import ArticleForm
from wiki.models import Article
from scutils.models import smart_caps
from scutils.forms import SCContactForm

from ct_groups.models import CTGroup, GroupMembership, Invitation, is_email_in_use
from ct_groups.templatetags.ct_groups_tags import contact_managers

# class UniqueEmailField(forms.EmailField):
#     """utility class to strip white space from value before validating"""
#     def clean(self, value):
#         if True:
#             raise forms.ValidationError(_("This email address is being used by another user account."))
#         return super(CleanEmailField, self).clean(value.strip())

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    # first_name = forms.CharField(max_length=30)
    # last_name = forms.CharField(max_length=30)
    # email = UniqueEmailField()
    # note = CharField(widget=Textarea(attrs={'rows': 6, 'cols': 40, 'class': 't_area'}), required=False) 

    def clean(self):
        if self.cleaned_data.has_key('first_name'):
            self.cleaned_data['first_name'] = smart_caps(self.cleaned_data['first_name'])
        if self.cleaned_data.has_key('last_name'):
            self.cleaned_data['last_name'] = smart_caps(self.cleaned_data['last_name'])
        if is_email_in_use(self.instance, self.cleaned_data['email']):
            raise forms.ValidationError(_("This email address is being used by another user account."))
        
        return self.cleaned_data

class CTPageForm(ArticleForm):
    summary = forms.CharField(label=_('Title'), max_length=46)
    comment = forms.CharField(widget=forms.HiddenInput, required=False)
    title = forms.CharField(widget=forms.HiddenInput)
    markup = forms.CharField(widget=forms.HiddenInput, initial='txl')

    def __init__(self, *args, **kwargs):
        """
        reorder fields from snippet: http://www.djangosnippets.org/snippets/759/
        """
        super(ArticleForm, self).__init__(*args, **kwargs)

        order = ('summary', 'content', 'title', 'tags', 
            'comment', 'user_ip', 'content_type', 'object_id', 'action', 'markup', )
        tmp = copy(self.fields)
        self.fields = SortedDict()
        for item in order:
            self.fields[item] = tmp[item]
        self.fields['tags'].label = _('Topics')

    def clean_title(self):
        """ override default which insists on wikiword
        """
        title = self.cleaned_data['title']
        return title
    
    def clean(self):
        
        cleaned_data = self.cleaned_data
        summary = cleaned_data.get("summary")
        object_id = cleaned_data.get("object_id")
        
        if summary and object_id:
            title = '%s-%s' % (slugify(summary), object_id)
            cleaned_data['title'] = title
            
        # page_id = self.cleaned_data['summary']
        
        if cleaned_data['action'] == 'create':
            if Article.objects.filter(title=title).exists():
                raise forms.ValidationError(_("This page already exists."))
        return cleaned_data

# from ct_groups.models import CTPost

CTPost = get_model('ct_groups', 'ctpost')

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = CTPost
        fields = ('title', 'body', 'tease', 'allow_comments', 'status', )

class GroupJoinForm(forms.Form):
    reason_for_joining = forms.CharField(label=_('Reason for joining'), required=False, widget=forms.Textarea)

class GroupMembershipForm(forms.ModelForm):
    class Meta:
        model = GroupMembership
        fields = ('post_updates', 'tool_updates', )

class ModerateRefuseForm(forms.Form):
    reason_for_refusal = forms.CharField(label=_('Reason for refusing group membership'), 
        help_text=_('Will be included in email to person being refused'), required=False, widget=forms.Textarea)

class InviteMemberForm(forms.Form):
    group = forms.IntegerField(widget=forms.HiddenInput, required=True)
    email = forms.EmailField(label=_('Email'))

    def clean_email(self):
        """ override default which insists on wikiword
        """
        email = self.cleaned_data['email']
        group = self.cleaned_data['group']
        # TODO include group for check for existing
        # TODO inform if already a member
        # maybe put check in groups.models as helper function

        if GroupMembership.objects.filter(group__id=group,user__email=email):
            raise forms.ValidationError(_('This person is already a group member'))
        if Invitation.objects.filter(group__id=group,email=email):
            raise forms.ValidationError(_('There is already an invitation for that email address'))

        return email

class CTGroupManagersContactForm(SCContactForm):
    """Contact form for use in CTGroup, contact email sent to group managers, or if none, to admins
    """
    recipient_list = []
    subject_template_name = "ct_groups/group_contact_form_subject.txt"
    # template_name = 'contact_form/contact_form.txt'
        
    def clean(self):
        cleaned_data = self.cleaned_data
        group = get_object_or_404(CTGroup, slug=self.request.POST.get('group', None))
        if not contact_managers(group, self.request.user):
            raise PermissionDenied()
        self.recipient_list = [m.user.email for m in group.get_managers()] or \
            [mail_tuple[1] for mail_tuple in settings.MANAGERS]
        cleaned_data['group'] = group
        return cleaned_data
