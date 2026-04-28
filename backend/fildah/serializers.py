from accounts.models import OrganizationMember


def product_dict(product):
    return {
        "id": product.id,
        "slug": product.slug,
        "name": product.name,
        "tagline": product.tagline,
        "summary": product.short_description,
        "short_description": product.short_description,
        "long_description": product.long_description,
        "category": product.category,
        "status": product.status,
        "frontend_url": product.frontend_url,
        "marketing_path": product.marketing_path,
        "api_namespace": product.api_namespace,
        "primary_color": product.primary_color,
        "secondary_color": product.secondary_color,
        "logo_url": product.logo_url,
        "icon_url": product.icon_url,
        "is_featured": product.is_featured,
    }


def page_dict(page):
    return {
        "slug": page.slug,
        "title": page.title,
        "page_type": page.page_type,
        "summary": page.summary,
        "body": page.body,
        "seo_title": page.seo_title,
        "seo_description": page.seo_description,
        "published_at": page.published_at,
        "updated_at": page.updated_at,
    }


def doc_dict(section):
    payload = {
        "slug": section.slug,
        "title": section.title,
        "summary": section.summary,
        "body": section.body,
        "published_at": section.published_at,
        "updated_at": section.updated_at,
    }
    if section.product:
        payload["product"] = {
            "slug": section.product.slug,
            "name": section.product.name,
        }
    else:
        payload["product"] = None
    return payload


def blog_post_dict(post):
    payload = {
        "slug": post.slug,
        "title": post.title,
        "excerpt": post.excerpt,
        "body": post.body,
        "status": post.status,
        "published_at": post.published_at,
        "updated_at": post.updated_at,
    }
    if post.product:
        payload["product"] = {
            "slug": post.product.slug,
            "name": post.product.name,
        }
    else:
        payload["product"] = None
    return payload


def product_access_dict(access):
    return {
        "id": access.id,
        "role": access.role,
        "status": access.status,
        "product": product_dict(access.product),
        "organization": (
            {
                "id": access.organization.id,
                "name": access.organization.name,
                "slug": access.organization.slug,
            }
            if access.organization
            else None
        ),
    }


def account_summary_dict(user):
    profile = getattr(user, "profile", None)
    subscription = getattr(user, "subscription", None)
    memberships = OrganizationMember.objects.select_related("organization", "organization__plan").filter(user=user)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "preferred_name": profile.preferred_name if profile else "",
            "role": profile.role if profile else "",
        },
        "subscription": (
            {
                "status": subscription.status,
                "plan": {
                    "name": subscription.plan.name,
                    "tier": subscription.plan.tier,
                    "price_monthly": str(subscription.plan.price_monthly),
                },
                "started_at": subscription.started_at,
                "expires_at": subscription.expires_at,
            }
            if subscription
            else None
        ),
        "organizations": [
            {
                "id": membership.organization.id,
                "name": membership.organization.name,
                "slug": membership.organization.slug,
                "role": membership.role,
                "plan": membership.organization.plan.name,
                "joined_at": membership.joined_at,
            }
            for membership in memberships
        ],
    }
