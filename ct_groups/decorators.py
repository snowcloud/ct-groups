from django.contrib.auth.views import login
from django.core.exceptions import PermissionDenied
from django.db.models import get_model
from django.http import HttpResponseRedirect

"""
def my_decorator(something)

@my_decorator('blah')
def func(...)
"""
CTGroupPermission = get_model('ct_groups', 'ctgrouppermission')
CTGroup = get_model('ct_groups', 'ctgroup')


def check_permission(user, group=None, perm_type=None, access=None ):
    """if group is None, will check NON_GROUP_PERMS
    if group instance is not CTGroup, will return None
    otherwise, will look up group permissions and compare to user"""
    
    from ct_groups.models import NON_GROUP_PERMS
    if (group is None):
        return access in NON_GROUP_PERMS.get(perm_type, [])
    if (not isinstance(group, CTGroup)) or user is None:
        return False
    try:
        perm = CTGroupPermission.objects.get(group=group, name=perm_type)
    except CTGroupPermission.DoesNotExist:
        return False
    return perm.check_permission(user, access)

def group_perm(perm_type, access):
    def _group_perm(fn):
        def _check(request, *args, **kwargs):
            user = request.user
            group_slug = kwargs.get('group_slug', None)
            try:
                group = CTGroup.objects.get(slug=group_slug) 
                if check_permission(user, group, perm_type, access):
                    # raise Exception('%s, %s, %s' % (group, perm_type, access))
                    return fn(request, *args, **kwargs)
            except CTGroup.DoesNotExist:
                pass
            if request.POST:
                return login(request)
            else:
                return HttpResponseRedirect('/accounts/login/?next=%s' % (request.path))
            
        return _check
    # raise Exception('%s, %s' % (perm_type, access))
    return _group_perm
