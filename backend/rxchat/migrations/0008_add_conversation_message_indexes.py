from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rxchat", "0007_rename_chat_app_to_rxchat"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["user", "-updated_at"],
                name="rxchat_conv_user_upd_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["session_key", "-updated_at"],
                name="rxchat_conv_sess_upd_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["conversation", "created_at"],
                name="rxchat_msg_conv_time_idx",
            ),
        ),
    ]
