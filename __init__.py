from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.settings import save_settings
import os
import requests
import subprocess


class WebpageSummarizer(MycroftSkill):
    """
    Skill to read out summaries of the provided web pages.
    """
    def __init__(self):
        MycroftSkill.__init__(self)
        self.folder = os.path.dirname(os.path.realpath(__file__))
        # Setup Django project and app
        if not os.path.isfile(os.path.join(self.folder, 'apiv1/db.sqlite3')):
            subprocess.run([
                os.path.join(
                    self.folder,
                    'scripts/create_database_and_superuser.sh'
                )
            ])

    def initialize(self):
        """
        Set all the required configuration and start the Summarization
        micro-service.
        """
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()
        # Keep track of which web pages have been summarized out loud and
        # delete those entries from the summarization micro-service queue.
        self.webpage_data_to_delete_after_reading = set()
        # Settings to use for the Daphne ASGI application server.
        self.api_endpoint = 'https://localhost:{}/v1/webpages/'.format(port)
        self.headers = {'Authorization': 'Token {}'.format(self.api_token)}
        try:
            # Start the Summarization micro-service in a Daphne ASGI
            # application server.
            self.daphne = subprocess.Popen([
                    os.path.join(
                        self.folder,
                        'scripts/start_daphne.sh'
                    )
                ]
            )
            self.log.info('Daphne started successfully in the background.')
        except Exception as e:
            self.speak('''Error! The summarization micro-service failed to
                       start.''')
            self.log.exception('Daphne failed to start.')
        self.speak('''The Mycroft AI Webpage Summarization skill
                   has been successfully installed and setup!''')

    def on_settings_changed(self):
        """
        Sets the Django superuser password and API token. Also, creates the
        self-signed SSL certificates for use by the Daphne ASGI application
        server.
        """
        # Generate an API token to authenticate with the Summarization
        # micro-service.
        self.api_token = self.settings.get('api_token', '')
        if self.api_token == '':
            self.settings['api_token'] = self.api_token = subprocess.run([
                os.path.join(
                    self.folder,
                    'scripts/update_password_and_token.sh'
                ),
                '|',
                'grep',
                'Generated token ',
                '|',
                'awk',
                '{print $3}'],
                capture_output=True).stdout.strip().decode('UTF-8')
            self.log.info('New API token generated successfully.')
        # Generate self-signed certificates to connect with the Summarization
        # micro-service over an encrypted TLS connection using HTTP/2. The
        # self-signed Root CA certificate is used by remote applications to
        # verify the authenticity of the self-signed certificate used by
        # the Daphne web application server.
        self.root_ca = self.settings.get('root_ca', '')
        if self.root_ca == '':
            root_ca_cert = os.path.join(
                self.folder,
                'apiv1/secrets/rootCA.crt'
            )
            subprocess.run([os.path.join(
                    self.folder,
                    'scripts/update_certificates.sh'
                )
            ])
            if os.path.isfile(root_ca_cert):
                with open(root_ca_cert, 'r') as f:
                    self.settings['root_ca'] = self.root_ca = f.read().strip()
            self.log.info('New certificates generated successfully.')
        save_settings(self.root_dir, self.settings)

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        """
        Fetch summaries from the Summarization micro-service and reads them
        out loud.
        :param message: The voice command issued by the user.
        """
        try:
            # API end-point URL keeps changing as we process the data.
            url = self.api_endpoint
            # API supports pagination. So, determine if more pages need to be
            # processed.
            pending_pages = True
            # Speak this dialog only for the first summary being read. Gives a
            # more natural feel to the conversation.
            first_dialog = True
            # Iterate through the summaries
            while pending_pages:
                request = requests.get(
                    url,
                    headers=self.headers,
                    verify=self.root_ca)
                if request.ok:
                    request_json = request.json()
                    if request_json['next'] == '':
                        pending_pages = False
                    else:
                        url = request_json['next']
                    for webpage_data in request_json['results']:
                        # Show the web page title on the Mycroft 1 mouth while
                        # the long summary is being read out aloud.
                        self.enclosure.mouth_text(webpage_data['webpage_title'])
                        if first_dialog:
                            first_dialog = False
                            self.speak_dialog('summarizer.webpage')
                            self.speak('''The first web page title is
                                       {}'''.format(
                                           request_json['webpage_title']))
                        else:
                            self.speak('''The next web page title is
                                       {}'''.format(
                                           request_json['webpage_title']))
                        # Read out the summary of the web page.
                        self.speak('''And the summary is as follows.
                                   {}'''.format(
                                       request_json['webpage_summary']))
                        self.webpage_data_to_delete_after_reading.add(request_json['url'])
            self.delete_data_after_reading()
            # Signal the end of the current queue to the user
            self.enclosure.mouth_text('No more summaries available.')
            self.speak('There are no more summaries available.')
            self.enclosure.reset()
        except Exception as e:
            self.enclosure.mouth_text('Error')
            self.speak('''There was an error. Is the summarization
                       micro-service working?''')
            self.enclosure.reset()
            self.log.exception('''Error while working with the
                               summarization micro-service.''')

    def stop(self):
        """
        Delete summaries from the micro-service queue which have already been
        read out aloud. We do not want to re-read any summaries that were read
        out loud earlier. We need to do this because Mycroft may have been
        interrupted while it was processing the queue.
        """
        if hasattr(self, 'delete_data_after_reading'):
            self.delete_data_after_reading()

    def shutdown(self):
        """
        Stop the Summarization micro-service cleanly before shutting down. This
        allows any pending transactions to be completed.
        """
        if hasattr(self, 'daphne'):
            self.daphne.terminate()

    def delete_data_after_reading(self):
        """
        Convenience function to delete summaries which have already been read
        out aloud. We do not want to re-read any summaries that were read
        out loud earlier. We need to do this because Mycroft may have been
        interrupted while it was processing the queue.
        """
        try:
            deletion_list = self.webpage_data_to_delete_after_reading.copy()
            for url in deletion_list:
                request = requests.delete(
                    url,
                    headers=self.headers,
                    verify=self.root_ca)
                self.webpage_data_to_delete_after_reading.remove(url)
            self.log.info('Cleared summaries from queue.')
        except Exception as e:
            self.log.exception('''Error while clearing the queue. Is the
                               summarization micro-service working?''')


def create_skill():
    return WebpageSummarizer()

