from mycroft import MycroftSkill, intent_file_handler

import os.path
import sqlite3
import mechanicalsoup
from gensim.summarization.summarizer import summarize


class WebpageSummarizer(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.browser = mechanicalsoup.StatefulBrowser(user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0')
        self.db = 'webpage_summary.db'
        self.table = 'webpage_summary'
        if not os.path.isfile(self.db):
            conn = sqlite3.connect(self.db)
            with conn:
                c = conn.cursor()
                c.execute('CREATE TABLE ? (url text, title text, summary text);', (self.table,))
                conn.commit()
                self.log.debug('Created database to store titles and summaries of URLs.')

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()
        self.summarize_webpages()

    def on_settings_changed(self):
        self.summarization_ratio = self.settings.get('summarization_ratio', 0.2)
        if self.summarization_ratio <= 0.0 or self.summarization_ratio >= 1.0:
            self.settings['summarization_ratio'] = self.summarization_ratio = 0.2
            self.log.warning('Invalid summarization ratio was set. This has been reset to the default value.')

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        conn = sqlite3.connect(self.db)
        with conn:
            c = conn.cursor()

            # Read out all the summaries in the queue and clear them out
            c.execute('SELECT * FROM ? WHERE summary IS NOT ?;', (self.table, None))
            data_to_speak = c.fetchall()
            if len(data_to_speak) > 0:
                for row in data_to_speak:
                    self.speak_dialog('summarizer.webpage')
                    self.speak('Web page title is {}'.format(row[1]))
                    self.speak('And the summary is as follows. {}'.format(row[2]))
                    c.execute('DELETE from ? where url = ?;', (self.table, row[0]))
                    conn.commit()
            else:
                self.speak('No more summaries available.')

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
            summarized_text = summarize(website_text, ratio=self.summarization_ratio).strip()
            self.log.debug('\n\nURL: {}\nTitle: {}\nSummary: {}\n\n'.format(url, title, summarized_text))
        except Exception as e:
            self.log.exception('Couldn\'t parse URL: {}.'.format(url))
        finally:
            self.browser.close()

        return title, summarized_text

    def summarize_webpages(self):
        conn = sqlite3.connect(self.db)
        with conn:
            c = conn.cursor()

            # Find summaries for all URLs in queue
            c.execute('SELECT url FROM ? WHERE summary IS ?;', (self.table, None))
            data_to_summarize = c.fetchall()
            if len(data_to_summarize > 0):
                for row in data_to_summarize:
                    url = row[0].strip()
                    title = summarized_web_text = ''
                    try:
                        title, summarized_web_text = self.summarize_webpage(url)
                        if title == '' or summarized_web_text == '':
                            self.log.error('Couldn\'t fetch title or summary for the given URL: {}'.format(url))
                            continue
                        # Replace all '|' symbols before saving to the SQLite database
                        title = title.replace('|', ',')
                        summarized_web_text = summarized_web_text.replace('|', ',')
                        c.execute('UPDATE ? SET title = ?, summary = ? WHERE url = ?;', (self.table, title, summarized_web_text, url))
                        conn.commit()
                    except Exception as e:
                        self.log.exception('Couldn\'t parse URL: {}.'.format(url))
                        continue
            else:
                self.log.debug('No pending URLs to summarize.')


def create_skill():
    return WebpageSummarizer()

