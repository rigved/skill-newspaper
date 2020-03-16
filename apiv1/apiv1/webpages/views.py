from rest_framework import viewsets
from rest_framework import permissions
from .models import Webpage
from .serializers import WebpageSerializer


class WebpageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows adding new webpage URLs to the queue, summarizing
    webpages, and retrieving all the webpage summaries in the queue.
    """
    queryset = Webpage.objects.all()
    serializer_class = WebpageSerializer
    permission_classes = [permissions.IsAuthenticated]
