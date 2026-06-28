from django.urls import path
from .views import user_login, user_logout, admin_dashboard, user_dashboard, add_user, update_user, delete_user, update_user_profile, mirror_preview, reset_password, request_otp, verify_otp, generate_qr, qr_login_action, qr_login_page, qr_scan_login, qr_check_status, phone_login_complete, mirror_feed_api, terms_and_conditions
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('dashboard/', admin_dashboard, name='dashboard'),
    path('user_dashboard/', user_dashboard, name='user_dashboard'),
    path('add_user/', add_user, name='add_user'),
    path('update_user/<int:user_id>/', update_user, name='update_user'),
    path('delete_user/<int:user_id>/', delete_user, name='delete_user'),
    path('update_profile/', update_user_profile, name='update_user_profile'),
    path('mirror_preview/', mirror_preview, name='mirror_preview'),
    path('request-otp/', request_otp, name='request_otp'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('reset-password/', reset_password, name='reset_password'),
    path('qr/', generate_qr, name='generate_qr'),
    path('qr-login/', qr_login_page, name='qr_login_page'),
    path('qr-scan-login/', qr_scan_login, name='qr_scan_login'),
    path('phone-login-complete/', phone_login_complete, name='phone_login_complete'),
    path('qr-check-status/', qr_check_status, name='qr_check_status'),
    path('api/mirror-feed/', mirror_feed_api, name='mirror_feed_api'),
    path('terms-and-conditions/', terms_and_conditions, name='terms_and_conditions'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
