from mycroft import MycroftSkill, intent_file_handler


class WebpageSummarizer(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        self.speak_dialog('summarizer.webpage')


def create_skill():
    return WebpageSummarizer()

