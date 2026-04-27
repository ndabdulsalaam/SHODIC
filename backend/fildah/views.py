from django.http import JsonResponse
from django.views.decorators.http import require_GET


PRODUCTS = [
    {
        'slug': 'rxchat',
        'name': 'RxChat',
        'summary': 'An AI pharmacy assistant for medication questions, drug information, and safer health decisions.',
        'status': 'active',
        'frontend_url': 'https://rxchat.fildah.com',
        'api_namespace': '/rxchat/',
    },
]


@require_GET
def home(request):
    return JsonResponse({
        'brand': {
            'name': 'Fildah',
            'tagline': 'Shared accounts, focused products, and developer-ready health technology.',
        },
        'primary_product': PRODUCTS[0],
        'navigation': [
            {'label': 'Products', 'path': '/products'},
            {'label': 'Docs', 'path': '/docs'},
            {'label': 'Developer API', 'path': '/developers/api'},
        ],
    })


@require_GET
def products(request):
    return JsonResponse({
        'products': PRODUCTS,
        'auth': {
            'shared_account': True,
            'namespace': '/auth/',
            'session_endpoint': '/auth/me/',
        },
    })


@require_GET
def docs(request):
    return JsonResponse({
        'sections': [
            {
                'slug': 'overview',
                'title': 'Fildah overview',
                'summary': 'How Fildah accounts, product frontends, and the shared API fit together.',
            },
            {
                'slug': 'rxchat',
                'title': 'RxChat',
                'summary': 'Product notes for the RxChat pharmacy assistant frontend and API namespace.',
            },
            {
                'slug': 'auth',
                'title': 'Authentication',
                'summary': 'Global sign-in routes shared by Fildah products.',
            },
        ],
    })


@require_GET
def developer_api(request):
    return JsonResponse({
        'base_url': 'https://api.fildah.com',
        'local_base_url': 'http://localhost:8000',
        'namespaces': [
            {
                'name': 'Global auth',
                'path': '/auth/',
                'examples': ['/auth/me/', '/auth/login/', '/auth/logout/'],
            },
            {
                'name': 'RxChat',
                'path': '/rxchat/',
                'examples': ['/rxchat/send/', '/rxchat/conversations/'],
            },
            {
                'name': 'Fildah public metadata',
                'path': '/',
                'examples': ['/home/', '/products/', '/docs/', '/developers/api/'],
            },
        ],
    })
