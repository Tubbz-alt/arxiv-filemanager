"""Handles all upload-related requests."""

from typing import Tuple, Optional
from datetime import datetime
import json
from werkzeug.datastructures import FileStorage
from flask.json import jsonify

import filemanager
from filemanager import status

from filemanager.shared import url_for

from filemanager.domain import Upload
from filemanager.services import uploads
from filemanager.tasks import sanitize_upload, check_sanitize_status

from filemanager.arxiv.file import File

# upload status codes
INVALID_UPLOAD_ID = {'reason': 'invalid upload identifier'}
MISSING_UPLOAD_ID = {'reason': 'missing upload id'}
UPLOAD_NOT_FOUND = {'reason': 'upload not found'}
ERROR_RETRIEVING_UPLOAD = {'reason': 'upload not found'}

# upload status
NO_SUCH_THING = {'reason': 'there is no upload'}
THING_WONT_COME = {'reason': 'could not get the upload'}
CANT_CREATE_UPLOAD = {'reason': 'could not create the upload'}
MISSING_NAME = {'reason': 'an upload needs a name'}
ACCEPTED = {'reason': 'upload in progress'}
INVALID_TASK_ID = {'reason': 'invalid task id'}

TASK_DOES_NOT_EXIST = {'reason': 'task not found'}
TASK_IN_PROGRESS = {'status': 'in progress'}
TASK_FAILED = {'status': 'failed'}
TASK_COMPLETE = {'status': 'complete'}

Response = Tuple[Optional[dict], int, dict]


# Create an upload workspace - generate unique upload identifier.


def create_upload() -> Response:
    """
    Create a new :class:`.Upload`.

    Parameters
    ----------

    Returns
    -------
    dict
        Unique upload identifier.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """

    headers = {}

    # TODO: Finalize or remove 'name'
    # I've left 'name' field for now in the event we want to add an optional
    # comment or label
    name = "Upload"

    if not name or not isinstance(name, str):
        status_code = 200
        response_data = MISSING_NAME
    else:

        upload = Upload(name=name, created_datetime=datetime.now(),
                        modified_datetime=datetime.now(),
                        state='Active')
        try:
            # Store in DB
            uploads.store(upload)

            status_code = status.HTTP_201_CREATED
            upload_url = url_for('upload_api.upload_files', upload_id=upload.upload_id)

            response_data = {
                'upload_id': upload.upload_id,
                'created_datetime': upload.created_datetime,
                'modified_datetime': upload.created_datetime,
                'url': upload_url
            }
            headers['Location'] = upload_url
        except RuntimeError as e:
            print('Error: ' + e.__str__())
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            response_data = CANT_CREATE_UPLOAD

    return response_data, status_code, headers




def upload(upload_id: int, file: FileStorage) -> Response:
    """Upload individual files or compressed archive. Unpack and add
    files to upload workspace.

    Parameters
    ----------
    upload_id : int
        The unique identifier for the upload in question.
    file : FileStorage
        File archive to be processed.

    Returns
    -------
    dict
        Basic information about the upload task.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """

    # TODO: Hook up async processing (celery/redis) - doesn't work now

    #print(f'Controller: Schedule upload task for {upload_id}')
    #
    #result = sanitize_upload.delay(upload_id, file)
    #
    #headers = {'Location': url_for('upload_api.upload_status',
    #                              task_id=result.task_id)}
    # return ACCEPTED, status.HTTP_202_ACCEPTED, headers

    # TODO: Replace code below this with async task - above

    try:
        # Make sure we have an upload to work with
        upload: Optional[Upload] = uploads.retrieve(upload_id)

        if upload is None:
            status_code = status.HTTP_404_NOT_FOUND
            response_data = UPLOAD_NOT_FOUND
        else:
            # Now handle upload package - process file or gzipped tar archive

            # NOTE: This will need to be migrated to task.py using Celery at
            #       some point in future. Depends in time it takes to process
            #       uploads.retrieve

            # Keep track of how long processing upload takes
            start_datetime = datetime.now()

            # Create Upload object
            uploadObj = filemanager.process.upload.Upload(upload_id)

            # Process upload
            uploadObj.process_upload(file)

            completion_datetime = datetime.now()

            # Keep track of files processed (this included deleted files)
            file_list = generate_upload_summary(uploadObj)

            # Prepare upload details (DB). I'm assuming that in memory Redis
            # is not sufficient for results that may be needed in the distant future.
            errors_and_warnings = uploadObj.get_errors() + uploadObj.get_warnings()
            upload.lastupload_logs = str(errors_and_warnings)
            upload.lastupload_start_datetime = start_datetime
            upload.lastupload_completion_datetime = completion_datetime
            upload.lastupload_file_summary = json.dumps(file_list)
            upload.state = 'ACTIVE'

            # Store in DB
            uploads.update(upload)


            # Upload action itself has very simple response
            headers = {'Location': url_for('upload_api.upload_status',
                                           # task_id=result.task_id)}
                                           upload_id=upload.upload_id)}
            return ACCEPTED, status.HTTP_202_ACCEPTED, headers

    except IOError:
        response_data = ERROR_RETRIEVING_UPLOAD
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response_data, status_code, {}

def upload_status(upload_id: int) -> Response:
    """
    Status for upload task. Refers to task processing upload.
    This is NOT status of upload.

    Parameters
    ----------
    upload_id : int
        The unique identifier for the upload in question.

    Returns
    -------
    dict
        Basic information about the upload task.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """

    try:
        upload: Optional[Upload] = uploads.retrieve(upload_id)
        if upload is None:
            status_code = status.HTTP_404_NOT_FOUND
            response_data = UPLOAD_NOT_FOUND
        else:
            status_code = status.HTTP_200_OK
            response_data = {
                'task_id': upload.upload_id,
                'start_datetime': upload.lastupload_start_datetime,
                'status': "SUCCEEDED"
            }
    except IOError:
        response_data = ERROR_RETRIEVING_UPLOAD
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response_data, status_code, {}

def upload_summary(upload_id: int) -> Response:
    """Provide summary of important upload details.

       Parameters
       ----------
       upload_id : int
           The unique identifier for the upload in question.

       Returns
       -------
       dict
           Detailed information about the upload.

           logs - Errors and Warnings
           files - list of file details


       int
           An HTTP status code.
       dict
           Some extra headers to add to the response.
       """

    try:
        # Make sure we have an upload to work with
        upload: Optional[Upload] = uploads.retrieve(upload_id)

        if upload is None:
            status_code = status.HTTP_404_NOT_FOUND
            response_data = UPLOAD_NOT_FOUND
        else:
            status_code = status.HTTP_200_OK
            response_data = {
                'upload_id': upload.upload_id,
                'created_datetime': upload.created_datetime,
                'modified_datetime': upload.modified_datetime,
                'start_datetime': upload.lastupload_start_datetime,
                'completion_datetime': upload.lastupload_completion_datetime,
                'files': upload.lastupload_file_summary,
                'log': upload.lastupload_logs,
                'status': "SUCCEEDED",
                'upload_state': upload.state
            }

    except IOError:
        response_data = ERROR_RETRIEVING_UPLOAD
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response_data, status_code, {}


# TODO: This really belongs as part of Upload object, though customized for UI display.

def generate_upload_summary(uploadObj: Upload) -> list:
    """Returns a list files with details [dict]. Maybe be generated when upload
    is processed or when invoked with existing upload directory.

    Return list of files created during upload processing.

    Generates a list of files in the upload source directory.

    Note: The detailed of regenerating the file list is still being worked out since
          the list generated during processing upload (includes removed files) may be
          different than the list generated against an existing source directory.

    """

    file_list = []

    if uploadObj.has_files():
        count = len(uploadObj.get_files())

        for fileObj in uploadObj.get_files():

            #print("\tFile:" + fileObj.name + "\tFilePath: " + fileObj.public_filepath
            #      + "\tRemoved: " + str(fileObj.removed) + " Size: " + str(fileObj.size))

            # Collect details we would like to return to client
            file_details = {}
            file_details = {
                'name': fileObj.name,
                'public_filepath': fileObj.public_filepath,
                'size': fileObj.size,
                'type': fileObj.type_string,
            }
            if fileObj.removed:
                file_details['removed'] = fileObj.removed

            file_list.append(file_details)

        return file_list

# Demo reference code
# TODO: Implement async processing and use/remove code below.


def upload_as_task(upload_id: int) -> Response:
    """
    Start sanitizing (a :class:`.Upload`.

    Parameters
    ----------
    upload_id : int

    Returns
    -------
    dict
        Some data.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """
    result = sanitize_upload.delay(upload_id)
    headers = {'Location': url_for('upload_api.upload_status',
                                   task_id=result.task_id)}
    return ACCEPTED, status.HTTP_202_ACCEPTED, headers


def upload_as_task_status(task_id: str) -> Response:
    """
    Check the status of a mutation process.

    Parameters
    ----------
    task_id : str
        The ID of the mutation task.

    Returns
    -------
    dict
        Some data.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """
    try:
        task_status, result = check_sanitize_status(task_id)
    except ValueError as e:
        return INVALID_TASK_ID, status.HTTP_400_BAD_REQUEST, {}
    if task_status == 'PENDING':
        return TASK_DOES_NOT_EXIST, status.HTTP_404_NOT_FOUND, {}
    elif task_status in ['SENT', 'STARTED', 'RETRY']:
        return TASK_IN_PROGRESS, status.HTTP_200_OK, {}
    elif task_status == 'FAILURE':
        reason = TASK_FAILED
        reason.update({'reason': str(result)})
        return reason, status.HTTP_200_OK, {}
    elif task_status == 'SUCCESS':
        reason = TASK_COMPLETE
        reason.update({'result': result})
        headers = {'Location': url_for('external_api.read_thing',
                                       thing_id=result['thing_id'])}
        return TASK_COMPLETE, status.HTTP_303_SEE_OTHER, headers
    return TASK_DOES_NOT_EXIST, status.HTTP_404_NOT_FOUND, {}