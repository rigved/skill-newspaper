from mycroft import MycroftSkill, intent_file_handler

import mechanicalsoup
from gensim.summarization.summarizer import summarize


class WebpageSummarizer(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.browser = mechanicalsoup.StatefulBrowser(
            user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0')

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        self.speak_dialog('summarizer.webpage')

    def get_summary(self, url):
        """
        Takes a website URL and returns the URL title and a summary of the website content.
        :param url: Website URL.
        :return: Website title and summarized website text.
        """
        try:
            self.browser.open(url)
            page = self.browser.get_current_page()
            website_text = ' '.join(map(lambda p: p.text, page.find_all('p')))
            summarized_text = summarize(website_text)
            self.browser.close()
            return page.title.text, summarized_text
        except Exception as e:
            pass


def create_skill():
    return WebpageSummarizer()

