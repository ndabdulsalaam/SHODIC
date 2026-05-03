from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import (
    Organization,
    OrganizationMember,
    PasswordResetOTP,
    PendingEmailChange,
    PendingLoginOTP,
    PendingRegistration,
    Subscription,
    SubscriptionPlan,
    TrustedDevice,
    UserEmail,
)
from fildah.models import (
    BlogPost,
    ContactMessage,
    DocumentationSection,
    Page,
    Product,
    ProductAccess,
)
from rxchat.models import (
    Conversation,
    DrugChunk,
    IngestionLog,
    Message,
    RawSourceData,
    ScrapeProgress,
    SourceFileUpload,
)
from rxchat.qdrant_service import (
    delete_points,
    ensure_collection,
    is_protected_collection,
    reset_collection,
    upsert_drug_chunks,
)


SEED_PREFIX = "dev-seed"
SEED_PASSWORD = "password123"
SEED_SOURCES = ["nafdac", "openfda", "neml", "who", "nhia_stg"]
SEED_ROLES = ["patient", "pharmacist", "physician", "nurse", "other_health_professional"]


class Command(BaseCommand):
    help = "Seed the dev database with small fake relational data and Qdrant vectors."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous dev seed rows before seeding.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush all dev database rows before seeding fake data.",
        )
        parser.add_argument(
            "--reset-qdrant",
            action="store_true",
            help="Delete and recreate the active dev Qdrant collection before upserting seed vectors.",
        )
        parser.add_argument(
            "--skip-qdrant",
            action="store_true",
            help="Seed only Postgres rows and skip Qdrant setup/upserts.",
        )
        parser.add_argument("--batch-size", type=int, default=64)

    def handle(self, *args, **options):
        self._require_dev_environment()

        qdrant_was_reset = False
        if options["flush"]:
            if not options["skip_qdrant"]:
                reset_collection()
                qdrant_was_reset = True
            call_command("flush", interactive=False, verbosity=0)
        elif options["reset"]:
            self._clear_seed_rows(skip_qdrant=options["skip_qdrant"])

        self._clear_transient_seed_rows()
        self._seed_subscription_plans()
        users = self._seed_users()
        plans = list(SubscriptionPlan.objects.filter(tier__in=["free", "pro", "plus", "enterprise"]))
        organizations = self._seed_organizations(users, plans)
        products = self._seed_fildah_content(users, organizations)
        self._seed_rxchat_content(users)

        upserted = 0
        if not options["skip_qdrant"]:
            if options["reset_qdrant"] and not qdrant_was_reset:
                reset_collection()
            ensure_collection()
            chunks = (
                DrugChunk.objects.filter(raw_source__source_id__startswith=SEED_PREFIX)
                .select_related("raw_source")
                .order_by("raw_source__source_id", "chunk_index")
            )
            upserted = upsert_drug_chunks(chunks, batch_size=options["batch_size"])

        self.stdout.write(self.style.SUCCESS(
            "Dev seed complete: "
            f"{len(users)} users, {len(organizations)} organizations, "
            f"{len(products)} products, "
            f"{DrugChunk.objects.filter(raw_source__source_id__startswith=SEED_PREFIX).count()} drug chunks, "
            f"{upserted} Qdrant points."
        ))
        self.stdout.write(
            f"Seed user password for all dev users: {SEED_PASSWORD}"
        )

    def _require_dev_environment(self):
        env_name = getattr(settings, "DJANGO_ENV", "").lower()
        collection = settings.QDRANT_COLLECTION
        if env_name != "dev":
            raise CommandError(
                f"seed_dev only runs with DJANGO_ENV=dev. Current environment is '{env_name}'."
            )
        if is_protected_collection(collection):
            raise CommandError(
                f"Refusing to seed protected Qdrant collection '{collection}'."
            )

    def _clear_transient_seed_rows(self):
        Message.objects.filter(conversation__title__startswith="Dev seed").delete()
        PendingEmailChange.objects.filter(new_email__startswith=f"{SEED_PREFIX}-").delete()
        PendingLoginOTP.objects.filter(user__username__startswith=f"{SEED_PREFIX}-user-").delete()
        PasswordResetOTP.objects.filter(user__username__startswith=f"{SEED_PREFIX}-user-").delete()
        ContactMessage.objects.filter(email__startswith=f"{SEED_PREFIX}-").delete()
        SourceFileUpload.objects.filter(description__startswith=SEED_PREFIX).delete()
        IngestionLog.objects.filter(action__startswith=SEED_PREFIX).delete()

    def _clear_seed_rows(self, skip_qdrant=False):
        point_ids = list(
            DrugChunk.objects.filter(raw_source__source_id__startswith=SEED_PREFIX)
            .exclude(qdrant_point_id__isnull=True)
            .exclude(qdrant_point_id="")
            .values_list("qdrant_point_id", flat=True)
        )
        if point_ids and not skip_qdrant:
            delete_points(point_ids)

        self._clear_transient_seed_rows()
        RawSourceData.objects.filter(source_id__startswith=SEED_PREFIX).delete()
        ScrapeProgress.objects.filter(source__in=SEED_SOURCES).delete()
        ProductAccess.objects.filter(user__username__startswith=f"{SEED_PREFIX}-user-").delete()
        ProductAccess.objects.filter(product__slug__startswith=f"{SEED_PREFIX}-product-").delete()
        OrganizationMember.objects.filter(organization__slug__startswith=f"{SEED_PREFIX}-org-").delete()
        Organization.objects.filter(slug__startswith=f"{SEED_PREFIX}-org-").delete()
        Subscription.objects.filter(user__username__startswith=f"{SEED_PREFIX}-user-").delete()
        User.objects.filter(username__startswith=f"{SEED_PREFIX}-user-").delete()
        BlogPost.objects.filter(slug__startswith=f"{SEED_PREFIX}-blog-").delete()
        DocumentationSection.objects.filter(slug__startswith=f"{SEED_PREFIX}-doc-").delete()
        Page.objects.filter(slug__startswith=f"{SEED_PREFIX}-page-").delete()
        Product.objects.filter(slug__startswith=f"{SEED_PREFIX}-product-").delete()
        PendingRegistration.objects.filter(email__startswith=f"{SEED_PREFIX}-pending-").delete()

    def _seed_subscription_plans(self):
        plan_data = [
            ("free", "Dev Free", "0.00", 50, 10),
            ("pro", "Dev Pro", "5000.00", 500, 100),
            ("plus", "Dev Plus", "12000.00", 1500, 300),
            ("enterprise", "Dev Enterprise", "0.00", 0, 0),
        ]
        for tier, name, price, max_messages, max_conversations in plan_data:
            SubscriptionPlan.objects.update_or_create(
                tier=tier,
                defaults={
                    "name": name,
                    "price_monthly": Decimal(price),
                    "max_messages_per_day": max_messages,
                    "max_conversations": max_conversations,
                    "description": f"{name} seeded for local development.",
                    "is_active": True,
                },
            )

    def _seed_users(self):
        users = []
        for index in range(1, 6):
            username = f"{SEED_PREFIX}-user-{index}"
            email = f"{SEED_PREFIX}-{index}@example.test"
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": f"Dev{index}",
                    "last_name": "User",
                    "is_staff": index == 1,
                    "is_superuser": index == 1,
                    "is_active": True,
                },
            )
            user.set_password(SEED_PASSWORD)
            user.save(update_fields=["password"])

            profile = user.profile
            profile.first_name = user.first_name
            profile.last_name = user.last_name
            profile.preferred_name = f"Dev {index}"
            profile.role = SEED_ROLES[index - 1]
            profile.gender = "female" if index % 2 else "male"
            profile.age_range = ["18_24", "25_34", "35_44", "45_54", "55_64"][index - 1]
            profile.phone_number = f"+23480000000{index}"
            profile.save()

            UserEmail.objects.update_or_create(
                email=email,
                defaults={
                    "user": user,
                    "is_verified": True,
                    "is_primary": True,
                    "verified_at": timezone.now(),
                },
            )
            TrustedDevice.objects.update_or_create(
                user=user,
                user_agent=f"Dev Seed Browser {index}",
                defaults={"last_used": timezone.now()},
            )
            PendingRegistration.objects.update_or_create(
                email=f"{SEED_PREFIX}-pending-{index}@example.test",
                defaults={"otp_code": f"{index}{index}{index}{index}{index}{index}"},
            )
            PendingEmailChange.objects.create(
                user=user,
                new_email=f"{SEED_PREFIX}-new-email-{index}@example.test",
                otp_code=f"9{index}{index}{index}{index}{index}",
            )
            PendingLoginOTP.objects.create(user=user, otp_code=f"8{index}{index}{index}{index}{index}")
            PasswordResetOTP.objects.create(
                user=user,
                otp_code=f"7{index}{index}{index}{index}{index}",
                verified=index == 1,
            )
            users.append(user)
        return users

    def _seed_organizations(self, users, plans):
        plans_by_tier = {plan.tier: plan for plan in plans}
        organizations = []
        for index, user in enumerate(users, start=1):
            org, _ = Organization.objects.update_or_create(
                slug=f"{SEED_PREFIX}-org-{index}",
                defaults={
                    "name": f"Dev Clinic {index}",
                    "owner": user,
                    "plan": plans_by_tier["enterprise" if index == 5 else "pro"],
                    "max_members": 10 + index,
                },
            )
            OrganizationMember.objects.update_or_create(
                organization=org,
                user=user,
                defaults={
                    "role": "owner",
                    "invited_by": users[0] if user != users[0] else None,
                },
            )
            Subscription.objects.update_or_create(
                user=user,
                defaults={
                    "plan": plans_by_tier[["free", "pro", "plus", "pro", "enterprise"][index - 1]],
                    "status": "active",
                    "expires_at": None,
                },
            )
            organizations.append(org)
        return organizations

    def _seed_fildah_content(self, users, organizations):
        now = timezone.now()
        products = []
        product_names = [
            "RxChat Sandbox",
            "Clinic Notes Lab",
            "Medication Review Desk",
            "Adherence Coach",
            "Inventory Signal",
        ]
        for index, name in enumerate(product_names, start=1):
            product, _ = Product.objects.update_or_create(
                slug=f"{SEED_PREFIX}-product-{index}",
                defaults={
                    "name": name,
                    "tagline": f"Fake product {index} for dev testing.",
                    "short_description": f"Small seeded product used to test Fildah cards and access flows {index}.",
                    "long_description": "This record is fake and exists only in the dev branch.",
                    "category": "Dev",
                    "status": Product.STATUS_ACTIVE,
                    "marketing_path": f"/products/{SEED_PREFIX}-product-{index}",
                    "frontend_url": f"http://localhost:5173/dev/product-{index}",
                    "api_namespace": f"dev_product_{index}",
                    "is_featured": index <= 2,
                    "sort_order": index,
                },
            )
            products.append(product)

            Page.objects.update_or_create(
                slug=f"{SEED_PREFIX}-page-{index}",
                defaults={
                    "title": f"Dev Seed Page {index}",
                    "page_type": Page.TYPE_CUSTOM,
                    "summary": f"Fake page summary {index}.",
                    "body": "This is local development content for layout and API testing.",
                    "is_published": True,
                    "published_at": now,
                },
            )
            DocumentationSection.objects.update_or_create(
                slug=f"{SEED_PREFIX}-doc-{index}",
                defaults={
                    "title": f"Dev Seed Doc {index}",
                    "summary": f"Fake documentation summary {index}.",
                    "body": "Use this fake document to verify docs list and detail screens.",
                    "product": product,
                    "sort_order": index,
                    "is_published": True,
                    "published_at": now,
                },
            )
            BlogPost.objects.update_or_create(
                slug=f"{SEED_PREFIX}-blog-{index}",
                defaults={
                    "title": f"Dev Seed Blog {index}",
                    "excerpt": f"Fake blog excerpt {index}.",
                    "body": "This fake post exists only to exercise blog UI and API behavior.",
                    "product": product,
                    "status": BlogPost.STATUS_PUBLISHED,
                    "is_published": True,
                    "published_at": now,
                },
            )
            ContactMessage.objects.create(
                name=f"Dev Contact {index}",
                email=f"{SEED_PREFIX}-contact-{index}@example.test",
                company=f"Dev Company {index}",
                topic=f"Seed topic {index}",
                product=product,
                message="Fake contact message for local admin testing.",
                status=ContactMessage.STATUS_NEW,
            )
            ProductAccess.objects.update_or_create(
                user=users[index - 1],
                product=product,
                organization=organizations[index - 1],
                defaults={
                    "role": ProductAccess.ROLE_MEMBER,
                    "status": ProductAccess.STATUS_ACTIVE,
                },
            )
        return products

    def _seed_rxchat_content(self, users):
        for index, user in enumerate(users, start=1):
            conversation, _ = Conversation.objects.update_or_create(
                user=user,
                title=f"Dev seed conversation {index}",
                defaults={
                    "session_key": f"{SEED_PREFIX}-session-{index}",
                    "role_override": SEED_ROLES[index - 1],
                },
            )
            conversation.messages.all().delete()
            Message.objects.create(
                conversation=conversation,
                role="user",
                content=f"What should I know about dev medicine {index}?",
            )
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=f"Dev answer {index}: this is fake local guidance for UI testing only.",
            )

            source = SEED_SOURCES[index - 1]
            raw_source, _ = RawSourceData.objects.update_or_create(
                source=source,
                source_id=f"{SEED_PREFIX}-{index}",
                defaults={
                    "raw_data": {
                        "marker": SEED_PREFIX,
                        "product_name": f"Dev Medicine {index}",
                        "strength": f"{index * 100} mg",
                        "source": source,
                    },
                    "file_name": f"{SEED_PREFIX}-{index}.json",
                },
            )
            DrugChunk.objects.update_or_create(
                raw_source=raw_source,
                chunk_index=1,
                defaults={
                    "text": (
                        f"Dev Medicine {index} is a fake seeded medicine for local RxChat testing. "
                        f"It belongs to source {source} and must never be treated as clinical truth."
                    ),
                    "metadata": {
                        "drug_name": f"Dev Medicine {index}",
                        "category": "dev-seed",
                        "source_label": f"Dev Seed Source {index}",
                        "source_type": source,
                        "status": "active",
                        "is_active": True,
                    },
                },
            )
            ScrapeProgress.objects.update_or_create(
                source=source,
                defaults={
                    "progress_data": {"marker": SEED_PREFIX, "last_fake_page": index},
                    "last_run": timezone.now(),
                },
            )
            IngestionLog.objects.create(
                source=source,
                action=f"{SEED_PREFIX}-ingest-{index}",
                status="ok",
                details={"marker": SEED_PREFIX, "chunk_count": 1},
            )
            SourceFileUpload.objects.create(
                source=source,
                file=f"{SEED_PREFIX}/{source}-{index}.txt",
                description=f"{SEED_PREFIX} upload {index}",
                processed=True,
            )
