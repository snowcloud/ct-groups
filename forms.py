from django import forms
from django.db.models import get_model
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.template.defaultfilters import slugify
from wiki.forms import ArticleForm
from ct_groups.models import GroupMembership


from copy import copy

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
		return cleaned_data

# from ct_groups.models import CTPost

CTPost = get_model('ct_groups', 'ctpost')

class BlogPostForm(forms.ModelForm):
	class Meta:
		model = CTPost
		fields = ('title', 'body', 'tease', 'allow_comments', 'status', )

class GroupMembershipForm(forms.ModelForm):
	class Meta:
		model = GroupMembership
		fields = ('post_updates', 'tool_updates', )
