""" urls.py for ct_groups app

"""

# from django.db.models import signals
from django.conf import settings
from django.conf.urls.defaults import *
# from django.contrib.auth.models import User
# from django.contrib.comments.models import Comment

from ct_groups.models import CTGroup #, email_comment, fix_open_id, email_unique
from ct_groups.forms import CTPageForm
from ct_groups.views import blog_new_post, blog_post_edit, group_detail, group_edit, group_note, \
    remove_editor, make_editor, moderate_accept, moderate_refuse, moderate_refuse_confirm, moderate_remove, \
    invite_member, accept_invitation, complete_invitation, register_invitee, invitation_remove
from ct_groups.decorators import group_perm

blog_view = group_perm('blog', 'r')
blog_edit = group_perm('blog', 'w')
group_access = group_perm('group', 'r')
group_write = group_perm('group', 'w')

wiki_args = {'group_slug_field': 'slug', 'group_qs': CTGroup.objects.all(), 'ArticleFormClass': CTPageForm }

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.list_detail.object_list', 
        dict(queryset=CTGroup.objects.all(), 
        paginate_by=400,
        template_name='ct_groups/ct_groups_index.html' ), name="groups"),    

    url(r'^process-digests/$', 'ct_groups.views.do_digests', name="process-digests"),

    url(r'^(?P<group_slug>[^/]+)/edit/$', group_access(group_edit), name="group-edit"),
    url(r'^(?P<group_slug>[^/]+)/note/$', group_write(group_note), name="group-note"),
    url(r'^(?P<group_slug>[^/]+)/note/$', group_write(group_note), name="group-note"),
    
    url(r'^(?P<group_slug>[^/]+)/invite/(?P<key>[^/]+)/$', accept_invitation, \
        name="accept-invitation"),    
    url(r'^(?P<group_slug>[^/]+)/invite-member/$', group_write(invite_member), \
        name="invite-member"),
    url(r'^(?P<group_slug>[^/]+)/invitation-remove/(?P<key>[^/]+)/$', group_write(invitation_remove), \
        name="invitation-remove"),    
    url(r'^(?P<group_slug>[^/]+)/register-invitee/(?P<key>[^/]+)/$', register_invitee, \
        name="register-invitee"),
    url(r'^(?P<group_slug>[^/]+)/complete-invitation/(?P<key>[^/]+)/$', complete_invitation, \
        name="complete-invitation"),

    url(r'^(?P<group_slug>[^/]+)/make-editor/(?P<object_id>[^/]+)/$', group_write(make_editor), \
        name="make-editor"),
    url(r'^(?P<group_slug>[^/]+)/remove-editor/(?P<object_id>[^/]+)/$', group_write(remove_editor), \
        name="remove-editor"),

    url(r'^(?P<group_slug>[^/]+)/moderate-accept/(?P<object_id>[^/]+)/$', group_write(moderate_accept), \
        name="moderate-accept"),
    url(r'^(?P<group_slug>[^/]+)/moderate-refuse/(?P<object_id>[^/]+)/$', group_write(moderate_refuse), \
        name="moderate-refuse"),
    url(r'^(?P<group_slug>[^/]+)/moderate-refuse-confirm/(?P<object_id>[^/]+)/$', group_write(moderate_refuse_confirm), \
        name="moderate-refuse-confirm"),
    url(r'^(?P<group_slug>[^/]+)/moderate-remove/(?P<object_id>[^/]+)/$', group_write(moderate_remove), \
        name="moderate-remove"),

    url(r'^(?P<group_slug>[^/]+)/blog/new-post/', blog_edit(blog_new_post), name='blog-new-post'),
    url(r'^(?P<group_slug>[^/]+)/blog/edit/(?P<slug>[^/]+)', blog_edit(blog_post_edit), name='blog-new-post'),
    url(r'^(?P<group_slug>[^/]+)/wiki/', include('ct_groups.wiki_urls'), wiki_args),
    url(r'^(?P<group_slug>[^/]+)/$', group_access(group_detail), name='group'),

    url(r'^join/(?P<object_id>\d+)/$', 'ct_groups.views.join', name="join-group"),
    url(r'^leave/(?P<object_id>\d+)/$', 'ct_groups.views.leave', name="leave-group"),
	)
