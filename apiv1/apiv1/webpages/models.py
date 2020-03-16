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
