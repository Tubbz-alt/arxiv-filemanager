"""Tests for :mod:`filemanager.services.upload`."""

from unittest import TestCase, mock
from datetime import datetime

from typing import Any
import sqlalchemy
from filemanager.services import uploads
from filemanager.domain import Upload


class TestUploadGetter(TestCase):
    """The method :meth:`.get_an_upload` retrieves data about uploads."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""

        self.uploads = uploads
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        uploads.db.init_app(app)
        uploads.db.app = app
        uploads.db.create_all()

        self.data = dict(name='The first upload', created=datetime.now(),
                         modified=datetime.now(), state="Active")
        self.dbupload = self.uploads.DBUpload(**self.data)  # type: ignore
        self.uploads.db.session.add(self.dbupload)  # type: ignore
        self.uploads.db.session.commit()  # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        uploads.db.session.remove()
        uploads.db.drop_all()

    def test_get_an_upload_that_exists(self) -> None:
        """When the uploads exists, returns a :class:`.Upload`."""
        upload = self.uploads.retrieve(1)  # type: ignore
        self.assertIsInstance(upload, Upload)
        self.assertEqual(upload.id, 1)
        self.assertEqual(upload.name, self.data['name'])
        self.assertEqual(upload.created, self.data['created'])

    def test_get_an_upload_that_doesnt_exist(self) -> None:
        """When the upload doesn't exist, returns None."""
        self.assertIsNone(uploads.retrieve(2))

    @mock.patch('filemanager.services.uploads.db.session.query')
    def test_get_upload_when_db_is_unavailable(self, mock_query: Any) -> None:
        """When the database squawks, raises an IOError."""

        def raise_op_error(*args: str, **kwargs: str) -> None:
            raise sqlalchemy.exc.OperationalError('statement', {}, None)

        mock_query.side_effect = raise_op_error
        with self.assertRaises(IOError):
            self.uploads.retrieve(1)  # type: ignore


class TestUploadCreator(TestCase):
    """:func:`.store_a_thing` creates a new record in the database."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""

        self.uploads = uploads
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        self.uploads.db.init_app(app)  # type: ignore
        self.uploads.db.app = app  # type: ignore
        self.uploads.db.create_all()  # type: ignore

        self.data = {'name': 'The first uploadthing', 'created': datetime.now(),
                     'modified': datetime.now(), 'state': "Active"}
        self.dbupload = self.uploads.DBUpload(**self.data)  # type: ignore
        self.uploads.db.session.add(self.dbupload)  # type: ignore
        self.uploads.db.session.commit()  # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        self.uploads.db.session.remove()  # type: ignore
        self.uploads.db.drop_all()  # type: ignore

    def test_store_an_upload(self) -> None:
        """A new row is added for the upload."""
        existing_upload = Upload(name='The first upload', created=datetime.now(),
                                 modified=datetime.now(), state="Active")

        self.uploads.store(existing_upload)  # type: ignore
        self.assertGreater(existing_upload.id, 0, "Upload.id is updated with pk id")

        dbupload = self.uploads.db.session.query(self.uploads.DBUpload).get(existing_upload.id)  # type: ignore

        self.assertEqual(dbupload.name, existing_upload.name)


class TestUploadUpdater(TestCase):
    """:func:`.update_an_upload` updates the db with :class:`.Upload` data."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""

        self.uploads = uploads
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        self.uploads.db.init_app(app)  # type: ignore
        self.uploads.db.app = app  # type: ignore
        self.uploads.db.create_all()  # type: ignore

        self.data = dict(name='The first upload', created=datetime.now())
        self.dbupload = self.uploads.DBUpload(**self.data)  # type: ignore
        self.uploads.db.session.add(self.dbupload)  # type: ignore
        self.uploads.db.session.commit()  # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        self.uploads.db.session.remove()  # type: ignore
        self.uploads.db.drop_all()  # type: ignore

    def test_update_an_upload(self) -> None:
        """The db is updated with the current state of the :class:`.Upload`."""
        an_upload = Upload(id=self.dbupload.id, name='Whoops')
        self.uploads.update(an_upload)  # type: ignore

        dbupload = self.uploads.db.session.query(self.uploads.DBUpload).get(self.dbupload.id)  # type: ignore

        self.assertEqual(dbupload.name, an_upload.name)

    @mock.patch('filemanager.services.uploads.db.session.query')
    def test_operationalerror_is_handled(self, mock_query: Any) -> None:
        """When the db raises an OperationalError, an IOError is raised."""
        an_upload = Upload(id=self.dbupload.id, name='Whoops')

        def raise_op_error(*args, **kwargs) -> None:  # type: ignore
            """Function designed to raise operational error."""
            raise sqlalchemy.exc.OperationalError('statement', {}, None)

        mock_query.side_effect = raise_op_error

        with self.assertRaises(IOError):
            self.uploads.update(an_upload)  # type: ignore

    def test_upload_really_does_not_exist(self) -> None:
        """If the :class:`.Upload` doesn't exist, a RuntimeError is raised."""
        an_update = Upload(id=555, name='Whoops')  # Unlikely to exist.
        with self.assertRaises(RuntimeError):
            self.uploads.update(an_update)  # type: ignore

    @mock.patch('filemanager.services.uploads.db.session.query')
    def test_thing_does_not_exist(self, mock_query: Any) -> None:
        """If the :class:`.Upload` doesn't exist, a RuntimeError is raised."""
        an_upload = Upload(id=555, name='Whoops')  # Unlikely to exist.
        mock_query.return_value = mock.MagicMock(
            get=mock.MagicMock(return_value=None)
        )
        with self.assertRaises(RuntimeError):
            self.uploads.update(an_upload)  # type: ignore