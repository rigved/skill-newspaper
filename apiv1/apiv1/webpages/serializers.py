from rest_framework import serializers
from django.core.validators import URLValidator
from .models import Webpage
import decimal
from .summarizer import WebpageSummarizer


class WebpageSerializer(serializers.HyperlinkedModelSerializer):
    webpage_url = serializers.URLField(
        help_text='Specify the URL of the web page to summarize. Only the http and https URI schemes are supported.',
        label='Web Page URL',
        validators=[
            URLValidator(
                schemes=[
                    'http',
                    'https',
                ]
            )
        ]
    )
    summarization_ratio = serializers.DecimalField(
        max_digits=2,
        decimal_places=2,
        coerce_to_string=True,
        max_value=0.99,
        min_value=0.01,
        rounding=decimal.ROUND_UP,
        help_text='''Fraction (percentage) of the original text that should be part of the summary.
        Enter a number between 0.00 and 1.00, exclusive of these two numbers.''',
        label='Summarization Ratio',
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.summarizer = WebpageSummarizer()

    def create(self, validated_data):
        # Fetch the title and the summary of the given web page
        validated_data['webpage_title'], validated_data['webpage_summary'] = self.summarizer.summarize_webpage(
            url=validated_data.get('webpage_url'),
            summarization_ratio=validated_data.get('summarization_ratio', decimal.Decimal(0.2)))
        # Delete the provided summarization ratio as that is no longer relevant
        validated_data.pop('summarization_ratio')
        return super().create(validated_data=validated_data)

    class Meta:
        model = Webpage
        fields = '__all__'
        read_only_fields = ['webpage_title', 'webpage_summary']
