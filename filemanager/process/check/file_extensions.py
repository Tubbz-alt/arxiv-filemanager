"""Methods for checking file name extensions."""

import os

from arxiv.base import logging

from ...domain import FileType, UserFile, Workspace, Code
from .base import BaseChecker


logger = logging.getLogger(__name__)


class FixFileExtensions(BaseChecker):
    """Checks and fixes filename extensions for known formats."""

    FIXED_EXTENSION: Code = 'fixed_extension'
    FIXED_EXTENSION_MESSAGE = "Renamed '%s' to '%s'."

    def _change_extension(self, workspace: Workspace,
                          u_file: UserFile, extension: str) \
            -> UserFile:
        prev_name = u_file.name
        base_dir, name = os.path.split(u_file.path)
        base_name, _ = os.path.splitext(name)
        new_name = f'{base_name}.{extension}'
        workspace.rename(u_file, os.path.join(base_dir, new_name))
        workspace.add_warning(
            u_file, self.FIXED_EXTENSION,
            self.FIXED_EXTENSION_MESSAGE % (prev_name, new_name),
            is_persistant=False
        )
        return u_file

    def check_POSTSCRIPT(self, workspace: Workspace,
                         u_file: UserFile) -> UserFile:
        """Ensure that postscript files have a ``.ps`` extension."""
        if u_file.ext != 'ps':
            u_file = self._change_extension(workspace, u_file, 'ps')
        return u_file

    def check_PDF(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Ensure that PDF files have a ``.pdf`` extension."""
        if u_file.ext != 'pdf':
            u_file = self._change_extension(workspace, u_file, 'pdf')
        return u_file

    def check_HTML(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Ensure that HTML files have a ``.html`` extension."""
        if u_file.ext != 'html':
            u_file = self._change_extension(workspace, u_file, 'html')
        return u_file
