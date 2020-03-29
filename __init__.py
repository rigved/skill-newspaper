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
        self.log.debug('__init__() started after call to super()')
        # Setup Django project and app
        if not os.path.isfile(os.path.join(self.root_dir, 'apiv1/db.sqlite3')):
            result = subprocess.run([
                os.path.join(
                    self.root_dir,
                    'scripts/create_database_and_superuser.sh'
                )],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log.info('Django setup successfully')
            else:
                self.log.error('Django was not setup because \
                               the subprocess returned error code {} \
                               with error message "{}"'.format(
                    result.returncode,
                    result.stderr
                ))
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
        # Daphne ASGI application servers
        self.daphne = self.daphne_tls = None
        self.log.debug('__init__() completed')

    def initialize(self):
        """
        Handle changes in settings and inform the user once the skill has been
        setup and installed for the first time.
        """
        self.log.debug('initialize() started')
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()
        # Inform the user when the installation completes
        if self.first_run:
            self.first_run = False
            self.speak('''The Mycroft AI Webpage Summarization skill
                       has been successfully installed and setup!''')
            self.log.info('Skill first run completed')
        self.log.debug('initialize() completed')

    def on_settings_changed(self):
        """
        Sets the Django superuser password and API token. Also, creates the
        self-signed SSL certificates for use by the Daphne ASGI application
        server. Start or restart the Daphne ASGI application server using
        the new certificates.
        """
        self.log.debug('on_settings_changed() started')
        # Keep track of whether settings have changed locally
        settings_changed = {'api_token': False, 'root_ca': False}
        if self.settings.get('api_token_reset', True):
            # Generate a new API token to authenticate with the
            # Summarization micro-service.
            self.log.info('API token needs to be (re)set')
            result = subprocess.run([
                os.path.join(
                    self.root_dir,
                    'scripts/update_password_and_token.sh'
                )],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log.info('New API token generated successfully')
                self.settings['api_token_reset'] = False
                settings_changed['api_token'] = True
            else:
                self.log.error('Unable to generate API token \
                    because subprocess returned error code {} \
                    with error message "{}"'.format(
                    result.returncode,
                    result.stderr
                ))
                self.speak('''Error! Failed to generate an API token
                            for the Summarization micro-service.''')
        if self.settings.get('root_ca_reset', True):
            # Generate self-signed certificates to connect with the Summarization
            # micro-service over an encrypted TLS connection using HTTP/2. The
            # self-signed Root CA certificate is used by remote applications
            # to verify the authenticity of the self-signed certificate
            # used by the Summarization micro-service application server.
            self.log.info('Self-signed certificates need be to (re-)generated')
            result = subprocess.run([os.path.join(
                    self.root_dir,
                    'scripts/update_certificates.sh'
                )],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log.info('New certificates generated successfully')
                self.settings['root_ca_reset'] = False
                settings_changed['root_ca'] = True
            else:
                self.log.error('Unable to generate self-signed certificates \
                               because subprocess returned error code {}\
                               with error message "{}"'.format(
                    result.returncode,
                    result.stderr
                ))
                self.speak('''Error! Failed to generate self-signed certificates
                            for the Summarization micro-service.''')
        # Start or restart the Summarization micro-service application server
        # using the new certificates.
        self.log.info('Restarting Daphne ASGI application servers')
        try:
            # Stop the Summarization and Pastebin micro-services in case they are running
            self.shutdown_daphne()
            # Start the Summarization and Pastebin micro-services in Daphne ASGI application servers
            self.start_daphne()
        except Exception as e:
            self.speak('''Error! The Summarization and Pastebin micro-services failed to
                       start.''')
            self.log.exception('Daphne failed to start \
                               due to an exception -\n{}'.format(
                e
            ))
        if settings_changed.get('api_token', False):
            # Update settings to the new API token
            if os.path.isfile(self.api_token_path):
                with open(self.api_token_path, 'r') as f:
                    self.settings['api_token'] = f.read().strip()
                # Use this new API token for all future communication with
                # the Summarization micro-service.
                self.headers = {'Authorization': 'Token {}'.format(self.settings.get('api_token'))}
                self.log.info('New API token loaded successfully')
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
                        self.log.info('New Root CA certificate successfully added to pastebin')
                        paste_id = response.json().get('url').split('/')[-2]
                        self.settings['root_ca'] = self.api_endpoint_pastebin_read_only + paste_id + '/'
                        self.log.info('New Root CA loaded successfully')
                        # Delete the previously generated Root CA certificate, if any
                        if int(paste_id) > 1:
                            response = requests.delete(
                                self.api_endpoint_pastebin + str(int(paste_id) - 1) + '/',
                                headers=self.headers,
                                verify=self.root_ca_cert_path)
                            if response.ok:
                                self.log.info('Old Root CA certificate deleted successfully')
                            else:
                                self.log.error('Unable to delete the old Root CA certificate')
                                # Increase verbosity for troubleshooting
                                response.raise_for_status()
                    else:
                        self.log.error('Unable to add the new Root CA certificate \
                                       to the pastebin')
                        # Increase verbosity for troubleshooting
                        response.raise_for_status()
                except Exception as e:
                    self.speak('''Error! Failed to share the self-signed Root CA certificate
                                for the Summarization micro-service.''')
                    self.log.exception('Unable to share the self-signed Root CA certificate \
                                       due to an exception -\n{}'.format(
                        e
                    ))
        if settings_changed.get('api_token', False) or settings_changed.get('root_ca', False):
            # Upload new setting values to the Selene Web UI. If this is the first run, then upload the settings
            # after 60 seconds because skill registration to the Selene web UI takes time.
            if self.first_run:
                self.schedule_event(handler=self.upload_settings, when=60, name='FirstRunUploadNewSettingValues')
                self.log.info('New setting values will be uploaded after 60 seconds')
            else:
                self.upload_settings()
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
                        for webpage_data in response_json.get('results', list()):
                            # Show the web page title on the Mycroft 1 mouth while
                            # the long summary is being read out aloud.
                            self.enclosure.mouth_text(webpage_data.get('webpage_title', ''))
                            if first_dialog:
                                self.log.debug('Found summaries to read')
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
                            self.log.debug('Successfully read a summary')
                    else:
                        self.log.error('Unable to fetch summaries')
                        # Increase verbosity for troubleshooting
                        response.raise_for_status()
            self.delete_data_after_reading()
            # Signal the end of the current queue to the user
            self.enclosure.mouth_text('No more summaries available.')
            self.speak('There are no more summaries available.')
            self.enclosure.reset()
            self.log.debug('Finished reading all summaries')
        except Exception as e:
            self.enclosure.mouth_text('Error')
            self.speak('''There was an error. Is the summarization
                       micro-service working?''')
            self.enclosure.reset()
            self.log.exception('Unable to work with the Daphne application server(s) \
                               due to an exception -\n{}'.format(
                e
            ))
        self.log.debug('handle_summarizer_webpage() completed')

    def stop(self):
        """
        Delete summaries from the micro-service queue which have already been
        read out aloud. We do not want to re-read any summaries that were read
        out loud earlier. We need to do this because Mycroft may have been
        interrupted while it was processing the queue.
        """
        self.log.debug('stop() started')
        self.delete_data_after_reading()
        self.log.debug('stop() completed')

    def shutdown(self):
        """
        Stop the Summarization micro-service cleanly before shutting down. This
        allows any pending transactions to be completed.
        """
        self.log.debug('shutdown() started')
        self.shutdown_daphne()
        self.log.debug('shutdown() started')

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
            if is_paired():
                settings_uploader.api = DeviceApi()
                if settings_uploader.api.identity.uuid and settings_uploader.yaml_path.is_file():
                    settings_uploader._load_settings_meta_file()
                    settings_uploader._update_settings_meta()
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][1]['value'] = self.settings.get('api_token', '')
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][2]['value'] = 'false'
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][4]['value'] = self.settings.get('root_ca', '')
                    settings_uploader.settings_meta['skillMetadata']['sections'][0]['fields'][5]['value'] = 'false'
                    settings_uploader._issue_api_call()
                    self.log.info('New setting values uploaded successfully \
                                    to the Selene Web UI')
        except Exception as e:
            self.log.exception('Unable to upload settings to the Selene Web UI \
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
                    self.log.debug('Successfully deleted an archived summary from storage')
                else:
                    self.log.error('Error while deleting archived summaries')
                    # Increase verbosity for troubleshooting
                    response.raise_for_status()
            self.log.info('Cleared all archived summaries from queue')
        except Exception as e:
            self.log.exception('Unable to clear the queue of archived summaries \
                               due to an exception -\n{}'.format(
                e
            ))
        self.log.debug('delete_data_after_reading() completed')

    def start_daphne(self):
        """
        Start two Daphne ASGI application servers in the background, one over HTTP and another over HTTPS using HTTP/2.
        """
        self.log.debug('start_daphne() started')
        # Start the Daphne ASGI application server over HTTP
        self.daphne = subprocess.Popen([
            os.path.join(
                self.root_dir,
                'scripts/start_daphne.sh'
            )
        ])
        # Start the Daphne ASGI application server over HTTPS using HTTP/2
        self.daphne_tls = subprocess.Popen([
            os.path.join(
                self.root_dir,
                'scripts/start_daphne_over_tls.sh'
            )
        ])
        # Wait for the Daphne ASGI application server processes to start
        time.sleep(30)
        self.log.debug('start_daphne() completed')

    def shutdown_daphne(self):
        """
        Cleanly stop the Daphne ASGI application server.
        """
        self.log.debug('shutdown_daphne() started')
        if hasattr(self, 'daphne') and self.daphne is not None:
            try:
                self.log.debug('Sending SIGTERM signal to Daphne ASGI application server')
                self.daphne.terminate()
                if self.daphne.poll() is None:
                    self.log.debug('Sending SIGKILL signal to Daphne ASGI application server')
                    self.daphne.kill()
                    if self.daphne.poll() is None:
                        raise Exception('Unable to stop Daphne ASGI application server')
                self.log.debug('Daphne ASGI application server successfully shut down with exit code: {}'.format(
                    self.daphne.returncode
                ))
                # Release resources
                self.daphne = None
            except Exception as e:
                self.log.exception('Error while shutting down the Daphne application server \
                                   due to an exception -\n{}'.format(
                    e
                ))
        if hasattr(self, 'daphne') and self.daphne_tls is not None:
            try:
                self.log.debug('Sending SIGTERM signal to Daphne-over-TLS ASGI application server')
                self.daphne_tls.terminate()
                if self.daphne_tls.poll() is None:
                    self.log.debug('Sending SIGKILL signal to Daphne-over-TLS ASGI application server')
                    self.daphne_tls.kill()
                    if self.daphne_tls.poll() is None:
                        raise Exception('Unable to stop Daphne-over-TLS ASGI application server')
                self.log.debug('Daphne-over-TLS ASGI application server successfully shut down with exit code: {}'.format(
                    self.daphne.returncode
                ))
                # Release resources
                self.daphne_tls = None
            except Exception as e:
                self.log.exception('Error while shutting down the Daphne-over-TLS application server \
                                   due to an exception -\n{}'.format(
                    e
                ))
        self.log.debug('shutdown_daphne() completed')


def create_skill():
    """
    Entry-point for loading this skill by the Mycroft AI Skill Loader.
    :return: An instance of the skill's main class
    """
    return WebpageSummarizer()

