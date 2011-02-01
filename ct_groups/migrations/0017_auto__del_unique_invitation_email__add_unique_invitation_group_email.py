# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Invitation', fields ['email']
        db.delete_unique('ct_groups_invitation', ['email'])

        # Adding unique constraint on 'Invitation', fields ['group', 'email']
        db.create_unique('ct_groups_invitation', ['group_id', 'email'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Invitation', fields ['group', 'email']
        db.delete_unique('ct_groups_invitation', ['group_id', 'email'])

        # Adding unique constraint on 'Invitation', fields ['email']
        db.create_unique('ct_groups_invitation', ['email'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'blog.category': {
            'Meta': {'ordering': "('title',)", 'object_name': 'Category', 'db_table': "'blog_categories'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'blog.post': {
            'Meta': {'ordering': "('-publish',)", 'object_name': 'Post', 'db_table': "'blog_posts'"},
            'allow_comments': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['blog.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'publish': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'tease': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ct_groups.ctevent': {
            'Meta': {'object_name': 'CTEvent'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '48', 'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'default': "'notify'", 'max_length': '16'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ct_groups.CTGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_setting': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'perm': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'todo'", 'max_length': '16'})
        },
        'ct_groups.ctgroup': {
            'Meta': {'ordering': "['name']", 'object_name': 'CTGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'through': "orm['ct_groups.GroupMembership']", 'symmetrical': 'False'}),
            'moderate_membership': ('django.db.models.fields.CharField', [], {'default': "'closed'", 'max_length': '8'}),
            'moderated_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'resource_comment_order': ('django.db.models.fields.CharField', [], {'default': "u'oldest first'", 'max_length': '12'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        'ct_groups.ctgrouppermission': {
            'Meta': {'object_name': 'CTGroupPermission'},
            'delete_permission': ('django.db.models.fields.CharField', [], {'default': "'50'", 'max_length': '3'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ct_groups.CTGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'read_permission': ('django.db.models.fields.CharField', [], {'default': "'20'", 'max_length': '3'}),
            'write_permission': ('django.db.models.fields.CharField', [], {'default': "'50'", 'max_length': '3'})
        },
        'ct_groups.ctpost': {
            'Meta': {'ordering': "('-publish',)", 'object_name': 'CTPost', '_ormbases': ['blog.Post']},
            'ct_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ct_groups.CTGroup']", 'null': 'True', 'blank': 'True'}),
            'notified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['blog.Post']", 'unique': 'True', 'primary_key': 'True'})
        },
        'ct_groups.groupmembership': {
            'Meta': {'object_name': 'GroupMembership'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ct_groups.CTGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_editor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_manager': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderation': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ct_groups.Moderation']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'post_updates': ('django.db.models.fields.CharField', [], {'default': "'single'", 'max_length': '8'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'accepted'", 'max_length': '8'}),
            'tool_updates': ('django.db.models.fields.CharField', [], {'default': "'single'", 'max_length': '8'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'ct_groups.invitation': {
            'Meta': {'unique_together': "(('group', 'email'),)", 'object_name': 'Invitation'},
            'accept_key': ('django.db.models.fields.CharField', [], {'max_length': '44', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'accepted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accepted_by'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ct_groups.CTGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'inviter'", 'to': "orm['auth.User']"}),
            'sent': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'to_send'", 'max_length': '8'})
        },
        'ct_groups.moderation': {
            'Meta': {'object_name': 'Moderation'},
            'applicants_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'moderator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'response_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '8'})
        }
    }

    complete_apps = ['ct_groups']
