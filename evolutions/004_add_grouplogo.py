from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('CTGroup', 'logo', models.ImageField, max_length=100, null=True),
    AddField('GroupMembership', 'is_editor', models.BooleanField, initial=False),
]
