from django.contrib import admin
from ct_groups.models import *

class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra=3

class CTGroupPermissionInline(admin.TabularInline):
    model = CTGroupPermission
    extra = 1

class GroupAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        GroupMembershipInline, CTGroupPermissionInline
    ]

class ModerationAdmin(admin.ModelAdmin):
    pass
    
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'is_manager', 'is_editor', 'is_active', 'status', 'post_updates', 'tool_updates')
    ordering = ('user', 'group')    

class CTGroupPermissionAdmin(admin.ModelAdmin):
    # list_display = ('user', 'group', 'is_manager', 'is_editor', 'is_active', 'notify_updates')
    # ordering = ('user', 'group')
    pass

class CTPostAdmin(admin.ModelAdmin):
    pass

class CTEventAdmin(admin.ModelAdmin):
    list_display = ('last_updated', 'group', 'event_type', 'content_type', 'object_id', 'status', )
    ordering = ('last_updated', 'group', )    


admin.site.register(CTGroup, GroupAdmin)
admin.site.register(Moderation, ModerationAdmin)
admin.site.register(GroupMembership, GroupMembershipAdmin)
admin.site.register(CTGroupPermission, CTGroupPermissionAdmin)
admin.site.register(CTPost, CTPostAdmin)
admin.site.register(CTEvent, CTEventAdmin)