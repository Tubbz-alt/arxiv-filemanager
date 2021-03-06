"""Check overall source type."""

import os

from arxiv.base import logging

from ...domain import FileType, UserFile, Workspace, SourceType, Code
from .base import BaseChecker, StopCheck


logger = logging.getLogger(__name__)
logger.propagate = False

INVALID_SOURCE_TYPE: Code = 'invalid_source_type'


class InferSourceType(BaseChecker):
    """Attempt to determine the source type for the workspace as a whole."""

    ALL_IGNORE_MESSAGE = (
        "All files are auto-ignore. If you intended to withdraw the "
        "article, please use the 'withdraw' function from the list "
        "of articles on your account page."
    )
    SINGLE_ANC_MESSAGE = 'Found single ancillary file. Invalid submission.'
    SINGLE_FILE_UNKNOWN_MESSAGE = 'Could not determine file type.'
    UNSUPPORTED_MESSAGE = 'Unsupported submission type'

    def check(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Check for single-file TeX source package."""
        workspace.source_type = SourceType.UNKNOWN
        if workspace.file_count != 1:
            return u_file
        logger.debug('Single file in workspace: %s', u_file.path)
        if u_file.is_ancillary or u_file.is_always_ignore:
            logger.debug('Ancillary or always-ignore file; invalid source')
            workspace.source_type = SourceType.INVALID
            workspace.add_error_non_file(INVALID_SOURCE_TYPE,
                                         self.SINGLE_ANC_MESSAGE)
        return u_file

    def check_workspace(self, workspace: Workspace) -> None:
        """Determine the source type for the workspace as a whole."""
        if workspace.file_count == 0:
            # No files detected, were all files removed? did user clear out
            # files? Since users are allowed to remove all files we won't
            # generate a message here. If system deletes all uploaded
            # files there will be warnings associated with those actions.
            logger.debug('Workspace has no files; setting source type invalid')
            workspace.source_type = SourceType.INVALID
            return

        if not workspace.source_type.is_unknown:
            return

        type_counts = workspace.get_file_type_counts()

        # HTML submissions may contain the formats below.
        html_aux_file_count = sum((
            type_counts[FileType.HTML], type_counts[FileType.IMAGE],
            type_counts[FileType.INCLUDE], type_counts[FileType.POSTSCRIPT],
            type_counts[FileType.PDF], type_counts[FileType.DIRECTORY],
            type_counts[FileType.README]
        ))

        # Postscript submission may be composed of several other formats.
        postscript_aux_file_counts = sum((
            type_counts[FileType.POSTSCRIPT], type_counts[FileType.PDF],
            type_counts['ignore'], type_counts[FileType.DIRECTORY],
            type_counts[FileType.IMAGE]
        ))
        if type_counts['files'] == type_counts['ignore']:
            workspace.source_type = SourceType.INVALID
            workspace.add_warning_non_file(INVALID_SOURCE_TYPE,
                                           self.ALL_IGNORE_MESSAGE)
            logger.debug('All files are auto-ignore; source type is invalid')
        elif type_counts['all_files'] > 0 and type_counts['files'] == 0:
            # No source files detected, extra ancillary files may be present
            # User may have deleted main document source.
            workspace.source_type = SourceType.INVALID
        elif type_counts[FileType.HTML] > 0 \
                and type_counts['files'] == html_aux_file_count:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.HTML
        elif type_counts[FileType.POSTSCRIPT] > 0 \
                and type_counts['files'] == postscript_aux_file_counts:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.POSTSCRIPT
        else:   # Default source type is TEX
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.TEX

    def check_tex_types(self, workspace: Workspace,
                        u_file: UserFile) -> UserFile:
        """Check for single-file TeX source package."""
        if workspace.source_type.is_unknown and workspace.file_count == 1:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.TEX
        return u_file

    def check_POSTSCRIPT(self, workspace: Workspace,
                         u_file: UserFile) -> UserFile:
        """Check for single-file PostScript source package."""
        if workspace.source_type.is_unknown and workspace.file_count == 1:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.POSTSCRIPT
        return u_file

    def check_PDF(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Check for single-file PDF source package."""
        if workspace.file_count == 1:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.PDF
        return u_file

    def check_HTML(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Check for single-file HTML source package."""
        if workspace.source_type.is_unknown and workspace.file_count == 1:
            workspace.remove_error(INVALID_SOURCE_TYPE)
            workspace.source_type = SourceType.HTML
        return u_file

    def check_FAILED(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """Check for single-file source with failed type detection."""
        if workspace.source_type.is_unknown and workspace.file_count == 1:
            workspace.source_type = SourceType.INVALID
            workspace.add_error_non_file(INVALID_SOURCE_TYPE,
                                         self.SINGLE_FILE_UNKNOWN_MESSAGE)
        return u_file

    # def check_DOS_EPS(self, workspace: Workspace, u_file: UserFile) \
    #         -> UserFile:
    #     if workspace.source_type.is_unknown and workspace.file_count == 1:
    #         workspace.source_type = SourceType.INVALID
    #         workspace.add_error(u_file, 'DOS EPS format is not supported.')
    #     return u_file

    def check_finally(self, workspace: Workspace,
                      u_file: UserFile) -> UserFile:
        """Check for unknown single-file source."""
        if workspace.source_type.is_unknown and workspace.file_count == 1:
            logger.debug('Source type not known, and only one file')
            workspace.source_type = SourceType.INVALID
            workspace.add_error_non_file(INVALID_SOURCE_TYPE,
                                         self.UNSUPPORTED_MESSAGE)
        return u_file
