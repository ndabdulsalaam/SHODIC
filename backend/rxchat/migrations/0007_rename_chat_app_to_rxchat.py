from django.db import migrations


TABLE_RENAMES = [
    ("chat_conversation", "rxchat_conversation"),
    ("chat_message", "rxchat_message"),
    ("chat_ingestionlog", "rxchat_ingestionlog"),
    ("chat_scrapeprogress", "rxchat_scrapeprogress"),
    ("chat_sourcefileupload", "rxchat_sourcefileupload"),
    ("chat_rawsourcedata", "rxchat_rawsourcedata"),
    ("chat_drugchunk", "rxchat_drugchunk"),
]


def _rename_tables(schema_editor, table_pairs):
    existing_tables = set(schema_editor.connection.introspection.table_names())
    quote = schema_editor.quote_name

    for old_name, new_name in table_pairs:
        old_exists = old_name in existing_tables
        new_exists = new_name in existing_tables

        if old_exists and not new_exists:
            schema_editor.execute(
                f"ALTER TABLE {quote(old_name)} RENAME TO {quote(new_name)}"
            )
            existing_tables.remove(old_name)
            existing_tables.add(new_name)


def rename_chat_to_rxchat(apps, schema_editor):
    _rename_tables(schema_editor, TABLE_RENAMES)

    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="chat").update(app_label="rxchat")


def rename_rxchat_to_chat(apps, schema_editor):
    _rename_tables(schema_editor, [(new, old) for old, new in reversed(TABLE_RENAMES)])

    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="rxchat").update(app_label="chat")


class Migration(migrations.Migration):

    dependencies = [
        ("rxchat", "0006_alter_drugchunk_options_alter_ingestionlog_options_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(rename_chat_to_rxchat, rename_rxchat_to_chat),
    ]
