from django.template import Library, Node, TemplateSyntaxError, Variable
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

register = Library()

from django.contrib.contenttypes.models import ContentType

def _get_ct(obj):
    """ Return the ContentType of the object's model.
    """
    return ContentType.objects.get(app_label=obj._meta.app_label,
                                   model=obj._meta.module_name)

from django.contrib.comments.models import Comment
from django.db.models import get_model
Article = get_model('wiki', 'article')
CTGroup = get_model('ct_groups', 'ctgroup')
Post = get_model('ct_groups', 'ctpost')


"""
    example usage:
    # {% permitted_objects tagged_templates with resource_access for user as templates %}
"""

class PermittedObjectsNode(Node):
    def __init__(self, objects, access, user, varname):
        self.access, self.varname = access, varname
        self.objects = Variable(objects)
        self.user = Variable(user)

    def render(self, context):
        actual_objects = self.objects.resolve(context)
        actual_user = self.user.resolve(context)
        access_func = globals()[self.access]
        context[self.varname] = [o for o in actual_objects if access_func(post_as_ctpost(o).group, actual_user)]
        return ''

def permitted_objects(parser, token):
    bits = token.contents.split()
    if len(bits) != 8:
        raise TemplateSyntaxError, "get_latest tag takes exactly 7 arguments"
    if bits[2] != 'with':
        raise TemplateSyntaxError, "second argument to get_latest tag must be 'with'"
    if bits[3] not in globals():
        raise TemplateSyntaxError, "access function %s not found" % bits[3]
    if bits[4] != 'for':
        raise TemplateSyntaxError, "second argument to get_latest tag must be 'for'"
    if bits[6] != 'as':
        raise TemplateSyntaxError, "fourth argument to get_latest tag must be 'as'"
    return PermittedObjectsNode(bits[1], bits[3], bits[5], bits[7])

permitted_objects = register.tag(permitted_objects)


class LatestCatPostsNode(Node):
    def __init__(self, num, group, varname):
        self.num, self.varname = num, varname
        self.group = Variable(group)

    def render(self, context):
        actual_group = self.group.resolve(context)
        context[self.varname] = Post.objects.filter(ct_group=actual_group)
        return ''

def get_latest_group_posts(parser, token):
    bits = token.contents.split()
    if len(bits) != 6:
        raise TemplateSyntaxError, "get_latest tag takes exactly 5 arguments"
    if bits[2] != 'for':
        raise TemplateSyntaxError, "second argument to get_latest tag must be 'for'"
    if bits[4] != 'as':
        raise TemplateSyntaxError, "fourth argument to get_latest tag must be 'as'"
    return LatestCatPostsNode(bits[1], bits[3], bits[5])

"""
    example usage:
    {% get_latest_group_posts 5 for group as latest_post_list %}
"""
get_latest_group_posts = register.tag(get_latest_group_posts)

class LatestGroupCommentsNode(Node):
    def __init__(self, num, group, varname):
        self.num, self.varname = num, varname
        self.group = Variable(group)

    def render(self, context):
        actual_group = self.group.resolve(context)
        post_ids = [post.id for post in Post.objects.filter(ct_group=actual_group)]
        c_type = _get_ct(Post)
        context[self.varname] = Comment.objects.order_by('-submit_date').filter(content_type=c_type, object_pk__in=post_ids)[:self.num]
        return ''

def get_latest_group_comments(parser, token):
    bits = token.contents.split()
    if len(bits) != 6:
        raise TemplateSyntaxError, "get_latest tag takes exactly 5 arguments"
    if bits[2] != 'for':
        raise TemplateSyntaxError, "second argument to get_latest tag must be 'for'"
    if bits[4] != 'as':
        raise TemplateSyntaxError, "fourth argument to get_latest tag must be 'as'"
    return LatestGroupCommentsNode(bits[1], bits[3], bits[5])

"""
    example usage:
    {% get_latest_group_comments 5 for group as latest_comment_list %}
"""
get_latest_group_comments = register.tag(get_latest_group_comments)


class PagesNode(Node):
    def __init__(self, obj, varname):
        self.varname = varname
        self.obj = Variable(obj)

    def render(self, context):
        actual_obj = self.obj.resolve(context)
        msg = '-'
        if isinstance(actual_obj, Article):
            c_type = actual_obj.content_type
            obj_id = actual_obj.object_id
            msg = 'page'
        else:
            c_type = _get_ct(actual_obj)
            obj_id = actual_obj.id

        context[self.varname] = Article.objects.filter(content_type=c_type,object_id=obj_id).order_by('summary')
        return ''

def wiki_pages(parser, token):
    bits = token.contents.split()
    if len(bits) != 5:
        raise TemplateSyntaxError, "wiki_pages tag takes exactly 4 arguments"
    if bits[1] != 'for':
        raise TemplateSyntaxError, "first argument to wiki_pages tag must be 'for'"
    if bits[3] != 'as':
        raise TemplateSyntaxError, "third argument to wiki_pages tag must be 'as'"
    return PagesNode(bits[2], bits[4])

"""
    example usage:
    {% wiki_pages for group as pages %}
"""
wiki_pages = register.tag(wiki_pages)

@register.filter
def has_member(group, user):
    """ usage group|has_member:user
    
    """
    return group.has_member(user)

@register.filter
def member_status(group, user):
    """ usage group|has_member:user

    """
    memb = group.get_member(user)
    if memb:
        return memb.status
    else:
        return ''

from ct_groups.decorators import check_permission

@register.filter
def blog_new_post(group, user):
    if check_permission(user, group, 'blog', 'w'):
        return mark_safe('<p><a class="action" href="%sblog/new-post/">%s</a></p>' % (group.get_absolute_url(), _('New post')))
    else:
        return ''

@register.filter
def blog_access(group, user):
    return check_permission(user, group, 'blog', 'r')

@register.filter
def blog_edit(post, user):
    group = post.ct_group
    if not group:
        return ''    
    if check_permission(user, group, 'blog', 'w'):
        return mark_safe('<p><a href="%sblog/edit/%s/">%s</a></p>' % (group.get_absolute_url(), post.slug, _('Edit this post')))
    else:
        return ''

BlogPost = get_model('blog', 'post')
@register.filter
def post_as_ctpost(post):
    # HACK - problem using django-tagging, won't find tagged CTPost, but just blog.Post
    # so trap that and get CTPost so group is accessible
    # NB other models pass straight through, so safe to use on generic objects
    if isinstance(post, BlogPost):
        post = Post.objects.get(pk=post.id)
    return post

@register.filter
def post_access(post, user):
    group = post.ct_group
    return (group is None) or check_permission(user, group, 'blog', 'r')

@register.filter
def get_previous_post(post, group=None):
    if not group:
        group = post.ct_group
        if not group:
            return None
    qs = CTPost.objects.filter(group=group, status__gte=2, publish__lt=post.publish)
    try:
        return qs[0]
    except IndexError:
        return None
    # return self.get_previous_by_publish(status__gte=2)

@register.filter
def get_next_post(self):
    pass
    # return self.get_next_by_publish(status__gte=2)


@register.filter
def comment_access(group, user):
    return (group is None) or check_permission(user, group, 'comment', 'r')

@register.filter
def can_comment(group, user):
    if group:
        return check_permission(user, group, 'comment', 'w')
    else:
        return user.is_authenticated()


@register.filter
def wiki_new_page(group, user):
    """ NB takes group as first param"""
    if check_permission(user, group, 'wiki', 'w'):
        return mark_safe('<p><a class="action" href="%swiki/edit/new-page/">%s</a></p>' % (group.get_absolute_url(), _('New page')))
    else:
        return ''

@register.filter
def wiki_edit(article, user):
    """ NB takes article as first param"""
    if check_permission(user, article.group, 'wiki', 'w'):
        return mark_safe('<p><a href="%swiki/edit/%s/">%s</a></p>' % (article.group.get_absolute_url(), article.title, _('Edit this page')))
    else:
        return ''

@register.filter
def resource_access(group, user):
    return check_permission(user, group, 'resource', 'r')

@register.filter
def resource_can_edit(group, user):
    return check_permission(user, group, 'resource', 'w')

@register.filter
def group_access(group, user):
    return check_permission(user, group, 'group', 'r')

@register.filter
def group_edit(group, user):
    return check_permission(user, group, 'group', 'w')


