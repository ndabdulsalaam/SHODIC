from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rxchat', '0003_conversation_role_override'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='attachments',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
