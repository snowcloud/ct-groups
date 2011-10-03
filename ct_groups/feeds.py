from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from ct_blog.models import Post

class BlogPostsPublicFeed(Feed):
    _site = Site.objects.get_current()
    title = '%s feed' % _site.name
    description = '%s posts feed.' % _site.name

    def link(self):
        return reverse('blog_index')

    def items(self):
        return Post.objects.public()[:10]

    def item_pubdate(self, obj):
        return obj.publish

