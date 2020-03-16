from django.urls import include, path
from django.conf import settings
from rest_framework import routers
from .webpages.views import WebpageViewSet

router = routers.DefaultRouter()
router.register(r'v1/webpages', WebpageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns.append(path('api-auth/', include('rest_framework.urls', namespace='rest_framework')))
