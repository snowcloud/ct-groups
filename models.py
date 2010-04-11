""" ctgroup/models.py

"""
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
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
import string
import os


class CTGroup(models.Model):
	name = models.CharField(max_length=64)
	slug = models.SlugField(_('slug'), unique=True)
	note = models.TextField(blank=True)
	tags = TagField()
	is_public = models.BooleanField(default=True)
	# moderate_membership = models.BooleanField(default=False)
	# show_join_link = models.BooleanField(default=True)
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
						
	def get_permission(self, perm_type):
		"""docstring for get_permission"""
		try:
			perm = CTGroupPermission.objects.get(group=self, name=perm_type)
			return perm
		except CTGroupPermission.DoesNotExist:
			return None

	def set_permission(self, perm_type, read=None, write=None):
		"""docstring for set_permission"""
		perm, created = CTGroupPermission.objects.get_or_create(group=self, name=perm_type)
		if read:
			perm.read_permission = read
		if write:
			perm.write_permission = write
		perm.save()
	
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

	def email_digests(self):
		"""docstring for email_digests"""
		# leave here - recursive load problem
		from ct_groups.decorators import check_permission
		
		fname = '%s/email-digest-%s.txt' % (settings.TMP_PATH, self.slug)
		if os.path.exists(fname):
			digest_file = open(fname, 'r')
		
			# add file contents to body
			body = ''.join(digest_file.readlines())
			# print body
			# print ''.join(body)
		
			digest_file.close()
			os.remove(fname)
		
			# now get comments from last 24 hours
			# add to body
		
			# IF GOING TO USE PERMISSIONS TO SEND POST COMMENTS, 
			# NEED SEP DIGESTS FOR POST COMMENTS, TOOL COMMENTS
		
			# get members with digest option
			# make email
			# send email
			members = self.groupmembership_set.all()
			rec_list = list(member.user.email for member in members if (getattr(member, 'post_updates') == 'digest') and 
				member.is_active and 
				check_permission(member.user, self, 'blog', 'r'))
			if rec_list:
				email = EmailMessage(
					#subject, body, from_email, to, bcc, connection)
					'[%s] %s updates (daily digest)' % (Site.objects.get_current().name, self.name), 
					body, 
					'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
					[settings.DEFAULT_FROM_EMAIL],
					rec_list )
				email.send()
		
		
		
		
		###############################################################
		
		# print self.name
		# make datetimes for midnight, mn - 24 hours
		# exclude lte prev mn, gt mn
		# or should be all not notified but published ???
		
		# NOTIFY DOESN'T WORK COS SET BY SINGLE EMAIL
		
		# posts = [post.notified for post in self.ctpost_set.published().filter(ct_group=self)]
		# print posts
		# today = datetime.datetime.now()
		# day_start = datetime.datetime(today.year, today.month, today.day)
		# day_end = day_start - datetime.timedelta(days=1)
		# print today, day_start, day_end
		
		# datetime.year
		# Between MINYEAR and MAXYEAR inclusive.
		# datetime.month
		# Between 1 and 12 inclusive.
		# datetime.day
		# Between 1 and the number of days in the given month of the given year.
		# datetime.hour
		# In range(24).
		# datetime.minute
		# In range(60).
		# datetime.second

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
	notified = models.BooleanField(default=False)
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
	if not instance.notified:
		if instance.status > 1 and instance.publish and instance.publish <= datetime.datetime.now():
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
				email = _email_notify(group, content, 'post_updates', 'blog')
				add_to_digest(group, email)
				
			instance.notified = True
			instance.save()
		
def email_comment(sender, instance, **kwargs):
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
					email = _email_notify(group, content, 'post_updates', 'comment')
					add_to_digest(group, email)
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
					email = _email_notify(group, content, 'tool_updates', 'resource')
					add_to_digest(group, email)
					

def _email_notify(group, content, update_func, perm):
	# leave here - recursive load problem
	from ct_groups.decorators import check_permission
	
	members = group.groupmembership_set.all()
	add_list = list(member.user.email for member in members if (getattr(member, update_func) == 'single') and 
		member.is_active and 
		check_permission(member.user, group, perm, 'r'))
	
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
		'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
		[settings.DEFAULT_FROM_EMAIL],
		add_list )
	email.send()
	# add_to_digest(group, email)
	return email

def	add_to_digest(group, email):
	"""
	docstring for 	add_to_digest(group, email)
	"""
	# print group.name
	# print email.subject
	# print email.body
	sep = '***********************************************************\n'
	path = settings.TMP_PATH
	outfile = open('%s/email-digest-%s.txt' % (path, group.slug), 'a')
	outfile.write(email.subject + '\n')
	outfile.write(email.body)
	outfile.write(sep)
	outfile.close()
	

signals.post_save.connect(email_comment, sender=Comment)
signals.post_save.connect(email_post, sender=CTPost)
