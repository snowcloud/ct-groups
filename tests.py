from django.core import mail
from django.template.defaultfilters import slugify
from django.test import TestCase
from django.contrib.auth.models import User
from ct_groups.models import CTGroup, GroupMembership, CTPost
import datetime

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
	
	def _make_membership(self, user, group, is_active=True):
		"""docstring for _make_membership"""
		member = GroupMembership(user=user, group=group)
		member.is_active = is_active
		member.save()
		return member

	def setUp(self):
		group = self._make_group('group one')
		
	# def tearDown(self):
	# 	pass

	def test_group(self):
		"""
		.
		"""
		# print mapping
		group = self._make_group('group two')
		count = CTGroup.objects.count()
		self.failUnlessEqual(count, 2)

		user = self._make_user('francie')
		member = self._make_membership(user, group, False)
		user = self._make_user('josie')
		member = self._make_membership(user, group)
		user = self._make_user('chic')
		member = self._make_membership(user, group)
		post = CTPost(
			ct_group=group,
			title = 'post one', 
			slug = slugify('post one'),
			author = user,
			body = 'some text here...',
			publish = datetime.datetime.now()
	    )
		post.save()
		self.assertEquals(len(mail.outbox), 1)
		self.assertEquals(mail.outbox[0].subject, '[example.com] group two update')
		print mail.outbox[0].bcc
		print mail.outbox[0].body

	def test_group2(self):
		"""
		.
		"""
		print
		group = self._make_group('group threeeeee')
		print group.name
		count = CTGroup.objects.count()
		self.failUnlessEqual(count, 2)
		
	# def test_get_mapitem(self):
	#	  """
	#	  .
	#	  """
	#	  mapitem = MapItem.objects.get(pk=1)
	#	  self.failUnlessEqual(mapitem.status, "partial")
