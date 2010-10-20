from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('GroupMembership', 'post_updates', models.CharField, initial=u'single', max_length=8),
    AddField('GroupMembership', 'tool_updates', models.CharField, initial=u'single', max_length=8),
    AddField('GroupMembership', 'moderation', models.CharField, initial=u'none', max_length=8)
]
