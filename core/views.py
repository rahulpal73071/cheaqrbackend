import io
import qrcode
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
)

from .serializers import (
    RegisterSerializer, UserSerializer, UserItemStatusSerializer,
    QRTokenSerializer, AdminScanResolveSerializer, AdminActionSerializer,
    MenuSerializer
)
from .models import QRToken, UserItemStatus, Menu
from .permissions import IsAdmin

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class MyStatusesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            request.user.item_statuses
            .select_related("item")
            .order_by("item__id")
        )
        data = UserItemStatusSerializer(qs, many=True).data
        return Response({"statuses": data})


class MyQRView(APIView):
    """Returns a short-lived QR payload for the current user."""
    permission_classes = [IsAuthenticated]

    def _generate_qr_token(self, user):
        token_obj = QRToken.create_for_user(user)
        payload = f"QR:{token_obj.token}"
        return QRTokenSerializer({
            "data": payload,
            "expires_at": token_obj.expires_at
        }).data

    def post(self, request):
        data = self._generate_qr_token(request.user)
        return Response(data, status=200)

    def get(self, request):
        data = self._generate_qr_token(request.user)
        return Response(data, status=200)


class MyQRPNGView(APIView):
    """Returns a PNG image of the current QR token (will generate/refresh)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token_obj = QRToken.create_for_user(request.user)
        payload = f"QR:{token_obj.token}"
        img = qrcode.make(payload)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        # Use HttpResponse with bytes (not DRF Response) for binary content
        resp = HttpResponse(buf.getvalue(), content_type="image/png")
        resp["Content-Disposition"] = 'inline; filename="qr.png"'
        return resp


class AdminScanResolveView(APIView):
    """
    Admin scans a QR and posts {"qr": "QR:<token>"} to resolve user info + available actions.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        ser = AdminScanResolveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qr = ser.validated_data["qr"]

        if not qr.startswith("QR:"):
            return Response({"detail": "Invalid QR format."}, status=400)

        token = qr.split("QR:", 1)[1].strip()
        try:
            tok = QRToken.objects.select_related("user").get(token=token)
        except QRToken.DoesNotExist:
            return Response({"detail": "QR token not found."}, status=404)

        if not tok.is_valid():
            return Response({"detail": "QR token expired."}, status=410)

        user = tok.user
        statuses = (
            UserItemStatus.objects
            .filter(user=user)
            .select_related("item")
            .order_by("item__id")
        )

        return Response({
            "user": UserSerializer(user).data,
            "statuses": UserItemStatusSerializer(statuses, many=True).data,
            "qr_expires_at": tok.expires_at
        }, status=200)


class AdminScanActionView(APIView):
    """
    Admin performs an action after scanning.
    Body: {"qr":"QR:<token>", "item": <menu_id or name>, "status":"taken|wait|not_taken"}
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def _resolve_menu(self, item_value):
        """
        Accepts:
          - int/str id -> fetch by pk
          - str name   -> fallback to unique name
        Returns Menu instance or None.
        """
        # If already a Menu instance
        if isinstance(item_value, Menu):
            return item_value

        # Try by primary key
        try:
            pk = int(item_value)
            menu = Menu.objects.filter(pk=pk).first()
            if menu:
                return menu
        except (TypeError, ValueError):
            pass

        # Fallback: try by unique name (optional; comment out if names aren't unique)
        if isinstance(item_value, str):
            return Menu.objects.filter(name=item_value).first()

        return None

    @transaction.atomic
    def post(self, request):
        ser = AdminActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        qr = ser.validated_data["qr"]
        item_value = ser.validated_data["item"]
        new_status = ser.validated_data["status"]

        if not qr.startswith("QR:"):
            return Response({"detail": "Invalid QR format."}, status=400)

        token = qr.split("QR:", 1)[1].strip()
        try:
            tok = QRToken.objects.select_related("user").get(token=token)
        except QRToken.DoesNotExist:
            return Response({"detail": "QR token not found."}, status=404)

        if not tok.is_valid():
            return Response({"detail": "QR token expired."}, status=410)

        # Resolve Menu instance safely
        menu = self._resolve_menu(item_value)
        if not menu:
            return Response(
                {"detail": "Menu item not found.", "item": item_value},
                status=400
            )

        user = tok.user

        # Ensure we store a proper FK instance, not a raw id
        status_obj, _ = UserItemStatus.objects.get_or_create(user=user, item=menu)
        status_obj.status = new_status
        # If you have an auto-updated field, updated_at may be auto_now=True; otherwise:
        status_obj.save(update_fields=["status", "updated_at"])

        statuses = (
            UserItemStatus.objects
            .filter(user=user)
            .select_related("item")
            .order_by("item__id")
        )

        return Response({
            "user": UserSerializer(user).data,
            "updated": {"item": menu.id, "item_name": menu.name, "status": new_status},
            "statuses": UserItemStatusSerializer(statuses, many=True).data,
            "timestamp": timezone.now()
        }, status=200)


# ✅ Menu CRUD
class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all().order_by("-created_at")
    serializer_class = MenuSerializer

    def get_permissions(self):
        # Read: anyone (or keep IsAuthenticatedOrReadOnly if you want only authed reads)
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticatedOrReadOnly()]
        # Writes: must be authenticated and admin
        return [IsAuthenticated(), IsAdmin()]
