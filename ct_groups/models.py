""" ctgroup/models.py

"""
# import re
import datetime
import os
import random
import string
import tagging

from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Manager, get_model, signals
from django.conf import settings
from django.template.defaultfilters import truncatewords
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _
from tagging.fields import TagField

# SHA1_RE = re.compile('^[a-f0-9]{40}$')

GROUP_MODERATE_OPTIONS = (('open', 'open'), ('mod', 'moderated'), ('closed', 'closed'))
RESOURCE_COMMENT_OLDEST_FIRST = 'oldest_top'
RESOURCE_COMMENT_NEWEST_FIRST = 'newest_top'
RESOURCE_COMMENT_ORDER = ((RESOURCE_COMMENT_NEWEST_FIRST, _('newest first')), (RESOURCE_COMMENT_OLDEST_FIRST, _('oldest first')))
RESOURCE_COMMENT_ORDER_DEFAULT = RESOURCE_COMMENT_ORDER[1][1]

def fix_email_body(body):
    """docstring for fix_email_body"""
    result = body.replace("&amp;", "&")
    result = result.replace("&#39;", "'")
    result = result.replace("&gt;", "")
    # this has no effect on email, gets replaced in mailer?
    # result = result.replace("=3D", "=")
    return result

class DuplicateEmailException(Exception):
    pass
     
class CTGroup(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(_('slug'), unique=True)
    note = models.TextField(blank=True)
    tags = TagField()
    is_public = models.BooleanField(default=True)
    moderate_membership = models.CharField(max_length=8, choices=GROUP_MODERATE_OPTIONS, default='closed')
    moderated_message = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=8, choices=settings.LANGUAGES, blank=True, null=True)
    resource_comment_order = models.CharField(max_length=12, choices=RESOURCE_COMMENT_ORDER,
        default=getattr(settings, 'RESOURCE_COMMENT_ORDER', RESOURCE_COMMENT_ORDER_DEFAULT), )
    
    members = models.ManyToManyField(User, through='GroupMembership')
    logo = models.ImageField(upload_to="groups", null=True, blank=True, help_text="60 H x 400 W (max)")
    
    class Admin:
        pass # ordering = ['name']

    class Meta:
        ordering = ['name']

    def __repr__(self):
        return '%s' % (self.name)

    def __unicode__(self):
        return u'%s' % (self.name)

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
            # only write perm is used for contact
            'contact_managers':  (PERM_CHOICE_GROUP_MEMBER, PERM_CHOICE_GROUP_MEMBER),
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

    def get_ct_group(self):
        """provides a common interface across ct models"""
        return self
    group = property(get_ct_group)
                        
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
    
    def get_active_members(self):
        return self.groupmembership_set.filter(is_active=True, status=STATUS_CHOICES_DEFAULT)
        
    def get_member(self, user, all=False):
        # TODO use a filter on set
        # TODO don't include pending/refused moderations
        if all:
            members = self.groupmembership_set.filter(user__id=user.id)
        else:
            members = self.get_active_members().filter(user__id=user.id)
        if len(members) > 0:
            # result = members[0]
            # if not (result.moderation and result.moderation != 'approved'):
            return members[0]
        return None

    def has_member(self, user, all=False):
        return self.get_member(user, all) is not None

    def has_manager(self, user):
        u = self.get_member(user)
        if u is None:
            return False
        else:
            return u.is_manager
            
    def get_managers(self):
        return self.groupmembership_set.filter(
            is_active=True,
            status=STATUS_CHOICES_DEFAULT,
            is_manager=True)
        
    def show_join_link(self):
        return not self.is_closed

    def get_is_closed(self):
        """provides a common interface across ct models"""
        return self.moderate_membership == 'closed'
    is_closed = property(get_is_closed)

    def _resource_comment_reversed(self):
        """docstring for is_resource_comment_newfirst"""
        return self.resource_comment_order != RESOURCE_COMMENT_OLDEST_FIRST
    resource_comment_reversed = property(_resource_comment_reversed)
    
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
NON_GROUP_PERMS = { 'blog': ('r',) }

class CTGroupPermission(models.Model):
    name = models.CharField(max_length=64)
    read_permission = models.CharField(max_length=3, choices=PERM_CHOICES, default=PERM_CHOICE_REG_USER)
    write_permission = models.CharField(max_length=3, choices=PERM_CHOICES, default=PERM_CHOICE_STAFF)
    delete_permission = models.CharField(max_length=3, choices=PERM_CHOICES, default=PERM_CHOICE_STAFF)
    group = models.ForeignKey(CTGroup)

    class Admin:
        pass

    def __unicode__(self):
        """docstring for __unicode__"""
        return u"CTGroupPermission: %s for %s" % (self.name, self.group)
        
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
        if (not self.group.is_public) and (level < 30):
            # private group gives access only to members or better
            return False
        if type == 'w':
            return level >= int(self.write_permission)
        elif type == 'r':
            return level >= int(self.read_permission)
        elif type == 'd':
            return level >= int(self.delete_permission)
        return False

MODERATION_CHOICES = (('pending', _('Pending')), ('accepted', _('Accepted')), ('refused', _('Refused')), )
MODERATION_CHOICES_DEFAULT = 'pending'

class Moderation(models.Model):
    """docstring for Moderation"""
    date_requested = models.DateTimeField(default=datetime.datetime.now)
    status = models.CharField(max_length=8, choices=MODERATION_CHOICES, default=MODERATION_CHOICES_DEFAULT)
    moderator = models.ForeignKey(User, null=True, blank=True, verbose_name=_('Group manager'))
    moderation_date = models.DateTimeField(null=True, blank=True)
    applicants_text = models.TextField(_('Reason for joining group'), null=True, blank=True)
    response_text = models.TextField(_('Group manager\'s reply'), null=True, blank=True)
    
    
    class Admin:
        pass
    
    def __str__(self):
        try:
            return '%s group: %s - %s' % (self.groupmembership.group.name, self.groupmembership.user.get_full_name(), self.status)
        except:
            return 'groupmembership not found'

    def __unicode__(self):
        try:
            return u'%s group: %s - %s' % (self.groupmembership.group.name, self.groupmembership.user.get_full_name(), self.status)
        except:
            return u'groupmembership not found'


    def save(self, *args, **kwargs):
        if self.id:
            memb = self.groupmembership
            memb.status = self.status
            memb.save()
        super(Moderation, self).save(*args, **kwargs)

    def _get_group(self):
        return self.groupmembership.group
    group = property(_get_group)

    def get_notify_content(self, comment=None):
        """docstring for get_notify_content"""
        content = render_to_string('ct_groups/email_post_comment_content.txt', {
            'line_1': _('Request to join group: %s.') % self.group.name,
            'line_2': '',
            'author': self.groupmembership.user.get_full_name(), 
            'review_date': self.date_requested.strftime("%d/%m/%Y, %H.%M"),
            'content': self.applicants_text,
            'url': '%s%s' % ( settings.APP_BASE[:-1], reverse('group-edit', kwargs={'group_slug': self.groupmembership.group.slug}))
        })    
        return (True, content)


POST_UPDATE_CHOICES= (('none', _('No updates')), ('single', _('Single emails')), ('digest', _('Daily digest')))
TOOL_UPDATE_CHOICES = POST_UPDATE_CHOICES
POST_UPDATE_CHOICES_DEFAULT = TOOL_UPDATE_CHOICES_DEFAULT = 'single'
STATUS_CHOICES_DEFAULT = 'accepted'
NOTIFY_ATTRS = { 'blog': 'post_updates', 'resource': 'tool_updates'}

class GroupMembership(models.Model):
    note = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField('active', blank=False, default=1)
    is_manager = models.BooleanField('manager', blank=True)
    is_editor = models.BooleanField('editor', blank=True)
    user = models.ForeignKey(User)
    group = models.ForeignKey(CTGroup)
    post_updates = models.CharField(_('Email discussion alerts'), max_length=8,
        choices=POST_UPDATE_CHOICES, default=POST_UPDATE_CHOICES_DEFAULT)
    tool_updates = models.CharField(_('Email tool comments'), max_length=8,
        choices=TOOL_UPDATE_CHOICES, default=TOOL_UPDATE_CHOICES_DEFAULT)
    moderation = models.OneToOneField(Moderation, null=True, blank=True)
    status = models.CharField(max_length=8, choices=MODERATION_CHOICES, default=STATUS_CHOICES_DEFAULT)
    
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
        return u'%s - %s' % (self.user.username, self.group.name)

    def save(self, *args, **kwargs):
        if self.moderation:
            self.status = self.moderation.status
        else:
            self.status = STATUS_CHOICES_DEFAULT
        super(GroupMembership, self).save(*args, **kwargs)
    
    def remove(self):
        # TODO: translations via ugettext being put in as proxy not string- needs translated up front
        body = '%s.\n\n' % 'Your membership of this group has been removed'
        email = EmailMessage(
            #subject, body, from_email, to, bcc, connection)
            '[%s] %s membership' % (Site.objects.get_current().name, self.group.name), 
            body, 
            'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
            [self.user.email ],
            )
        email.send()
        self.delete()
        
    def delete(self, *args, **kwargs):
        if self.moderation:
            self.moderation.delete()
        super(GroupMembership, self).delete(*args, **kwargs)

    def _get_member_type(self):
        if self.is_manager: return self.MANAGERS
        if self.is_editor: return self.EDITORS
        if self.is_active: return self.MEMBERS
        else: return self.NOT_ACTIVE
    member_type = property(_get_member_type)

    def _get_group_name(self):
        return self.group.name
    group_name = property(_get_group_name)

    def _get_user_last_name(self):
        return self.user.last_name
    user_last_name = property(_get_user_last_name)

    def notify_pref(self, perm):
        return getattr(self, NOTIFY_ATTRS[perm])

    def approve(self):
        """docstring for approve"""
        if self.moderation:
            self.moderation.delete()
            self.moderation = None
        self.status = 'accepted'
        self.save()
        body = '%s\n %s%s' % \
            ('Your request to join this group has been approved.\n\nVisit the group here:',
                settings.APP_BASE[:-1], reverse('group', kwargs={'group_slug': self.group.slug}))
        email = EmailMessage(
            #subject, body, from_email, to, bcc, connection)
            '[%s] %s update' % (Site.objects.get_current().name, self.group.name), 
            body, 
            'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
            [self.user.email ],
            )
        email.send()
        
    def refuse(self, reason_for_refusal):
        """docstring for refuse"""
        self.moderation.status = 'refused'
        self.moderation.response_text = reason_for_refusal
        self.moderation.save()
        # self.status = 'refused'
        self.save()
        body = '%s.\n\n %s' % \
            ('Your request to join this group has not been approved',
                self.moderation.response_text)
        email = EmailMessage(
            #subject, body, from_email, to, bcc, connection)
            '[%s] %s update' % (Site.objects.get_current().name, self.group.name), 
            body, 
            'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
            [self.user.email ],
            )
        email.send()

INVITATION_STATUS_CHOICES= (('to_send', 'To send'), ('sent', _('Sent')), ('failed', _('Email failed')), ('accepted', _('Accepted')))
INVITATION_STATUS_CHOICES_DEFAULT = 'to_send'

class Invitation(models.Model):
    """docstring for Invitation"""
    group = models.ForeignKey(CTGroup)
    sent = models.DateTimeField(default=datetime.datetime.now)
    inviter = models.ForeignKey(User, related_name='inviter')
    email = models.EmailField()
    accepted_by = models.ForeignKey(User, null=True, blank=True, related_name='accepted_by')
    status = models.CharField(max_length=8,
        choices=INVITATION_STATUS_CHOICES, default=INVITATION_STATUS_CHOICES_DEFAULT)
    accept_key = models.CharField(_('accept key'), help_text=_('DO NOT EDIT'), max_length=44, null=True, blank=True, unique=True)
    
    class Meta:
        unique_together = (("group", "email"),)
        
    class Admin:
        pass
    
    def save(self, *args, **kwargs):
        """docstring for save"""
        super(Invitation, self).save(*args, **kwargs)
        if not self.accept_key:
            self.accept_key = '%s%06d' % (make_hash(self.email), self.id)
            self.save()

    def send(self):
        """docstring for send"""
        if self.accept_key:
            body = '%s\n %s%s' % \
                ('%s has invited you to join the %s group.\n\nTo accept the invitation, click this link:' %
                    (self.inviter.get_full_name(), self.group.name),
                    settings.APP_BASE[:-1], reverse('accept-invitation', kwargs={'group_slug': self.group.slug, 'key': self.accept_key}))
            email = EmailMessage(
                #subject, body, from_email, to, bcc, connection)
                '[%s] %s update' % (Site.objects.get_current().name, self.group.name), 
                body, 
                'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
                [self.email ],
                )
            email.send()
            self.status = 'sent'
            self.save()
        else:
            raise Exception('Invitation has no key')

    def accept(self, user):
        """docstring for accept"""
        self.status = 'accepted'
        self.accepted_by = user
        self.save()
    
    def get_is_accepted(self):
        """docstring for is_accepted"""
        return self.status == 'accepted'
    is_accepted = property(get_is_accepted)
    
def make_hash(key, size=12):
    """docstring for make_hash"""
    salt = sha_constructor(str(random.random())).hexdigest()[:5]
    if isinstance(key, unicode):
        key = key.encode('utf-8')
    return sha_constructor(salt+key).hexdigest()[:size]
    
# from basic.blog.models import Post
# # Post = get_model('blog', 'post')
# 
# class PublicManager(Manager):
#     """Returns published posts that are not in the future."""
#     
#     def published(self):
#         return self.get_query_set().filter(status__gte=2, publish__lte=datetime.datetime.now())
# 
#     def public(self):
#         return self.published().filter(
#             ct_group__is_public=True).filter(
#             ct_group__ctgrouppermission__name__exact='blog',
#             ct_group__ctgrouppermission__read_permission__exact='10')

# class CTPost(Post):
#     ct_group = models.ForeignKey(CTGroup, blank=True, null=True)
#     notified = models.BooleanField(default=False)
#     objects = PublicManager()
#     
#     def save(self, *args, **kwargs):
#         super(CTPost, self).save(*args, **kwargs)
#         if not self.notified:
#             if self.status > 1 and self.publish and self.publish <= datetime.datetime.now():
#                 if self.ct_group:
#                     group_notify(self)
#                 self.notified = True
#                 super(CTPost, self).save(*args, **kwargs)
# 
#     def get_ct_group(self):
#         """kludge cos field should be just group to be same as other models
#             TODO: change field name and update all references"""
#         return self.ct_group
#     group = property(get_ct_group)
# 
#     def _summary(self):    
#         if self.tease:
#             return self.tease
#         else:
#             return truncatewords(self.body, 80)
#     summary = property(_summary)
#     
#     def get_notify_content(self, comment=None):
#         """docstring for get_notify_content"""
#         from django.contrib.comments.models import Comment
#         
#         if comment:
#             if not isinstance(comment, Comment):
#                 comment = Comment.objects.get(pk=comment)
#             line_1 = _("A comment has been added to: %s.") % self.title
#             author= comment.user.get_full_name()
#             content = comment.comment
#             url = '%s%s#comment' % ( settings.APP_BASE[:-1], self.get_absolute_url())           
#         else:
#             line_1 = _('A discussion post has been added to: %s.') % self.group.name
#             author= self.author.get_full_name()
#             content = '%s\n%s' % (self.title, self.summary)
#             url = '%s%s' % ( settings.APP_BASE[:-1], self.get_absolute_url())
#                     
#         content = render_to_string('ct_groups/email_post_comment_content.txt', {
#             'line_1': line_1,
#             'line_2': '',
#             'author': author, 
#             'review_date': self.publish.strftime("%d/%m/%Y, %H.%M"),
#             'content': content,
#             'url': url
#         })    
#         return (True, content)

EVENT_TYPE_CHOICES = (('notify', 'notify'), ('notify_comment', 'notify comment'))
EVENT_TYPE_DEFAULT = 'notify'
EVENT_STATUS_CHOICES = (('todo', 'todo'), ('repeat', 'repeat'), ('failed', 'failed'), ('done', 'done'), )
EVENT_STATUS_DEFAULT = 'todo'

class CTEvent(models.Model):
    """docstring for CTEvent"""
    last_updated = models.DateTimeField(blank=True, null=True)
    group = models.ForeignKey(CTGroup, blank=True, null=True)
    event_type = models.CharField(max_length=16, choices=EVENT_TYPE_CHOICES, default=EVENT_TYPE_DEFAULT)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    data = models.CharField(max_length=48, blank=True, null=True)
    notify_setting = models.CharField(max_length=16, blank=True, null=True)
    perm = models.CharField(max_length=16, blank=True, null=True)
    status = models.CharField(max_length=16, choices=EVENT_STATUS_CHOICES, default=EVENT_STATUS_DEFAULT)
    
    def __unicode__(self):
        """docstring for __unicode__"""
        return 'CTEvent: %s, %s, %s|%s (%s)' % (self.group, self.event_type,
            self.content_type, self.object_id, self.last_updated)
            
    def save(self, *args, **kwargs):
        self.last_updated = datetime.datetime.now()
        # self.log_state()      
        super(CTEvent, self).save(*args, **kwargs)

    def done(self, status='done'):
        """docstring for done"""
        self.status = status
        self.save()

def group_notify(obj, managers=False):
    """docstring for group_email"""
    if hasattr(obj, 'get_notify_content'):
        enabled, content = obj.get_notify_content()
        if enabled:
            email_notify([obj.group], content, 'blog', managers)
            # email to managers will go straight away, so no need to digest
            if not managers:
                add_notify_event(obj, 'notify', 'blog')
    else:
        print 'obj does not provide notify content'

def email_comment(sender, instance, **kwargs):
    if kwargs.get('created', False):
        obj = instance.content_object
        if hasattr(obj, 'get_notify_content'):
            enabled, content = obj.get_notify_content(comment=instance)
            email_notify([obj.group], content, 'blog')
            add_notify_event(obj, 'notify_comment', 'blog', instance.id)
        else:
            print 'obj does not provide notify content'
    
def add_notify_event(obj, event_type, perm, data=None):
    """docstring for add_notify_event"""
    
    if hasattr(obj, 'multi_groups'):
        all_groups = obj.multi_groups
    else:
        all_groups = [obj.group]
    
    # print obj, all_groups
    for group in all_groups:
        if group:
            ev = CTEvent(
                group = group,
                event_type = event_type,
                content_object = obj,
                perm = perm,
                data = data
            )
            ev.save()

def email_notify(groups, content, perm, managers=False):
    # leave here - recursive load problem
    from ct_groups.decorators import check_permission
    
    all_memberships = []
    for group in groups:
        if group:
            if managers: 
                # ignore settings and send to all managers at once
                all_memberships.extend(group.get_managers())
            else:
                all_memberships.extend([member for member in group.groupmembership_set.all() 
                    if (member.notify_pref(perm) == 'single') and 
                        member.is_active and 
                        check_permission(member.user, group, perm, 'r')])

    add_list = list(frozenset([member.user.email for member in all_memberships]))
    if len(add_list) == 0:
        return
    site = Site.objects.get_current().name
    body = render_to_string('ct_groups/email_post_comment_body.txt',
        { 'content': content, 'site': site, 'dummy': datetime.datetime.now().strftime("%H:%M"),
            'settings_url': '%s%s' % ( settings.APP_BASE[:-1], reverse('group-edit', kwargs={'group_slug': group.slug}))})
            
    # TODO: put this in utils
    # also used in ct_template.models
    email = EmailMessage(
        #subject, body, from_email, to, bcc, connection)
        '[%s] %s update' % (site, group.name), 
        fix_email_body(body), 
        'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
        [settings.DEFAULT_FROM_EMAIL],
        add_list )
    email.send()

def process_digests():
    """docstring for email_digests"""
    # leave here - recursive load problem
    from ct_groups.decorators import check_permission
        
    events = CTEvent.objects.filter(status='todo').order_by('last_updated', 'content_type', 'object_id')
    event_dict = { }
    for event in events:
        group = event_dict.setdefault(event.group, {})
        perm = group.setdefault(event.perm, {})
        # perm['notify_setting'] = event.notify_setting
        obj_type = perm.setdefault(event.content_type, {})
        obj_data = obj_type.setdefault(event.content_object, {})
        if event.event_type == 'notify':
            obj_data['obj'] = True
        elif event.event_type == 'notify_comment':
            comments = obj_data.setdefault('comments', [])
            comments.append(event.data)
        else:
            raise Exception('unrecognised event_type')
        event.done()
            
    site = Site.objects.get_current().name
    for group, digest in event_dict.iteritems():
        # print '*** group', group
        # print digest
        for perm, items in digest.iteritems():
            # print perm
            members = group.groupmembership_set.all()
            add_list = list(member.user.email for member in members if (member.notify_pref(perm) == 'digest') and 
                member.is_active and 
                check_permission(member.user, group, perm, 'r'))
            # print add_list

            if len(add_list):
                content = ''
                
                for content_type in items.itervalues():
                    for obj, data in content_type.iteritems():
                        # print data
                        if data.get('obj', False):
                            dummy, txt = obj.get_notify_content()
                            content += txt
                        comment_ids = data.get('comments', False)
                        if comment_ids:
                            # TODO just pass comment id, not comment, so template can use
                            # for comment in [Comment.objects.get(pk=c) for c in comment_ids]:
                            for c_id in comment_ids:
                                dummy, txt = obj.get_notify_content(comment=c_id)
                                content += txt
                
                body = render_to_string('ct_groups/email_digest_body.txt',
                    { 'group': group.name, 'content': content, 'site': site, 'dummy': datetime.datetime.now().strftime("%H:%M"),
                        'settings_url': '%s%s' % ( settings.APP_BASE[:-1], reverse('group-edit', kwargs={'group_slug': group.slug}))})
                email = EmailMessage(
                    #subject, body, from_email, to, bcc, connection)
                    '[%s] %s update' % (site, group.name), 
                    fix_email_body(body), 
                    'do not reply <%s>' % settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],
                    add_list )
                email.send()

    CTEvent.objects.filter(status='done').delete()

# def fix_open_id(sender, instance, **kwargs):
#     if kwargs.get('created', False):
#         user = instance.user
#         users = list(User.objects.filter(email=user.email))
#         if len(users) > 1:
#             users.remove(user)
#             print users
#             existing_user = users[0]
#             for attr in ('first_name', 'last_name'):
#                 setattr(existing_user, attr, 
#                     getattr(existing_user, attr, None) or getattr(user, attr, None))
#             existing_user.save()
#             instance.user = existing_user
#             instance.save()
#             print 'deleting user ', user
#             # THIS DOESN'T WORK- BEING CALLED IN SAVE SIGNAL? NEED TO QUEUE FOR DELETION IN SEP PROCESS ?
#             user.delete()
#         print 'created UserOpenID with user: %s' % instance.user
#     print instance.user

def is_email_in_use(user, email):
    return bool([u for u in User.objects.filter(email=email) if u.id != user.id])
    
def email_unique(sender, instance, **kwargs):
    if is_email_in_use(instance, instance.email):
        print 'checking unique email:', instance.email
        # User.message_set.create(message)
        
        # TODO THIS BREAKS OPENID REGISTRATION COS IT CALLS user.save()
        raise DuplicateEmailException


# SIGNALS

if not settings.DEBUG:
    signals.post_save.connect(email_comment, sender=Comment)

# try:
#     from django_openid_auth.models import UserOpenID
#     signals.post_save.connect(fix_open_id, sender=UserOpenID)
# except ImportError:
#     pass

try:
    USER_EMAIL_UNIQUE = settings.USER_EMAIL_UNIQUE
except AttributeError:
    USER_EMAIL_UNIQUE = True
if USER_EMAIL_UNIQUE:
    signals.pre_save.connect(email_unique, sender=User)
    

