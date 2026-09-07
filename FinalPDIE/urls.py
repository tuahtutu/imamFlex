from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ImamFlex.urls')),  # tukar ke root ('') bukan 'ImamFlex/'
]

# Serve fail MEDIA (upload) semasa development sahaja.
# Di production (PythonAnywhere), /media/ diserve terus oleh server web.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
