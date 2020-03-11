from mycroft import MycroftSkill, intent_file_handler

import os.path
import sqlite3
import mechanicalsoup
from gensim.summarization.summarizer import summarize


class WebpageSummarizer(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.browser = mechanicalsoup.StatefulBrowser(
            user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0')
        self.db = 'webpage_summary.db'
        self.table = 'webpage_summary'
        if not os.path.isfile(self.db):
            conn = sqlite3.connect(self.db)
            with conn:
                c = conn.cursor()
                c.execute('CREATE TABLE ? (url text, title text, summary text);', (self.table,))
                conn.commit()
                self.log.debug('Created database to store titles and summaries of URLs')

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        self.speak_dialog('summarizer.webpage')

    def summarize_webpage(self, url):
        """
        Takes a website URL and returns the URL title and a summary of the website content.
        :param url: Website URL.
        :return: Website title and summarized website text.
        """
        title = summarized_text = ''
        try:
            self.browser.open(url)
            page = self.browser.get_current_page()
            website_text = ' '.join(map(lambda p: p.text, page.find_all('p')))
            title = page.title.text.strip()
            summarized_text = summarize(website_text).strip()
            self.log.debug('\n\nURL: {}\nTitle: {}\nSummary: {}\n\n'.format(url, title, summarized_text))
        except Exception as e:
            self.log.exception(e)
        finally:
            self.browser.close()

        return title, summarized_text


def create_skill():
    return WebpageSummarizer()

