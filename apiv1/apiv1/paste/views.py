"""
views.py
Modifications Copyright (C) 2020  Rigved Rakshit

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


from rest_framework import viewsets
from rest_framework import permissions
from apiv1.webpages.models import Paste
from apiv1.webpages.serializers import PasteSerializer


class PasteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows viewing pastebin data that can be shared.
    """
    queryset = Paste.objects.all()
    serializer_class = PasteSerializer
    permission_classes = [permissions.AllowAny]
