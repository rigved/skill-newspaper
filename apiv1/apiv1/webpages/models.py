"""
models.py
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


from django.db import models
from django.core.validators import URLValidator


class Webpage(models.Model):
    webpage_url = models.URLField(
        help_text='Specify the URL of the web page to summarize. Only the http and https URI schemes are supported.',
        unique=True,
        verbose_name='Web Page URL',
        validators=[URLValidator(schemes=['http', 'https'])])
    webpage_title = models.TextField(
        blank=True,
        help_text='The extracted title of the web page. Leave this blank as it is auto-generated.',
        verbose_name='Web Page Title')
    webpage_summary = models.TextField(
        blank=True,
        help_text='The extracted summary of the web page. Leave this blank as it is auto-generated.',
        verbose_name='Web Page Summary')

    class Meta:
        ordering = ['id']
