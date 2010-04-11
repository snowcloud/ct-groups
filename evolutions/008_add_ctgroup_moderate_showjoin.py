from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('CTGroup', 'show_join_link', models.BooleanField, initial=True),
    # AddField('CTGroup', 'moderate_membership', models.BooleanField, initial=False)
]