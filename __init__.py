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
                self.log.debug('Created database to store titles and summaries of URLs')

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        self.speak_dialog('summarizer.webpage')

        conn = sqlite3.connect(self.db)
        with conn:
            c = conn.cursor()

            # Find summaries for all URLs in queue
            c.execute('SELECT url FROM ? WHERE summary IS ?;', (self.table, None))
            for row in c.fetchall():
                url = row[0].strip()
                title = summarized_web_text = ''
                try:
                    title, summarized_web_text = self.summarize_webpage(url)
                    if title == '' or summarized_web_text == '':
                        self.log.error('Couldn\'t fetch title or summary for the given URL: {}'.format(url))
                        self.speak('Couldn not fetch title or summary for the given web page. I will continue to the next web page. Please check the logs for more details.')
                        continue
                    # Replace all | symbols before saving to the SQLite database
                    title = title.replace('|', ',')
                    summarized_web_text = summarized_web_text.replace('|', ',')
                    c.execute('UPDATE ? SET title = ?, summary = ? WHERE url = ?;', (self.table, title, summarized_web_text, url))
                    conn.commit()
                except Exception as e:
                    self.log.exception('Couldn\'t parse URL: {}.'.format(url))
                    self.speak('Couldn not fetch title or summary for the given web page. I will continue to the next web page. Please check the logs for more details.')
                    continue

            # Read out all the summaries in the queue and clear them out
            c.execute('SELECT * FROM ? WHERE summary IS NOT ?;', (self.table, None))
            for row in c.fetchall():
                self.speak('Web page title is {}'.format(row[1]))
                self.speak('And the summary is as follows. {}'.format(row[2]))
                c.execute('DELETE from ? where url = ?;', (self.table, row[0]))
                conn.commit()

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
            self.log.debug('\n\nTitle: {}\nSummary: {}\n\n'.format(title, summarized_text))
        except Exception as e:
            self.log.exception('Couldn\'t parse URL: {}.'.format(url))
        finally:
            self.browser.close()

        return title, summarized_text


def create_skill():
    return WebpageSummarizer()

