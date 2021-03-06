import time
import tempfile
from datetime import datetime
from filemanager.domain import Workspace
from filemanager.process.strategy import AsynchronousCheckingStrategy, \
    SynchronousCheckingStrategy
from filemanager.process.check import get_default_checkers
from filemanager.services.storage import SimpleStorageAdapter

basedir = tempfile.mkdtemp()
storage = SimpleStorageAdapter(basedir)

workspace = Workspace(
    upload_id=1234,
    owner_user_id='98765',
    created_datetime=datetime.now(),
    modified_datetime=datetime.now(),
    _strategy=SynchronousCheckingStrategy(),
    checkers=get_default_checkers(),
    _storage=storage
)
workspace.initialize()

with open('tests/test_files_upload/UploadWithANCDirectory.tar.gz', 'rb') as f:
    tgz_content = f.read()



u_file = workspace.create('upload.tar.gz')
with workspace.open(u_file, 'wb') as f:
    f.write(tgz_content)

start = time.time()
workspace.perform_checks()
print(time.time() - start)
workspace.delete_all_files()
