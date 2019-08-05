"""Tests related to the workspace source log."""

import os
import json
import shutil
import tempfile
import logging
from datetime import datetime
from unittest import TestCase, mock
from http import HTTPStatus as status

from pytz import UTC
import jsonschema

from arxiv.users import domain, auth

from filemanager.factory import create_web_app
from filemanager.services import database

from .util import generate_token

logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LOGLEVEL', '20')))


class TestDownloadLogs(TestCase):
    """Test service and source log download requests."""

    DATA_PATH = os.path.join(os.path.split(os.path.abspath(__file__))[0], '..')

    def setUp(self) -> None:
        """Initialize the Flask application, and get a client for testing."""
        self.workdir = tempfile.mkdtemp()
        self.server_name = 'fooserver.localdomain'
        self.app = create_web_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SERVER_NAME'] = self.server_name
        self.app.config['STORAGE_BASE_PATH'] = self.workdir

        # There is a bug in arxiv.base where it doesn't pick up app config
        # parameters. Until then, we pass it to os.environ.
        os.environ['JWT_SECRET'] = self.app.config.get('JWT_SECRET')
        self.client = self.app.test_client()
        # self.app.app_context().push()
        with self.app.app_context():
            database.db.create_all()

        with open('schema/resources/Workspace.json') as f:
            self.schema = json.load(f)

        # Create a token for writing to upload workspace
        self.token = generate_token(self.app, [auth.scopes.READ_UPLOAD,
                                               auth.scopes.WRITE_UPLOAD,
                                               auth.scopes.DELETE_UPLOAD_FILE])

        # Upload a gzipped tar archive package containing files to delete.
        filepath = os.path.join(self.DATA_PATH,
                                'test_files_upload/upload2.tar.gz')
        fname = os.path.basename(filepath)

        # Upload some files so we can delete them
        response = self.client.post('/filemanager/api/',
                                    data={
                                        'file': (open(filepath, 'rb'), fname),
                                    },
                                    headers={'Authorization': self.token},
                                    #        content_type='application/gzip')
                                    content_type='multipart/form-data')

        self.assertEqual(response.status_code, status.CREATED,
                         "Accepted and processed uploaded Submission Contents")

        self.original_upload_data = json.loads(response.data)
        self.upload_id = self.original_upload_data['upload_id']

    def tearDown(self):
        """
        Clean up!

        This cleans out the workspace. Comment out if you want to inspect files
        in workspace. Source log is saved to 'deleted_workspace_logs' directory.
        """
        shutil.rmtree(self.workdir)

    def test_with_insufficient_privileges(self):
        """Make HEAD request for log with underprivileged auth token."""
        admin_token = generate_token(self.app, [
            auth.scopes.READ_UPLOAD,
            auth.scopes.WRITE_UPLOAD,
            auth.scopes.DELETE_UPLOAD_WORKSPACE.as_global()
        ])

        # Attempt to check if source log exists
        response = self.client.head(f"/filemanager/api/{self.upload_id}/log",
                                    headers={'Authorization': admin_token})
        self.assertEqual(response.status_code, status.FORBIDDEN)

    def test_get_with_insufficient_privileges(self):
        """Make GET request for log with underprivileged auth token."""
        admin_token = generate_token(self.app, [
            auth.scopes.READ_UPLOAD,
            auth.scopes.WRITE_UPLOAD,
            auth.scopes.DELETE_UPLOAD_WORKSPACE.as_global()
        ])
        response = self.client.get(f"/filemanager/api/{self.upload_id}/log",
                                   headers={'Authorization': admin_token})
        self.assertEqual(response.status_code, status.FORBIDDEN)

    def test_head_with_sufficient_privileges(self):
        """Make HEAD request for log with ``READ_UPLOAD_LOGS`` scope."""
        # Add READ_UPLOAD_LOGS authorization to admin token
        admin_token = generate_token(self.app, [
            auth.scopes.READ_UPLOAD,
            auth.scopes.WRITE_UPLOAD,
            auth.scopes.READ_UPLOAD_LOGS,
            auth.scopes.DELETE_UPLOAD_WORKSPACE.as_global()
        ])

        # Attempt to check if source log exists
        response = self.client.head(f"/filemanager/api/{self.upload_id}/log",
                                    headers={'Authorization': admin_token})
        self.assertEqual(response.status_code, status.OK)
        self.assertIn('ETag', response.headers, "Returns an ETag header")

    def test_get_with_sufficient_privileges(self):
        """Make GET request for log with ``READ_UPLOAD_LOGS`` scope."""
        # Add READ_UPLOAD_LOGS authorization to admin token
        admin_token = generate_token(self.app, [
            auth.scopes.READ_UPLOAD,
            auth.scopes.WRITE_UPLOAD,
            auth.scopes.READ_UPLOAD_LOGS,
            auth.scopes.DELETE_UPLOAD_WORKSPACE.as_global()
        ])
        response = self.client.get(
            f"/filemanager/api/{self.upload_id}/log",
            headers={'Authorization': admin_token}
        )
        self.assertEqual(response.status_code, status.OK)
        self.assertIn('ETag', response.headers, "Returns an ETag header")

        # Look for something in upload source log
        self.assertIn(rb'unpack gzipped upload2.tar to dir', response.data,
                      'Test that upload file is in log.')

        # TODO: do we need this in tests? -- Erick 2019-06-20
        #
        # Write service log to file
        upload_log_filename = "upload_log_" + str(self.upload_id)
        log_path = os.path.join(self.workdir, upload_log_filename)
        with open(log_path, 'wb') as fileH:
            fileH.write(response.data)
        # Highlight log download. Remove at some point.
        logger.debug(f"FYI: SAVED UPLOAD SOURCE LOG FILE TO DISK: {log_path}\n")