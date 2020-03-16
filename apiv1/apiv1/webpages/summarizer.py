from mechanicalsoup import StatefulBrowser
from gensim.summarization.summarizer import summarize


class WebpageSummarizer(object):
    """
    Generates summary of a given web page.
    """
    def __init__(self):
        self.browser = StatefulBrowser(user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0')
        self.browser.session.headers.update({'Upgrade-Insecure-Requests': '1'})

    def summarize_webpage(self, url, summarization_ratio):
        """
        Takes a web page URL and returns the title and a summary of the web page.
        :param url: Web page URL.
        :param summarization_ratio: Fraction of original text to include in the summary.
        :return: Web page title and summarized web page text.
        """
        title = summarized_text = ''
        try:
            self.browser.open(url)
            page = self.browser.get_current_page()
            # Find all the paragraphs because they contain the main web page text
            page_text = ' '.join(map(lambda p: p.text, page.find_all('p')))
            title = page.title.text.strip()
            # Generate a summary of the given web page text
            summarized_text = summarize(page_text, ratio=summarization_ratio).strip()
        except Exception:
            raise
        finally:
            self.browser.close()

        return title, summarized_text
