""" views for workgroups app

"""
import datetime

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
from basic.blog.models import Category

from ct_groups.decorators import check_permission
from ct_groups.models import CTGroup, Moderation, GroupMembership, Invitation, CTPost, \
    process_digests, group_notify
from ct_groups.forms import BlogPostForm, GroupJoinForm, GroupMembershipForm, ModerateRefuseForm, \
    InviteMemberForm, ProfileForm
from ct_groups.registration_backends import RegistrationWithName

def index(request):
    group_list = CTGroup.objects.order_by('name')
    return render_to_response('workgroups_index.html', RequestContext( request, {'group_list': group_list, } ))

def detail(request, object_id):
    o = get_object_or_404(CTGroup, pk=object_id)
    u = request.user
    is_member = u.is_authenticated and o.has_member(u)
    # print "is_member"
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
            return HttpResponseRedirect(reverse('group',kwargs={'group_slug':object.slug}))
    else:
        membershipform = GroupMembershipForm(instance=membership)

    return render_to_response('ct_groups/ct_groups_edit.html', 
        RequestContext( request, {'object': object, 'membershipform': membershipform, 'membership': membership }))

@login_required
def group_note(request, group_slug):
    """docstring for group_note"""
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()

    if request.method == 'POST':
        note = request.POST.get("note", None)
        if note:
            object.note = note
            object.save()
            return HttpResponseRedirect(reverse('group-edit',kwargs={'group_slug':object.slug}))
    
    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))

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

            profile_form = ProfileForm(request.POST)
            if profile_form.is_valid():
                user.first_name = profile_form.clean()['first_name']
                user.last_name = profile_form.clean()['last_name']
                user.email = profile_form.clean()['email']
                user.save()
                # profile.note = profile_form.clean()['note']
                # profile.save()
                return HttpResponseRedirect('/accounts/profile/changed/')

    else: # not a POST
        profile_form = ProfileForm({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            # 'note': profile.note,
             })

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
            return HttpResponseRedirect(reverse('group-edit',kwargs={'group_slug': object.slug}))
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # print email, form.users
            invitation = Invitation(group=object, inviter=u, email=email)
            invitation.save() # this will generate the accept_key
            invitation.send()
            
            return HttpResponseRedirect(reverse('group-edit',kwargs={'group_slug': object.slug}))
    else:
        form = InviteMemberForm()
    
    return render_to_response('ct_groups/invite_member.html', RequestContext( request, {'object': object, 'form': form }))

@login_required
def invitation_remove(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    u = request.user
    if not check_permission(u, object, 'group', 'w'):
        raise PermissionDenied()
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted:
        invitation.delete()
    return HttpResponseRedirect(reverse('group-edit',kwargs={'group_slug': object.slug}))

def accept_invitation(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted:
        raise Http404
    try:
        user = User.objects.get(email=invitation.email)
        return HttpResponseRedirect(reverse('complete-invitation',kwargs={'group_slug': object.slug, 'key': key}))

    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('register-invitee',kwargs={'group_slug': object.slug, 'key': key}))

@login_required
def complete_invitation(request, group_slug, key):
    object = get_object_or_404(CTGroup, slug=group_slug)
    invitation = get_object_or_404(Invitation, accept_key=key)
    if invitation.is_accepted or invitation.group != object:
        raise Http404
    
    if invitation.email != request.user.email:
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
        return HttpResponseRedirect(reverse('group-edit',kwargs={'group_slug':object.slug}))
    return render_to_response('ct_groups/ct_groups_edit.html', RequestContext( request, {'object': object, }))
    
@login_required
def remove_editor(request, group_slug, object_id):
    """docstring for remove-editor"""
    return change_editor(request, group_slug, object_id, 'remove')
    
@login_required
def make_editor(request, group_slug, object_id):
    """docstring for remove-editor"""
    return change_editor(request, group_slug, object_id, 'make')

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

        return HttpResponseRedirect(reverse('group-edit', kwargs={'group_slug': group_slug}))

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
            return HttpResponseRedirect(reverse('group-edit', kwargs={'group_slug': group_slug}))
        #     redirect to group

        form = ModerateRefuseForm(request.POST)
        if form.is_valid():
            membership = get_object_or_404(GroupMembership, pk=object_id)
            membership.refuse(form.cleaned_data['reason_for_refusal'])

            return HttpResponseRedirect(reverse('group-edit', kwargs={'group_slug': group_slug}))

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
    
    return HttpResponseRedirect(reverse('group-edit', kwargs={'group_slug': group_slug}))
    
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

@login_required
def blog_new_post(request, group_slug):
    group = get_object_or_404(CTGroup, slug=group_slug)

    if request.method == 'POST':
        form = BlogPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.slug = slugify(post.title)
            post.publish = datetime.datetime.now()
            post.ct_group = group
            post.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = BlogPostForm()
    return render_to_response('blog/post_add.html',
        RequestContext( request, {'form': form,  }))


@login_required
def blog_post_edit(request, group_slug, slug):

    obj = get_object_or_404(CTPost, slug=slug)

    if request.method == 'POST':
        form = BlogPostForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(obj.get_absolute_url())
    else:
        form = BlogPostForm(instance=obj)
    return render_to_response('blog/post_add.html',
        RequestContext( request, {'form': form, 'object': obj }))

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
