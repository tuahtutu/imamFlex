from django.conf import settings
from django.conf.urls.static import static
import os

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Manual serve untuk folder luar
    urlpatterns += static('/profile_pics/', document_root=os.path.join(settings.BASE_DIR, 'profile_pics'))
    urlpatterns += static('/leave_docs/', document_root=os.path.join(settings.BASE_DIR, 'leave_docs'))
