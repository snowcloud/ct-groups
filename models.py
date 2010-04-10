""" ctgroup/models.py

"""
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Manager, signals, get_model
from django.conf import settings
from django.template.defaultfilters import truncatewords
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from tagging.fields import TagField
import tagging
import datetime


class CTGroup(models.Model):
	name = models.CharField(max_length=64)
	slug = models.SlugField(_('slug'), unique=True)
	note = models.TextField(blank=True)
	tags = TagField()
	is_public = models.BooleanField(default=True)
	members = models.ManyToManyField(User, through='GroupMembership')
	logo = models.ImageField(upload_to="groups", null=True, blank=True, help_text="60 H x 400 W (max)")
	
	class Admin:
		pass # ordering = ['name']

	class Meta:
		ordering = ['name']

	def __repr__(self):
		return '%s' % (self.name)

	def __unicode__(self):
		return '%s' % (self.name)

	def get_absolute_url(self):
		# return "/groups/%i/" % self.id
		return "/groups/%s/" % self.slug

	def check_default_permissions(self, *args, **kwargs):
		"""docstring for check_default_permissions"""
		defs = { 
			'group': (PERM_CHOICE_PUBLIC, PERM_CHOICE_EDITOR),
			'wiki': (PERM_CHOICE_PUBLIC, PERM_CHOICE_EDITOR),
			'blog': (PERM_CHOICE_PUBLIC, PERM_CHOICE_EDITOR),
			'comment': (PERM_CHOICE_PUBLIC, PERM_CHOICE_REG_USER),
			'resource': (PERM_CHOICE_GROUP_MEMBER, PERM_CHOICE_EDITOR),
			}
		perms = dict([(p.name, p) for p in self.ctgrouppermission_set.all()])
		for name, p in defs.iteritems():
			if name not in perms:
				new_p = CTGroupPermission(
					name = name,
					read_permission = p[0],
					write_permission = p[1],
					group = self
					)
				new_p.save()
				
			# print name, p
		# print perms
		# if not self.class_code:
		#	  self.class_code = self.id
		#	  super(SMGClass, self).save(*args, **kwargs)
		
	
	def save(self, *args, **kwargs):
		super(CTGroup, self).save(*args, **kwargs)
		self.check_default_permissions(*args, **kwargs)
	
	def get_member(self, user):
		members = [gm for gm in self.groupmembership_set.all() if gm.user.id == user.id]
		if len(members) > 0:
			return members[0]
		else:
			return None

	def has_member(self, user):
		members = [gm.user for gm in self.groupmembership_set.all()]
		return user in members

	def has_manager(self, user):
		u = self.get_member(user)
		if u is None:
			return False
		else:
			return u.is_manager

# this is buggy- corrupting fields in admin
# tagging.register(CTGroup)


PERM_CHOICES = (
	('50', 'staff member'),
	('45', 'group manager'),
	('40', 'editor'),
	('30', 'group member'),
	('20', 'registered user'),
	('10', 'public'),
	)
PERM_CHOICE_STAFF = '50'
PERM_CHOICE_MANAGER = '45'
PERM_CHOICE_EDITOR = '40'
PERM_CHOICE_GROUP_MEMBER = '30'
PERM_CHOICE_REG_USER = '20'
PERM_CHOICE_PUBLIC ='10'

class CTGroupPermission(models.Model):
	name = models.CharField(max_length=64)
	read_permission = models.CharField(max_length=3, choices=PERM_CHOICES, default=PERM_CHOICE_REG_USER)
	write_permission = models.CharField(max_length=3, choices=PERM_CHOICES, default=PERM_CHOICE_STAFF)
	group = models.ForeignKey(CTGroup)

	class Admin:
		pass

	def check_permission(self, user, type):
		if self.name == 'group' and type == 'r' and self.group.is_public:
			return True
		level = 10
		if user.is_authenticated():
			if user.is_staff:
				level = 50
			else:
				memb = self.group.get_member(user)
				if memb and memb.is_active:
					if memb.is_manager:
						level = 45
					elif memb.is_editor:
						level = 40
					else:
						level = 30
				else:
					level = 20
		# print level
		if (not self.group.is_public) and (level < 30):
			# private group gives access only to members or better
			return False
		if type == 'w':
			return level >= int(self.write_permission)
		elif type == 'r':
			return level >= int(self.read_permission)
		return False

# def POST_UPDATE_CHOICES():
# 	return (('none', _('no updates')), ('single', _('single emails')), ('digest', _('daily digest')))
POST_UPDATE_CHOICES= (('none', _('No updates')), ('single', _('Single emails')), ('digest', _('Daily digest')))
TOOL_UPDATE_CHOICES = POST_UPDATE_CHOICES
POST_UPDATE_CHOICES_DEFAULT = TOOL_UPDATE_CHOICES_DEFAULT = 'single'
MODERATION_CHOICES = (('none', 'None'), ('pending', 'Pending'), ('refused', 'Refused'), )
MODERATION_CHOICES_DEFAULT = 'none'

class GroupMembership(models.Model):
	#name = models.CharField(max_length=64, core=True)
	note = models.CharField(max_length=64, blank=True)
	is_active = models.BooleanField('active', blank=False, default=1)
	is_manager = models.BooleanField('manager', blank=True)
	# is_champion = models.BooleanField('editor', blank=True)
	is_editor = models.BooleanField('editor', blank=True)
	user = models.ForeignKey(User)
	group = models.ForeignKey(CTGroup)
	# notify_updates = models.BooleanField('email updates', default=1)
	notify_post_updates = models.BooleanField('email discussion alerts', default=1)
	notify_tool_updates = models.BooleanField('email tool comments', default=1)
	post_updates = models.CharField(_('email discussion alerts') ,max_length=8, choices=POST_UPDATE_CHOICES, default=POST_UPDATE_CHOICES_DEFAULT)
	tool_updates = models.CharField(_('email tool comments'), max_length=8, choices=TOOL_UPDATE_CHOICES, default=TOOL_UPDATE_CHOICES_DEFAULT)
	moderation = models.CharField(max_length=8, choices=MODERATION_CHOICES, default=MODERATION_CHOICES_DEFAULT)

	# need these strings stable across translation to allow matching
	EDITORS = 'Editors'
	MANAGERS = 'Managers'
	MEMBERS = 'Members'
	NOT_ACTIVE = 'Not currently active'
	# dummy lets makemessages find these for translation files
	dummy = (_('Editors'), _('Managers'), _('Members'), _('Not currently active') )
	
	class Admin:
		pass

	def __repr__(self):
		return '%s - %s' % (self.user.username, self.group.name)
	
	def __unicode__(self):
		return '%s - %s' % (self.user.username, self.group.name)
	
	def _get_member_type(self):
		if self.is_editor: return self.EDITORS
		if self.is_manager: return self.MANAGERS
		if self.is_active: return self.MEMBERS
		else: return self.NOT_ACTIVE
	member_type = property(_get_member_type)

	def _get_group_name(self):
		return self.group.name
	group_name = property(_get_group_name)

	def _get_user_last_name(self):
		return self.user.last_name
	user_last_name = property(_get_user_last_name)

# from basic.blog.models import Post
Post = get_model('blog', 'post')

class PublicManager(Manager):
	"""Returns published posts that are not in the future."""
	
	def published(self):
		return self.get_query_set().filter(status__gte=2, publish__lte=datetime.datetime.now())

	def public(self):
		return self.published().filter(
			ct_group__is_public=True).filter(
			ct_group__ctgrouppermission__name__exact='blog',
			ct_group__ctgrouppermission__read_permission__exact='10')

class CTPost(Post):
	ct_group = models.ForeignKey(CTGroup, blank=True, null=True)
	objects = PublicManager()
	
	class Admin:
		pass

	def _summary(self):	   
		if self.tease:
			return self.tease
		else:
			return truncatewords(self.body, 80)
	summary = property(_summary)
	
def email_post(sender, instance, **kwargs):
	"""docstring for email_post"""
	if kwargs.get('created', False):
		if instance.publish and instance.publish <= datetime.datetime.now():
			group = instance.ct_group
			if group:
				content = render_to_string('ct_groups/email_post_comment_content.txt', {
					'line_1': 'A discussion post has been added to %s.' % group.name,
					'line_2': '',
					'author': instance.author.get_full_name(), 
					'review_date': instance.publish.strftime("%d/%m/%Y, %H.%M"),
					'comment': instance.summary,
					'url': '%s%s' % ( settings.APP_BASE[:-1], instance.get_absolute_url())
				})			  
				_email_notify(group, content, 'notify_post_updates')
		
def email_comment(sender, instance, **kwargs):
	import string
	# TODO: need a more generic mechanism
	# either do with django-notification (needs notices set up for each group member)
	# or do something where object can be queried for notifiable content
	# then check for user membership settings for this group and permissions
	
	if kwargs.get('created', False):
		if (instance.content_type.model == 'ctpost'):
			post = instance.content_object
			if post:
				group = post.ct_group
				if group:
					content = render_to_string('ct_groups/email_post_comment_content.txt', {
						'line_1': 'A comment has been added to %s.' % group.name,
						'line_2': '',
						'author': instance.user.get_full_name(), 
						'review_date': instance.submit_date.strftime("%d/%m/%Y, %H.%M"),
						'comment': instance.comment,
						'url': '%s%s#comments' % ( settings.APP_BASE[:-1], post.get_absolute_url()) 
					})			  
					_email_notify(group, content, 'notify_post_updates')
		elif (instance.content_type.model == 'mapitem'):
			mapitem = instance.content_object
			if mapitem:
				group = mapitem.section.mapping.group
				if group:
					content = render_to_string('ct_groups/email_post_comment_content.txt', {
						'line_1': 'A comment has been added to %s.\n%s' % (group.name, mapitem),
						'line_2': '',
						'author': instance.user.get_full_name(), 
						'review_date': instance.submit_date.strftime("%d/%m/%Y, %H.%M"),
						'comment': instance.comment,
						'url': '%s%s#comments' % ( settings.APP_BASE[:-1], mapitem.get_absolute_url()) 
					})			  
					_email_notify(group, content, 'notify_tool_updates')

def _email_notify(group, content, update_func):
	import string
	import datetime
	from django.core.mail import EmailMessage

	members = group.groupmembership_set.all()
	add_list = list(member.user.email for member in members if getattr(member, update_func) and member.is_active)
	# print add_list
	if len(add_list) == 0:
		return
	site = Site.objects.get_current().name
	body = render_to_string('ct_groups/email_post_comment_body.txt',
		{ 'content': content, 'site': site, 'dummy': datetime.datetime.now().strftime("%H:%M"),
			'settings_url': '%s%s' % ( settings.APP_BASE[:-1], reverse('group-edit', kwargs={'group_slug': group.slug}))})
	body = body.replace("&#39;", "'")
	body = body.replace("&gt;", "")
	email = EmailMessage(
		#subject, body, from_email, to, bcc, connection)
		'[%s] %s update' % (site, group.name), 
		body, 
		'do not reply <do_not_reply@clintemplate.org>',
		['do_not_reply@clintemplate.org'],
		add_list )
	email.send()

signals.post_save.connect(email_comment, sender=Comment)
signals.post_save.connect(email_post, sender=CTPost)
