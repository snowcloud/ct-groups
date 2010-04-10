from ct_groups.models import GroupMembership

for gm in GroupMembership.objects.all():
    if gm.is_champion:
        gm.is_editor = True
        gm.save()