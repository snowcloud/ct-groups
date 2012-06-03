""" views for workgroups app

"""
import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from contact_form.views import contact_form

from ct_blog.forms import BlogPostForm
from ct_blog.models import Post
from ct_groups.decorators import check_permission
from ct_groups.models import CTGroup, Moderation, GroupMembership, Invitation, \
    process_digests, group_notify, DuplicateEmailException
from ct_groups.forms import GroupSettingsForm, GroupJoinForm, GroupMembershipForm, \
    ModerateRefuseForm, InviteMemberForm, ProfileForm, CTGroupManagersContactForm
from ct_framework.forms import ConfirmForm
from ct_framework.registration_backends import RegistrationWithName
from wiki.models import Article

def index(request):
    group_list = CTGroup.objects.order_by('name')
    return render_to_response('workgroups_index.html', RequestContext( request, {'group_list': group_list, } ))

def detail(request, object_id):
    o = get_object_or_404(CTGroup, pk=object_id)
    u = request.user
    is_member = u.is_authenticated and o.has_member(u)
    is_manager = is_member and o.has_manager(u)
    
    return render_to_response(
        'workgroups_detail.html',
        RequestContext( request, {'group': o, 'is_member': is_member, 'is_manager': is_manager }))

@login_required
def group_edit(request, group_slug):
    """docstring for groups_edit"""
        
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'r'):
        raise PermissionDenied()

    membership = object.get_member(u)
    if request.method == 'POST':
        result = request.POST.get('result')
        if result == 'cancel':
            return HttpResponseRedirect(reverse('group',kwargs={'group_slug':object.slug}))
        membershipform = GroupMembershipForm(request.POST, instance=membership)
        if membershipform.is_valid():
            membershipform.save()
            messages.success(request, _('Your changes were saved.'))
            return HttpResponseRedirect(reverse('group',kwargs={'group_slug':object.slug}))
    else:
        membershipform = GroupMembershipForm(instance=membership)

    # group settings are not saved via this method- uses group settings
    groupsettingsform = GroupSettingsForm(instance=object)

    return render_to_response('ct_groups/ct_groups_edit.html', 
        RequestContext( request, {'object': object,
            'groupsettingsform': groupsettingsform, 'membershipform': membershipform, 'membership': membership }))

@login_required
def group_settings(request, group_slug):
    """docstring for group_note"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':
        result = request.POST.get('result')
        if result == 'cancel':
            return HttpResponseRedirect(reverse('group',kwargs={'group_slug':object.slug}))
        groupsettingsform = GroupSettingsForm(request.POST, request.FILES, instance=object)
        if groupsettingsform.is_valid():
            groupsettingsform.save()
            messages.success(request, _('Your changes were saved.'))
            return HttpResponseRedirect('%s#group' % reverse('group-edit',kwargs={'group_slug':object.slug}))
    
    return render_to_response('ct_groups/ct_groups_edit.html',
        RequestContext( request, {'object': object, 'groupsettingsform': groupsettingsform}))

@login_required
def profile(request):
    """

    """
    user = request.user
    # profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        submit = request.POST.get('result', '')
        if submit == 'cancel':
            return HttpResponseRedirect('/')
        else:

            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                user.save()
                return HttpResponseRedirect('/accounts/profile/changed/')

    else: # not a POST
        profile_form = ProfileForm(instance=user)

    return render_to_response('registration/profile_details.html',  
        RequestContext( request, { 
            'profile_form': profile_form, 
            })
        )

@login_required
def invite_member(request, group_slug):
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':
        
        if request.POST['result'] == _('Cancel'):
            return HttpResponseRedirect('%s#membership' % reverse('group-edit',kwargs={'group_slug': object.slug}))
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            invitation = Invitation(group=object, inviter=u, email=email)
            invitation.save() # this will generate the accept_key
            invitation.send()
            messages.success(request, _('Invitation sent.'))

            return HttpResponseRedirect('%s#membership' % reverse('group-edit',kwargs={'group_slug': object.slug}))
    else:
        form = InviteMemberForm(initial={'group': object.id})
    
    return render_to_response('ct_groups/invite_member.html', RequestContext( request, {'object': object, 'form': form }))

@login_required
def invitation_remove(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()
    invitation = get_object_or_404(Invitation, accept_key=key)
    # if invitation.is_accepted:
    invitation.delete()
    messages.success(request, _('Invitation removed.'))

    return HttpResponseRedirect('%s#membership' % reverse('group-edit',kwargs={'group_slug': object.slug}))

def accept_invitation(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted:
        raise Http404
    try:
        user = User.objects.get(email__iexact=invitation.email)
        return HttpResponseRedirect(reverse('complete-invitation',kwargs={'group_slug': object.slug, 'key': key}))

    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('register-invitee',kwargs={'group_slug': object.slug, 'key': key}))

@login_required
def complete_invitation(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted or invitation.group != object:
        raise Http404
    
    if invitation.email.lower() != request.user.email.lower():
        return render_to_response('ct_groups/complete_invitation.html', RequestContext( request, {'invitation': invitation, }))
    
    memb = GroupMembership.objects.get_or_create(group=object, user=request.user)
    invitation.accept(request.user)

    return render_to_response('ct_groups/ct_groups_confirm_join.html', 
        RequestContext( request, {'group': invitation.group, 'memb': memb, }))

def register_invitee(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted or invitation.group != object:
        raise Http404
    
    if request.method == 'POST':
    
        if request.POST['result'] == _('Cancel'):
            return HttpResponseRedirect('/')
        #     redirect to group
    
        form = RegistrationWithName(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                form.cleaned_data['username'], 
                form.cleaned_data['email'],
                form.cleaned_data['password1'])
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            memb = GroupMembership(user=user, group=object)
            memb.save()
            invitation.accept(user)
            user = authenticate(username=user.username, password=form.cleaned_data['password1'])
            login(request, user)
            
            return HttpResponseRedirect(reverse('group', kwargs={'group_slug': group_slug}))
    
    else:
        # a GET, so make form
        form = RegistrationWithName(initial={'email': invitation.email })

    return render_to_response('ct_groups/register_invitee.html', 
        RequestContext( request, {'form': form }))

@login_required
def change_manager(request, group_slug, object_id, change):
    """docstring for change_editor"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not (u.is_staff or object.has_manager(u)):
        raise PermissionDenied()

    if request.method == 'POST':
        membership = get_object_or_404(GroupMembership, pk=object_id)
        membership.is_manager = change == 'make'
        membership.save()
        return HttpResponseRedirect('%s#membership' % reverse('group-edit',kwargs={'group_slug':object.slug}))
    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))

@login_required
def change_editor(request, group_slug, object_id, change):
    """docstring for change_editor"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':
        membership = get_object_or_404(GroupMembership, pk=object_id)
        membership.is_editor = change == 'make'
        membership.save()
        return HttpResponseRedirect('%s#membership' % reverse('group-edit',kwargs={'group_slug':object.slug}))
    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))

@login_required
def remove_manager(request, group_slug, object_id):
    """docstring for remove_manager"""
    return change_manager(request, group_slug, object_id, 'remove')
    
@login_required
def make_manager(request, group_slug, object_id):
    """docstring for make_manager"""
    return change_manager(request, group_slug, object_id, 'make')

@login_required
def remove_editor(request, group_slug, object_id):
    """docstring for remove_editor"""
    return change_editor(request, group_slug, object_id, 'remove')
    
@login_required
def make_editor(request, group_slug, object_id):
    """docstring for make_editor"""
    return change_editor(request, group_slug, object_id, 'make')

@login_required
def remove_member(request, group_slug, object_id):
    """docstring for remove_member"""

    memb = get_object_or_404(GroupMembership, pk=object_id, group__slug=group_slug)
    if not check_permission(request.user, memb.group, 'group', 'w'):
        raise PermissionDenied()
    
    if request.POST:
        if request.POST['result'] == _('Cancel'):
            pass
            # messages.warning(request, _('Cancelled'))
        else:
            form = ConfirmForm(request.POST)
            if form.is_valid():
                memb.remove()
                messages.success(request, _('Group member removed.'))
        return HttpResponseRedirect('%s#membership' %reverse('group-edit',kwargs={'group_slug': memb.group.slug}))
    else:
        form = ConfirmForm(initial={ 'resource_name': '%s (%s)' % (memb.user.get_full_name(), memb.user.username) })

    return render_to_response('ct_framework/confirm.html', 
        RequestContext( request, 
            {   'form': form,
                'title': _('Remove member from this group?')
            })
        )

@login_required
def join(request, object_id):
    group = get_object_or_404(CTGroup, pk=object_id)
    u = request.user
    form = memb = None
    
    try:
        memb = GroupMembership.objects.get(user=u, group=group)
    except GroupMembership.DoesNotExist:
        
        # moderate_membership = 'open', 'mod', 'closed'
        if not group.is_closed:
            mod = None
            if group.moderate_membership == 'mod':
                
                if request.method == 'POST':
                    if request.POST['result'] == _('Cancel'):
                        return HttpResponseRedirect(reverse('group',kwargs={'group_slug': group.slug}))
                    form = GroupJoinForm(request.POST)
                    if form.is_valid():
                        mod = Moderation(status='pending', applicants_text=form.cleaned_data['reason_for_joining'])
                        mod.save()
                        memb = GroupMembership(user=u, group=group, moderation=mod)
                        memb.save()
                        group_notify(mod, True)
                        return HttpResponseRedirect(reverse('join-group',kwargs={'object_id': group.id}))
                    
                    # else, reshow form
                    else:
                        mod = None
                else:
                    # a GET, so make form
                    form = GroupJoinForm()
            else:
                memb = GroupMembership(user=u, group=group, moderation=mod)
                memb.save()
                

    return render_to_response('ct_groups/ct_groups_confirm_join.html', 
        RequestContext( request, {'group': group, 'memb': memb, 'form': form }))


def contact_managers(request, group_slug):
    """
    ContactForm won't take extra_context, but gets request
    so using request.META to pass in group_slug
    """
    request.META["ct_group"] = group_slug
    return contact_form(request,
        form_class=CTGroupManagersContactForm,
        success_url=reverse('contact-form-sent', kwargs={'group_slug': group_slug}))

def contact_managers_sent(request, group_slug):
    """docstring for contact_managers_sent"""
    return render_to_response('ct_groups/group_contact_form_sent.html', RequestContext( request, {'group_slug': group_slug, }))
    
@login_required
def moderate_accept(request, group_slug, object_id):
    """docstring for moderate_accept"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':
        membership = get_object_or_404(GroupMembership, pk=object_id)
        membership.approve()
        messages.success(request, _('Group membership approved.'))

        return HttpResponseRedirect('%s#membership' % reverse('group-edit', kwargs={'group_slug': group_slug}))

    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))

@login_required
def moderate_refuse(request, group_slug, object_id):
    """docstring for moderate_refuse"""
    if request.method == 'POST':
        return HttpResponseRedirect(reverse('moderate-refuse-confirm', kwargs={'group_slug': group_slug, 'object_id': object_id}))

    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))

@login_required
def moderate_refuse_confirm(request, group_slug, object_id):
    """docstring for moderate_refuse_confirm"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':

        if request.POST['result'] == _('Cancel'):
            return HttpResponseRedirect('%s#membership' % reverse('group-edit', kwargs={'group_slug': group_slug}))
        #     redirect to group

        form = ModerateRefuseForm(request.POST)
        if form.is_valid():
            membership = get_object_or_404(GroupMembership, pk=object_id)
            membership.refuse(form.cleaned_data['reason_for_refusal'])
            messages.success(request, _('Membership not approved.'))

            return HttpResponseRedirect('%s#membership' % reverse('group-edit', kwargs={'group_slug': group_slug}))

        # else, reshow form
        else:
            mod = None
    else:
        # a GET, so make form
        form = ModerateRefuseForm()

    return render_to_response('ct_groups/ct_groups_moderate_refuse.html', 
        RequestContext( request, {'group': object, 'memb': None, 'form': form }))

@login_required
def moderate_remove(request, group_slug, object_id):
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()
    
    if request.method == 'POST':
        membership = get_object_or_404(GroupMembership, pk=object_id)
        membership.delete()
        messages.success(request, _('Membership removed.'))
    
    return HttpResponseRedirect('%s#membership' % reverse('group-edit', kwargs={'group_slug': group_slug}))
    
@login_required
def leave(request, object_id):
    group = get_object_or_404(CTGroup, pk=object_id)
    u = request.user
    try:
        gm = GroupMembership.objects.get(user=u, group=group)
        gm.delete()
    except GroupMembership.DoesNotExist:
        pass
    return render_to_response('ct_groups/ct_groups_confirm_leave.html', RequestContext( request, {'group': group, }))

# @login_required
# def blog_new_post(request, group_slug):
#     group = get_object_or_404(CTGroup, slug=group_slug)
# 
#     if request.method == 'POST':
#         form = BlogPostForm(request.POST)
#         if form.is_valid():
#             post = form.save(commit=False)
#             post.author = request.user
#             post.slug = slugify(post.title)
#             post.publish = datetime.datetime.now()
#             post.group = group
#             post.save()
#             return HttpResponseRedirect(post.get_absolute_url())
#     else:
#         form = BlogPostForm()
#     return render_to_response('blog/post_add.html',
#         RequestContext( request, {'form': form,  }))
# 
# 
# @login_required
# def blog_post_edit(request, group_slug, slug):
# 
#     obj = get_object_or_404(Post, slug=slug)
# 
#     if request.method == 'POST':
#         form = BlogPostForm(request.POST, instance=obj)
#         if form.is_valid():
#             form.save()
#             return HttpResponseRedirect(obj.get_absolute_url())
#     else:
#         form = BlogPostForm(instance=obj)
#     return render_to_response('blog/post_add.html',
#         RequestContext( request, {'form': form, 'object': obj }))

def group_detail(request, group_slug):
    group = get_object_or_404(CTGroup, slug=group_slug)
    return render_to_response('ct_groups/ct_groups_detail.html',
        RequestContext( request, {'object': group,  }))

def do_digests(request):
    """docstring for email_digests"""
    process_digests()
    return HttpResponse('OK')

from django.views.i18n import set_language

@csrf_exempt
def setlang(request):
    """docstring for setlang"""
    return set_language(request)

@login_required
def delete_page(request, title, *args, **kw):
    """docstring for delete_page"""
    page = get_object_or_404(Article, title=title)
    if not check_permission(request.user, page.group, 'wiki', 'd'):
        raise PermissionDenied()
    
    if request.POST:
        if request.POST['result'] == _('Cancel'):
            return HttpResponseRedirect(page.get_absolute_url())
        else:
            form = ConfirmForm(request.POST)
            if form.is_valid():
                page.delete()
                return HttpResponseRedirect(reverse('group',kwargs={'group_slug': page.group.slug}))
    else:
        form = ConfirmForm(initial={ 'resource_name': page.title })

    return render_to_response('ct_framework/confirm.html', 
        RequestContext( request, 
            {   'form': form,
                'title': _('Delete this page?')
            })
        )

    