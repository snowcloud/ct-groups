from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('CTGroup', 'is_public', models.BooleanField, initial=True)
]
