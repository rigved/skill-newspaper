# skill-newspaper to read aloud web page contents.
# Copyright (C) 2017  Rigved Rakshit
#
# This file is part of skill-newspaper.
#
# skill-newspaper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# skill-newspaper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with skill-newspaper. If not, see <http://www.gnu.org/licenses/>.

from os.path import dirname
import time

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

import newspaper

__author__ = 'rigved'

LOGGER = getLogger(__name__)

class NewsPaperSkill(MycroftSkill):
    def __init__(self):
        """
        Initialize variables.

        self.url: Stores the URL of the web page to be spoken
        self.article: Object of newspaper.Article class for self.url
        """
        super(NewsPaperSkill, self).__init__(name = 'NewsPaperSkill')

        self.url = None
        self.article = None

    def initialize(self):
        """
        Build all the required intents.

        read_full_text_intent: Read the full text at the given web page.
        read_summary_intent: Read the summary of the given web page.
        """
        read_full_text_intent = IntentBuilder('ReadFullTextIntent'). \
            require('ReadFullTextKeyword').optionally('URL').build()
        self.register_intent(read_full_text_intent, self.handle_read_full_text_intent)

        read_summary_intent = IntentBuilder('ReadSummaryIntent'). \
            require('ReadSummaryKeyword').optionally('URL').build()
        self.register_intent(read_summary_intent, self.handle_read_summary_intent)

    def parse_url(self, message):
        """
        Process the web page at the given URL.
        """
        try:
            self.url = message.data.get('URL', None)
            self.article = newspaper.Article(self.url)
            self.article.download()
            self.article.parse()
        except Exception as e:
            print e

    def handle_read_full_text_intent(self, message):
        """
        Read full text on given web page.
        """
        try:
            self.speak_dialog('reading.full.text')
            self.parse_url(message)
            self.speak_dialog(self.article.text.replace('\\n', ' '))
        except Exception as e:
            self.speak_dialog('error')
            LOGGER.error('Error: {0}'.format(e))

    def handle_read_summary_intent(self, message):
        """
        Read summary of content of the given web page.
        """
        try:
            self.speak_dialog('reading.summary')
            self.parse_url(message)
            self.article.nlp()
            self.speak_dialog(self.article.summary.replace('\\n', ' '))
        except Exception as e:
            self.speak_dialog('error')
            LOGGER.error('Error: {0}'.format(e))

    def stop(self):
        pass

def create_skill():
    return NewsPaperSkill()
