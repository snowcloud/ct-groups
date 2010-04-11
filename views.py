""" views for workgroups app

"""
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.contrib.auth.decorators import login_required
from ct_groups.decorators import check_permission
from ct_groups.models import CTGroup, GroupMembership, CTPost
from ct_groups.forms import BlogPostForm, GroupMembershipForm
from basic.blog.models import Category
import datetime

def index(request):
    group_list = CTGroup.objects.order_by('name')
    return render_to_response('workgroups_index.html', RequestContext( request, {'group_list': group_list, } ))

def detail(request, object_id):
    o = get_object_or_404(CTGroup, pk=object_id)
    u = request.user
    is_member = u.is_authenticated and o.has_member(u)
    print "is_member"
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
    try:
        gm = GroupMembership.objects.get(user=u, group=group)
    except GroupMembership.DoesNotExist:
        gm = GroupMembership(user=u, group=group)
        gm.save()
    return render_to_response('ct_groups/ct_groups_confirm_join.html', RequestContext( request, {'group': group, }))

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

def email_digests(request):
	"""docstring for email_digests"""
	for group in CTGroup.objects.all():
		group.email_digests()
	return HttpResponse('OK')