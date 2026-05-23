from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .integrations import router


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sources(request):
    """Returns all configured integration sources and their status."""
    return Response({
        'sources':      router.status(),
        'total_active': len(router.sources),
        'callback_urls': {
            'donors_found':         f'{router.app_url}/webhook/inbound/donors-found/',
            'availability_result':  f'{router.app_url}/webhook/inbound/availability-result/',
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reload_sources(request):
    """Reloads sources from env vars without restarting the server."""
    sources = router.reload()
    return Response({
        'message':      f'Reloaded — {len(sources)} source(s) active',
        'sources':      router.status(),
    })