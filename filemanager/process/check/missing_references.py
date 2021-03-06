"""Checks for possible missing references."""

import os
import re
from arxiv.base import logging

from ...domain import FileType, UserFile, Workspace, Code
from .base import BaseChecker

logger = logging.getLogger(__name__)


class CheckForMissingReferences(BaseChecker):
    """
    Checks for .bib files, and removes them if a .bbl file is present.

    New modified handling of .bib without .bbl. We no longer delete .bib UNLESS
    we detect .bbl file. Generate error until we have .bbl.
    """

    BIB_FILE = re.compile(r'(.*)\.bib$', re.IGNORECASE)

    BIB_WITH_BBL: Code = 'bib_with_bbl'
    BIB_WITH_BBL_MESSAGE = (
        "We do not run bibtex in the auto - TeXing procedure. We do not run"
        " bibtex because the .bib database files can be quite large, and the"
        " only thing necessary to make the references for a given paper is"
        " the .bbl file."
    )

    BIB_NO_BBL: Code = 'bib_no_bbl'
    BIB_NO_BBL_MESSAGE = (
        "We do not run bibtex in the auto - TeXing "
        "procedure. If you use it, include in your submission the .bbl file "
        "which bibtex produces on your home machine; otherwise your "
        "references will not come out correctly. We do not run bibtex "
        "because the .bib database files can be quite large, and the only "
        "thing necessary to make the references for a given paper is "
        "the.bbl file."
    )

    BBL_MISSING: Code = 'bbl_missing'
    BBL_MISSING_MESSAGE = (
        "Your submission contained {base}.bib file, but no {base}.bbl"
        " file (include {base}.bbl, or submit without {base}.bib; and"
        " remember to verify references)."
    )

    def check_workspace(self, workspace: Workspace) -> None:
        """Check for a .bib file, and remove if a .bbl file is present."""
        for u_file in workspace.iter_files():
            if self.BIB_FILE.search(u_file.name):
                self._check_for_missing_bbl_file(workspace, u_file)


    def _check_for_missing_bbl_file(self, workspace: Workspace,
                                    u_file: UserFile) -> None:
        """
        Look for a sibling .bbl file.

        If found, delete the .bib file. Otherwise, add an error, as this is
        very likely indicative of missing references.
        """
        # Create path to bbl file - assume uses same basename as .bib.
        base_path, name = os.path.split(u_file.path)
        base, _ = os.path.splitext(name)
        bbl_file = f'{base}.bbl'
        bbl_path = os.path.join(base_path, bbl_file)

        if workspace.exists(bbl_path):
            # If .bbl exists we go ahead and delete .bib file and warn
            # submitter of this action.
            workspace.add_warning(u_file, self.BIB_WITH_BBL,
                                  self.BIB_WITH_BBL_MESSAGE,
                                  is_persistant=False)
            workspace.remove(u_file,
                             f"Removed the file '{u_file.name}'. Using"
                             f" '{bbl_file}' for references.")
        else:
            # Missing .bbl (potential missing references). Generate an
            # error and DO NOT DELETE .bib file. Note: We are using .bib as
            # flag until .bbl exists.
            workspace.add_warning(u_file, self.BIB_NO_BBL,
                                  self.BIB_NO_BBL_MESSAGE)
            workspace.add_error(u_file, self.BBL_MISSING,
                                self.BBL_MISSING_MESSAGE.format(base=base))
