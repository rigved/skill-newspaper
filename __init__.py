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
from mycroft.api import DeviceApi, is_paired
import os
import time
import requests
import subprocess


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
        # Setup Django project and app
        if not os.path.isfile(os.path.join(self.root_dir, 'apiv1/db.sqlite3')):
            subprocess.run([
                os.path.join(
                    self.root_dir,
                    'scripts/create_database_and_superuser.sh'
                )
            ])
        # Configuration for the Summarization micro-service
        self.api_endpoint_webpages = 'https://localhost:65443/v1/webpages/'
        self.api_endpoint_pastebin = 'https://localhost:65443/v1/paste/'
        self.api_endpoint_pastebin_read_only = 'http://mycroftai.shieldofachilles.in:65080/v1/paste/'
        self.api_token_path = os.path.join(self.root_dir, 'apiv1/secrets/api.token')
        self.root_ca_cert_path = os.path.join(self.root_dir, 'apiv1/secrets/rootCA.crt')
        self.headers = {}
        # Keep track of which web pages have been summarized out loud and
        # delete those entries from the Summarization micro-service queue.
        self.webpage_data_to_delete_after_reading = set()
        # Keep track of when first run things need to be performed
        self.first_run = True

    def initialize(self):
        """
        Handle changes in settings and inform the user once the skill has been
        setup and installed for the first time.
        """
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()
        # Inform the user when the installation completes
        if self.first_run:
            self.first_run = False
            self.speak('''The Mycroft AI Webpage Summarization skill
                       has been successfully installed and setup!''')

    def on_settings_changed(self):
        """
        Sets the Django superuser password and API token. Also, creates the
        self-signed SSL certificates for use by the Daphne ASGI application
        server. Start or restart the Daphne ASGI application server using
        the new certificates.
        """
        # Keep track of whether settings have changed locally
        settings_changed = {'api_token': False, 'root_ca': False}
        if self.settings.get('api_token_reset', True):
            # Generate a new API token to authenticate with the
            # Summarization micro-service.
            result = subprocess.run([
                os.path.join(
                    self.root_dir,
                    'scripts/update_password_and_token.sh'
                )
            ]
            )
            if result.returncode == 0:
                self.log.info('New API token generated successfully.')
                self.settings['api_token_reset'] = False
                settings_changed['api_token'] = True
            else:
                self.log.error('Unable to generate API token.')
                self.speak('''Error! Failed to generate an API token
                            for the Summarization micro-service.''')
        if self.settings.get('root_ca_reset', True):
            # Generate self-signed certificates to connect with the Summarization
            # micro-service over an encrypted TLS connection using HTTP/2. The
            # self-signed Root CA certificate is used by remote applications
            # to verify the authenticity of the self-signed certificate
            # used by the Summarization micro-service application server.
            result = subprocess.run([os.path.join(
                    self.root_dir,
                    'scripts/update_certificates.sh'
                )
            ])
            if result.returncode == 0:
                self.log.info('New certificates generated successfully.')
                self.settings['root_ca_reset'] = False
                settings_changed['root_ca'] = True
            else:
                self.log.error('Unable to generate self-signed certificates.')
                self.speak('''Error! Failed to generate self-signed certificates
                            for the Summarization micro-service.''')
        # Start or restart the Summarization micro-service application server
        # using the new certificates.
        try:
            # Stop the Summarization micro-service in case it is running
            self.shutdown_daphne()
            # Start the Summarization and Pastebin micro-services in Daphne ASGI
            # application servers.
            self.daphne = subprocess.Popen([
                os.path.join(
                    self.root_dir,
                    'scripts/start_daphne.sh'
                )
            ]
            )
            self.daphne_ssl = subprocess.Popen([
                os.path.join(
                    self.root_dir,
                    'scripts/start_daphne_over_tls.sh'
                )
            ]
            )
            # Wait for the Summarization and Pastebin micro-services to finish booting up
            time.sleep(30)
            self.log.info('Daphne started successfully in the background.')
        except Exception as e:
            self.speak('''Error! The summarization micro-service failed to
                       start.''')
            self.log.exception('Daphne failed to start.')
        if settings_changed.get('api_token', False):
            # Update settings to the new API token
            if os.path.isfile(self.api_token_path):
                with open(self.api_token_path, 'r') as f:
                    self.settings['api_token'] = f.read().strip()
                # Use this new API token for all future communication with
                # the Summarization micro-service.
                self.headers = {'Authorization': 'Token {}'.format(self.settings.get('api_token'))}
        if settings_changed.get('root_ca', False):
            # Update settings to the new Root CA certificate
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
                        paste_id = response.json().get('url').split('/')[-2]
                        self.settings['root_ca'] = self.api_endpoint_pastebin_read_only + paste_id + '/'
                        # Delete the previously generated Root CA certificate, if any
                        if int(paste_id) > 1:
                            response = requests.delete(
                                self.api_endpoint_pastebin + str(int(paste_id) - 1) + '/',
                                headers=self.headers,
                                verify=self.root_ca_cert_path)
                except Exception as e:
                    self.log.error('Unable to share the self-signed Root CA certificate.')
                    self.speak('''Error! Failed to share the self-signed Root CA certificate
                                for the Summarization micro-service.''')
        if settings_changed.get('api_token', False) or settings_changed.get('root_ca', False):
            # Upload new setting values to the Selene Web UI
            self.upload_settings()

    @intent_file_handler('summarizer.webpage.intent')
    def handle_summarizer_webpage(self, message):
        """
        Fetch summaries from the Summarization micro-service and reads them
        out loud.
        :param message: The voice command issued by the user.
        """
        try:
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
                        if response_json.get('next', '') == '':
                            pending_pages = False
                        else:
                            url = response_json.get('next')
                        for webpage_data in response_json.get('results', list()):
                            # Show the web page title on the Mycroft 1 mouth while
                            # the long summary is being read out aloud.
                            self.enclosure.mouth_text(webpage_data.get('webpage_title', ''))
                            if first_dialog:
                                first_dialog = False
                                self.speak_dialog('summarizer.webpage')
                                self.speak('''The first web page title is
                                           {}'''.format(
                                               webpage_data.get('webpage_title', '')))
                            else:
                                self.speak('''The next web page title is
                                           {}'''.format(
                                               webpage_data.get('webpage_title', '')))
                            # Read out the summary of the web page.
                            self.speak('''And the summary is as follows.
                                       {}'''.format(
                                           webpage_data.get('webpage_summary', '')))
                            self.webpage_data_to_delete_after_reading.add(webpage_data.get('url'))
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
        self.delete_data_after_reading()

    def shutdown(self):
        """
        Stop the Summarization micro-service cleanly before shutting down. This
        allows any pending transactions to be completed.
        """
        self.shutdown_daphne()

    def upload_settings(self):
        """
        Upload new setting values to the Selene Web UI.
        """
        try:
            settings_uploader = SettingsMetaUploader(
                self.root_dir,
                self.name
            )
            if is_paired():
                settings_uploader.api = DeviceApi()
                if settings_uploader.api.identity.uuid and settings_uploader.yaml_path.is_file():
                    settings_uploader._load_settings_meta_file()
                    settings_uploader._update_settings_meta()
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][1]['value'] = self.settings.get('api_token', '')
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][4]['value'] = self.settings.get('root_ca', '')
                    settings_uploader._issue_api_call()
                    self.log.info('''New setting values uploaded successfully
                                    to the Selene Web UI.''')
        except Exception as e:
            self.log.exception('''Error while uploading settings
                                to the Selene Web UI.''')

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
                response = requests.delete(
                    url,
                    headers=self.headers,
                    verify=self.root_ca_cert_path)
                if response.ok:
                    self.webpage_data_to_delete_after_reading.remove(url)
            self.log.info('Cleared summaries from queue.')
        except Exception as e:
            self.log.exception('''Error while clearing the queue. Is the
                               summarization micro-service working?''')

    def shutdown_daphne(self):
        """
        Cleanly stop the Daphne ASGI application server.
        """
        if hasattr(self, 'daphne'):
            try:
                self.daphne.terminate()
                self.log.info('Daphne stopped successfully.')
            except Exception as e:
                self.log.exception('Error while shutting down the Daphne application server.')
        if hasattr(self, 'daphne_ssl'):
            try:
                self.daphne_ssl.terminate()
                self.log.info('Daphne-over-TLS stopped successfully.')
            except Exception as e:
                self.log.exception('Error while shutting down the Daphne-over-TLS application server.')


def create_skill():
    return WebpageSummarizer()

