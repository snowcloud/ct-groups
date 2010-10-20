from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    DeleteField('GroupMembership', 'notify_updates')
]
