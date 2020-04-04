"""
__init__.py
Modifications Copyright (C) 2020  Rigved Rakshit

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.settings import SettingsMetaUploader
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
import os
import requests


class WebpageSummarizer(MycroftSkill):
    """
    Skill to read out summaries of the provided web pages.
    """
    def __init__(self):
        """
        Set all the required configuration for the Summarization
        micro-service.
        """
        MycroftSkill.__init__(self)
        self.log.debug('__init__() started after call to super()')
        # Configuration for the Summarization micro-service
        self.api_endpoint_webpages = 'https://localhost:65443/v1/webpages/'
        self.api_endpoint_pastebin = 'https://localhost:65443/v1/paste/'
        self.api_endpoint_pastebin_read_only = 'http://mycroftai.shieldofachilles.in:65080/v1/paste/'
        self.summarization_micro_service_path = os.path.abspath('/opt/webpage_summarizer_service')
        self.api_token_path = os.path.join(self.summarization_micro_service_path, 'apiv1/secrets/api.token')
        self.root_ca_cert_path = os.path.join(self.summarization_micro_service_path, 'apiv1/secrets/rootCA.crt')
        self.headers = None
        # Stop speaking when the user says so
        self.stop_speaking = False
        # Keep track of which web pages have been summarized out loud and
        # delete those entries from the Summarization micro-service queue.
        self.webpage_data_to_delete_after_reading = set()
        self.log.debug('__init__() completed')

    def initialize(self):
        """
        Handle changes in settings and inform the user once the skill has been
        setup and installed for the first time.
        """
        self.log.debug('initialize() started')
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()
        self.log.debug('initialize() completed')

    def on_settings_changed(self):
        """
        Sets the Django superuser password and API token. Also, creates the
        self-signed SSL certificates for use by the Daphne ASGI application
        server. Start or restart the Daphne ASGI application server using
        the new certificates.
        """
        self.log.debug('on_settings_changed() started')
        # Check if setting values are loaded
        if self.headers is None:
            # Load the API token
            if os.path.isfile(self.api_token_path):
                with open(self.api_token_path, 'r') as f:
                    self.settings['api_token'] = f.read().strip()
                # Use this API token for all future communication with the Summarization micro-service
                self.headers = {'Authorization': 'Token {}'.format(self.settings.get('api_token'))}
                self.log.debug('API token loaded successfully.')
            else:
                self.log.error('API token doesn\'t exist! Generate an API token before using this skill.')
                return
            # Load the Root CA certificate
            if os.path.isfile(self.root_ca_cert_path):
                with open(self.root_ca_cert_path, 'r') as f:
                    root_ca = f.read().strip()
                try:
                    response = requests.post(
                        self.api_endpoint_pastebin,
                        headers=self.headers,
                        verify=self.root_ca_cert_path,
                        data={'paste_data': root_ca}
                    )
                    if response.ok:
                        self.log.debug('New Root CA certificate successfully added to pastebin.')
                        paste_id = response.json().get('url').split('/')[-2]
                        self.settings['root_ca'] = self.api_endpoint_pastebin_read_only + paste_id + '/'
                        self.log.debug('New Root CA loaded successfully.')
                        # Delete the previously generated Root CA certificate, if any
                        if int(paste_id) > 1:
                            response = requests.delete(
                                self.api_endpoint_pastebin + str(int(paste_id) - 1) + '/',
                                headers=self.headers,
                                verify=self.root_ca_cert_path)
                            if response.ok:
                                self.log.debug('Old Root CA certificate deleted successfully.')
                            else:
                                self.log.error('Unable to delete the old Root CA certificate!')
                    else:
                        self.log.error('''Unable to add the Root CA certificate to the pastebin!
                                        A working Pastebin micro-service is required before using this skill.''')
                        return
                except Exception as e:
                    self.log.exception('Unable to share the self-signed Root CA certificate \
                                       due to an exception -\n{}'.format(
                        e
                    ))
            else:
                self.log.error('''Root CA Certificate doesn\'t exist!
                               Generate a Root CA certificate before using this skill.''')
                return
        # Sync setting values to the Selene Web UI after 60 seconds
        # because settings are loaded after skill initialization has been completed.
        self.schedule_event(handler=self.upload_settings, when=60, name='Sync Settings')
        self.log.debug('Setting values will be synced after 60 seconds.')
        self.log.debug('on_settings_changed() completed')

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        """
        Fetch summaries from the Summarization micro-service and reads them
        out loud.
        :param message: The voice command issued by the user.
        """
        self.log.debug('handle_summarizer_webpage() started')
        try:
            self.stop_speaking = False
            # API end-point URL keeps changing as we process the data.
            url = self.api_endpoint_webpages
            # API supports pagination. So, determine if more pages need to be
            # processed.
            pending_pages = True
            # Speak this dialog only for the first summary being read. Gives a
            # more natural feel to the conversation.
            first_dialog = True
            # Iterate through the summaries
            while pending_pages:
                if os.path.isfile(self.root_ca_cert_path):
                    response = requests.get(
                        url,
                        headers=self.headers,
                        verify=self.root_ca_cert_path)
                    if response.ok:
                        response_json = response.json()
                        if response_json.get('next', None) is None:
                            pending_pages = False
                            self.log.debug('Found last page of summaries to read')
                        else:
                            url = response_json.get('next')
                        # Read pending summaries
                        if len(response_json.get('results', list())) > 0:
                            for webpage_data in response_json.get('results'):
                                self.log.debug('Found summaries to read')
                                if first_dialog:
                                    first_dialog = False
                                    self.speak_dialog('summarizer.webpage', wait=True)
                                    self.speak('''The first web page title is
                                               {}'''.format(
                                                   webpage_data.get('webpage_title', '')),
                                        wait=True)
                                else:
                                    self.speak('''The next web page title is
                                               {}'''.format(
                                                   webpage_data.get('webpage_title', '')),
                                        wait=True)
                                # Read out the summary of the web page.
                                self.speak('And the summary is as follows.', wait=True)
                                for sentence in webpage_data.get('webpage_summary', '').split('. '):
                                    if self.stop_speaking:
                                        self.acknowledge()
                                        pending_pages = False
                                        break
                                    wait_while_speaking()
                                    self.speak(sentence, wait=True)
                                if not self.stop_speaking:
                                    self.log.debug('Successfully read the summary for {} .'.format(webpage_data.get('url')))
                                    self.webpage_data_to_delete_after_reading.add(webpage_data.get('url'))
                                    should_continue = self.ask_yesno('Should I read the next summary?')
                                    # Continue in case there's no response or the response is a 'yes'
                                    if should_continue is not None and should_continue != 'yes':
                                        self.acknowledge()
                                        pending_pages = False
                                        self.stop_speaking = True
                                    if not pending_pages:
                                        # Signal the end of the current queue to the user
                                        self.speak('I have finished reading all the summaries from the queue.', wait=True)
                                        self.log.debug('Finished reading all summaries.')
                                else:
                                    break
                        else:
                            self.speak('''There are no more summaries to read!
                                       Give me some more web pages and I'll generate summaries out of them.''',
                                       wait=True)
                            self.log.debug('There are no pending summaries.')
                    else:
                        self.log.error('Unable to fetch summaries')
                        return
                else:
                    self.log.error('''Root CA Certificate doesn\'t exist!
                                   Generate a Root CA certificate before using this skill.''')
                    return
            self.delete_data_after_reading()
        except Exception as e:
            self.log.exception('Unable to work with the Daphne application server(s) \
                               due to an exception -\n{}'.format(
                e
            ))
        self.log.debug('handle_summarizer_webpage() completed')

    def stop(self):
        """
        Stop speaking and delete summaries from the micro-service queue which have already been read out aloud.
        We need to do this because Mycroft may have been interrupted while it was processing the summary queue.
        """
        self.log.debug('stop() started')
        self.stop_speaking = True
        self.delete_data_after_reading()
        self.log.debug('stop() completed')

    def upload_settings(self):
        """
        Upload new setting values to the Selene Web UI.
        """
        self.log.debug('upload_settings() started')
        try:
            settings_uploader = SettingsMetaUploader(
                self.root_dir,
                self.name
            )
            settings_uploader.api = DeviceApi()
            settings_uploader._load_settings_meta_file()
            settings_uploader._update_settings_meta()
            settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][1]['value'] = self.settings.get('api_token', '')
            settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][3]['value'] = self.settings.get('root_ca', '')
            settings_uploader._issue_api_call()
            self.log.debug('Setting values successfully synced to the Selene Web UI.')
            self.cancel_scheduled_event(name='Sync Settings')
        except Exception as e:
            self.log.exception('Unable to sync settings to the Selene Web UI \
                                due to an exception -\n{}'.format(
                e
            ))
        self.log.debug('upload_settings() completed')

    def delete_data_after_reading(self):
        """
        Convenience function to delete summaries which have already been read
        out aloud. We do not want to re-read any summaries that were read
        out loud earlier. We need to do this because Mycroft may have been
        interrupted while it was processing the queue.
        """
        self.log.debug('delete_data_after_reading() started')
        try:
            deletion_list = self.webpage_data_to_delete_after_reading.copy()
            for url in deletion_list:
                response = requests.delete(
                    url,
                    headers=self.headers,
                    verify=self.root_ca_cert_path)
                if response.ok:
                    self.webpage_data_to_delete_after_reading.remove(url)
                    self.log.debug('''Successfully deleted the archived summary \
                                    for the URL: {}'''.format(
                        url
                    ))
                else:
                    self.log.error('''Error while deleting the archived summary \
                                    for the URL: {}'''.format(
                        url
                    ))
                    return
            self.log.debug('Cleared all archived summaries from queue')
        except Exception as e:
            self.log.exception('Unable to clear the queue of archived summaries \
                               due to an exception -\n{}'.format(
                e
            ))
        self.log.debug('delete_data_after_reading() completed')

    def get_intro_message(self):
        """
        Provide post-install instructions to the user.
        :return: Post-install message that will be read out loud.
        """
        self.log.debug('get_intro_message() started')
        message = '''Visit the Mycroft AI Skills page for the Webpage Summarization Skill
                    to save the API Token and the SSL Certificate. You will need these two settings
                    to allow other applications to send web pages to me over a secure channel.
                    Then, you can ask me to read out the summaries of these web pages by saying:
                    Hey Mycroft, read web page summary.
                    Or hey Mycroft, read web page summaries.
                    Or hey Mycroft, read summary.
                    Or hey Mycroft, read summaries.'''
        self.log.debug('get_intro_message() completed')
        return message


def create_skill():
    """
    Entry-point for loading this skill by the Mycroft AI Skill Loader.
    :return: An instance of WebpageSummarizer class
    """
    return WebpageSummarizer()

