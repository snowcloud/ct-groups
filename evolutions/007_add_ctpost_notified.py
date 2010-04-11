from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('CTPost', 'notified', models.BooleanField, initial=False)
]
