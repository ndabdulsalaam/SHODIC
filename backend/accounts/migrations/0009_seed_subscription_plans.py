"""Seed subscription plan data: Free, Pro, Plus, Enterprise."""

from django.db import migrations


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    plans = [
        {
            'name': 'Free',
            'tier': 'free',
            'price_monthly': 0,
            'max_messages_per_day': 50,
            'max_conversations': 10,
            'description': 'Get started with RxChat — 50 messages/day, 10 conversations, RAG-powered AI.',
        },
        {
            'name': 'Pro',
            'tier': 'pro',
            'price_monthly': 7500,
            'max_messages_per_day': 0,  # unlimited
            'max_conversations': 0,    # unlimited
            'description': 'Unlimited messages and conversations with priority RAG access.',
        },
        {
            'name': 'Plus',
            'tier': 'plus',
            'price_monthly': 9000,
            'max_messages_per_day': 0,
            'max_conversations': 0,
            'description': 'Everything in Pro plus team workspace, admin roles, and priority support.',
        },
        {
            'name': 'Enterprise',
            'tier': 'enterprise',
            'price_monthly': 0,  # custom pricing
            'max_messages_per_day': 0,
            'max_conversations': 0,
            'description': 'Custom pricing for hospitals, government, and large organizations. Contact us.',
        },
    ]
    for plan_data in plans:
        SubscriptionPlan.objects.get_or_create(
            tier=plan_data['tier'],
            defaults=plan_data,
        )


def remove_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(tier__in=['free', 'pro', 'plus', 'enterprise']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_subscriptionplan_organization_pendingemailchange_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
