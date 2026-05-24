from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from hospitals.models import Hospital
from hospitals.serializers import HospitalSerializer
from ml_engine.models import DonorMatchOutcome
from blood_requests.models import BloodRequest


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Registration successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'hospital': None,
        }, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        # Try by email
        try:
            u = User.objects.get(email=username)
            user = authenticate(username=u.username, password=password)
        except User.DoesNotExist:
            pass

    if not user:
        return Response({'error': 'Wrong username or password'}, status=401)

    refresh = RefreshToken.for_user(user)
    hospital = None
    try:
        hospital = HospitalSerializer(user.hospital).data
    except Exception:
        pass

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
        'hospital': hospital,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    hospital = None
    try:
        hospital = HospitalSerializer(request.user.hospital).data
    except Exception:
        pass
    return Response({
        'user': UserSerializer(request.user).data,
        'hospital': hospital,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    try:
        hospital = request.user.hospital
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital profile not found'}, status=404)

    requests_qs = BloodRequest.objects.filter(hospital=hospital)
    total     = requests_qs.count()
    completed = requests_qs.filter(status='completed').count()
    pending   = requests_qs.exclude(status__in=['completed', 'cancelled', 'failed']).count()
    ml_count  = DonorMatchOutcome.objects.count()

    from blood_requests.serializers import BloodRequestSerializer
    recent = BloodRequest.objects.filter(hospital=hospital).order_by('-created_at')[:5]

    return Response({
        'total_requests':     total,
        'completed_requests': completed,
        'pending_requests':   pending,
        'success_rate':       round((completed / total * 100) if total > 0 else 0, 1),
        'ml_training_data':   ml_count,
        'ml_autonomous_mode': ml_count >= 50,
        'ml_threshold':       50,
        'recent_requests':    BloodRequestSerializer(recent, many=True).data,
    })