"""Provides application for development purposes."""

from filemanager.factory import create_web_app
from filemanager.services import database

app = create_web_app()

app.app_context().push()

database.db.create_all()
