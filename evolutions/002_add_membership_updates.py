from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('GroupMembership', 'notify_post_updates', models.BooleanField, initial=1),
    AddField('GroupMembership', 'notify_tool_updates', models.BooleanField, initial=1)
]
