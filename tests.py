from django.core import mail
from django.template.defaultfilters import slugify
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from ct_groups.models import CTGroup, GroupMembership, CTPost, CTEvent, \
	PERM_CHOICE_EDITOR, PERM_CHOICE_GROUP_MEMBER, email_digests
import datetime

def _delay(seconds):
	t = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
	while t > datetime.datetime.now():
		pass

class CTGroupTest(TestCase):

	def _make_group(self, name, is_public=True):
		"""docstring for _make_group"""
		group = CTGroup(
			name = name,
			slug = slugify(name),
			# note = models.TextField(blank=True),
			# tags = TagField(),
			is_public = is_public
		)
		group.save()
		return group
	
	def _make_user(self, username):
		"""docstring for _make_user"""
		user, created = User.objects.get_or_create(
			username=username,
			first_name=username.capitalize(),
			last_name='Hoojie',
			email='%s@ganzie.com' % username
			)
		return user
	
	def _make_membership(self, user, group, is_active=True, is_editor=False, post_updates='single'):
		"""docstring for _make_membership"""
		member = GroupMembership(user=user, group=group)
		member.is_active = is_active
		member.is_editor = is_editor
		member.post_updates = post_updates
		member.save()
		return member

	def setUp(self):
		group1 = self._make_group('Test group one')
		group2 = self._make_group('Test group two')
		group3 = self._make_group('Test group three')
		user = self._make_user('shuggie')
		member = self._make_membership(user, group1, False)
		user = self._make_user('francie')
		member = self._make_membership(user, group2, False)
		user = self._make_user('ella')
		member = self._make_membership(user, group2, True, True)
		member = self._make_membership(user, group3)
		user = self._make_user('josie')
		member = self._make_membership(user, group1, True, True, 'digest')
		member = self._make_membership(user, group2, True, True, 'digest')
		member = self._make_membership(user, group3, True, True, 'digest')
		user = self._make_user('hubert')
		member = self._make_membership(user, group2, True, False, 'digest')
		
	# def tearDown(self):
	# 	pass

	def test_group(self):
		"""
		.
		"""
		site = Site.objects.get_current()
		count = CTGroup.objects.count()
		self.failUnlessEqual(count, 3)
		group1 = CTGroup.objects.get(name='Test group one')
		# group.set_permission('blog', read=PERM_CHOICE_EDITOR)
		user = self._make_user('bernie')
		member = self._make_membership(user, group1)
		post = CTPost(
			ct_group=group1,
			title = 'Post one', 
			slug = slugify('post one'),
			author = user,
			body = "some text's here...",
			publish = datetime.datetime.now()
	    )
		post.save()
		c = Comment(
			content_object=post,
			site= site,
			user = user,
			comment = 'Comment 1...',
			submit_date= datetime.datetime.now()
		)
		c.save()
		_delay(1)
		c = Comment(
			content_object=post,
			site= site,
			user = user,
			comment = 'Comment 2...',
			submit_date= datetime.datetime.now()
		)
		c.save()
		group2 = CTGroup.objects.get(name='Test group two')
		group2.set_permission('blog', read=PERM_CHOICE_EDITOR)
		user = self._make_user('chic')
		member = self._make_membership(user, group2)
		post = CTPost(
			ct_group=group2,
			title = 'Post one', 
			slug = slugify('post one'),
			author = user,
			body = "some text's here...",
			publish = datetime.datetime.now()
	    )
		post.save()
		post.save() # checks not emailed twice
		post = CTPost(
			ct_group=group2,
			title = 'Post two', 
			slug = slugify('post two'),
			author = user,
			body = "some text here for this's draft post...",
			publish = datetime.datetime.now(),
			status = 1
	    )
		post.save()
		self.assertEquals(len(mail.outbox), 4)
		post.status = 2
		post.save()
		self.assertEquals(len(mail.outbox), 5)
		# for m in mail.outbox:
		# 	print
		# 	print m.bcc
		# 	print m.subject
		# 	print m.body
			
		# print mail.outbox[0].bcc
		# print mail.outbox[0].body
		# print mail.outbox[1].bcc
		count = CTEvent.objects.count()
		self.failUnlessEqual(count, 5)
		


	def test_digest(self):
		"""
		.
		"""
		site = Site.objects.get_current()
		group = CTGroup.objects.get(name='Test group two')
		group3 = CTGroup.objects.get(name='Test group three')
		group.set_permission('blog', read=PERM_CHOICE_GROUP_MEMBER)
		user = self._make_user('chic')
		member = self._make_membership(user, group)
		post = CTPost(
			ct_group=group,
			title = 'digest post one', 
			slug = slugify('post one'),
			author = user,
			body = "Some text's here for post 1...",
			publish = datetime.datetime.now()
	    )
		post.save()
		c = Comment(
			content_object=post,
			site= site,
			user = user,
			comment = 'Comment...',
			submit_date= datetime.datetime.now()
		)
		c.save()
		post = CTPost(
			ct_group=group,
			title = 'digest post two', 
			slug = slugify('post two'),
			author = user,
			body = "Some text's here for post 2...",
			publish = datetime.datetime.now()
	    )
		post.save()
		post = CTPost(
			ct_group=group3,
			title = 'digest post one', 
			slug = slugify('post one'),
			author = user,
			body = "Some text's here for post 1...",
			publish = datetime.datetime.now()
	    )
		post.save()
		post = CTPost(
			ct_group=group3,
			title = 'digest post two', 
			slug = slugify('post two'),
			author = user,
			body = "Some text's here for post 2...",
			publish = datetime.datetime.now(),
			notified = True
	    )
		post.save()
		c = Comment(
			content_object=post,
			site= site,
			user = user,
			comment = 'Comment 1...',
			submit_date= datetime.datetime.now()
		)
		c.save()
		_delay(1)
		c = Comment(
			content_object=post,
			site= site,
			user = user,
			comment = 'Comment 2...',
			submit_date= datetime.datetime.now()
		)
		c.save()
		self.assertEquals(len(mail.outbox), 6)
		self.assertEquals(mail.outbox[0].subject, '[example.com] Test group two update')
		self.assertEquals(len(mail.outbox[0].bcc), 2)

		mail.outbox = []
		self.failUnlessEqual(Comment.objects.count(), 3)
		self.failUnlessEqual(CTEvent.objects.count(), 6)
		email_digests()
		self.assertEquals(len(mail.outbox), 2)
		# print
		# print mail.outbox[0].bcc
		# print mail.outbox[0].subject
		# print mail.outbox[0].body
		# print
		# print mail.outbox[1].bcc
		# print mail.outbox[1].subject
		# print mail.outbox[1].body
		
		# events should be cleared
		self.failUnlessEqual(CTEvent.objects.count(), 0)
		
	# def test_get_mapitem(self):
	#	  """
	#	  .
	#	  """
	#	  mapitem = MapItem.objects.get(pk=1)
	#	  self.failUnlessEqual(mapitem.status, "partial")
