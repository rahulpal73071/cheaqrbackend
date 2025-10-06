from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # ==== Auth ====
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ==== User ====
    path('user/me/', views.MeView.as_view(), name='me'),
    path('user/statuses/', views.MyStatusesView.as_view(), name='my_statuses'),

    # ==== QR ====
    path('user/qr/', views.MyQRView.as_view(), name='my_qr'),
    path('user/qr.png', views.MyQRPNGView.as_view(), name='my_qr_png'),

    # ==== Admin ====
    path('admin/scan/resolve/', views.AdminScanResolveView.as_view(), name='admin_scan_resolve'),
    path('admin/scan/action/', views.AdminScanActionView.as_view(), name='admin_scan_action'),

    # ==== Menu ====
    path(
        'menu/',
        views.MenuViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='menu_list'
    ),
    path(
        'menu/<int:pk>/',
        views.MenuViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='menu_detail'
    ),
]
