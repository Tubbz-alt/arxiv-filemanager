# arXiv filemanager service

File management and sanitization service

### Quick Start Guide

There are multiple ways to run the file management server: docker,
docker-compose, and local flask development server.

### Authentication + authorization

This app uses ``arxiv.users`` to implement authentication and authorization
requirements. You will need to generate and use an auth token for development
and manual testiing. Be sure to use the same value for ``JWT_SECRET`` when
generating the auth token and when running the application.

```bash
JWT_SECRET=foosecret generate-token
```

The following scopes are used in this application:

| Scope                           | Description                               |
|---------------------------------|-------------------------------------------|
| ``upload:read``                 | View the content of an upload workspace.  |
| ``upload:create``               | Create a new workspace.                   |
| ``upload:update``               | Upload files to to a workspace.           |
| ``upload:release``              | Release a workspace (pre-delete).         |
| ``upload:delete``               | Can delete files from a workspace.        |
| ``upload:delete_workspace``     | Delete an entire workspace.               |
| ``upload:read_logs``            | Can read logs for a workspace.            |
| ``upload:read_service_logs``    | Can read service logs.                    |
| ``upload:create_checkpoint``    | Create a checkpoint.                      |
| ``upload:delete_checkpoint``    | Delete a checkpoint.                      |
| ``upload:read_checkpoints``     | Read from checkpoints.                    |
| ``upload:restore_checkpoint``   | Restore workspace to a checkpoint.        |



### Docker

Prerequisites: (Docker application, arxiv-base)

1. Setup [Docker CE using the instructions for your
   OS](https://docs.docker.com/engine/installation/)

Build/Run/Test FileManager Docker image:

2. Build the Docker image with:

```bash
docker build . -t arxiv-filemanager \
    --build-args=BASE_VERSION=[target base version]
```

where ``[target base version]`` is the tag on ``arxiv/base`` against which you
wish to build. The default should be the most recent version of ``arxiv/base``
against which this service has been tested.

3. Run the application with:

```bash
docker run -p 8000:8000 \
    --name=filemanager \
    -e JWT_SECRET=foosecret \
    arxiv-filemanager
```

Note: (add a `-d` flag to run in daemon mode)

4. Test that the container is working:
   http://localhost:8000/filemanager/api/status
5. To shut down the container, press ``ctrl-c`` (or `docker stop filemanager`
   if in daemon mode).
6. Each time you change a file, you will need to rebuild the Docker image
   in order to import the updated files. Alternatively, volume-mount selected
   parts of your home directory such has .ssh and .gitconfig in your `docker
   run` command if you wish to be able to push modifications to github.

Note: Local flask development server (described below) detects changed files
and reloads them into running development server (debug mode).

#### Docker Cleanup

To purge your container run  `docker rmi filemanager`.

If you receive the following error:

```
$ docker rmi c196c3ef21c7
Error response from daemon: conflict: unable to delete c196c3ef21c7 (must be
forced) - image is being used by stopped container 75bb481b5857
```

You will need to issue a remove command for each container that depends on the
image you are trying to delete. Run `docker rm CONTAINER_ID` for each stopped
container until the above error clears

Note: There are commands that will remove images and containers en masse. For
now I'll refer you to the Docker documentation.

### Local Flask Deployment

This section describes launching flask development server and running script to
load test database.

Sometimes Docker adds more overhead than you want, especially when making quick
changes. We assume your developer machine already has a version of Python 3.6
with `pip`.

1. `pipenv install --dev`
2. `FLASK_APP=app.py pipenv run python populate_test_database.py`
3. `JWT_SECRET=foosecret FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run`
4. Test that the app is working: http://localhost:5000/filemanager/api/status

#### Notes on the development server

Flask provides a single-threaded dev server for your enjoyment.

The entrypoint for this dev server is [``app.py``](app.py) (in the root of the
project). Flask expects the path to this entrypoint in the environment variable
``FLASK_APP``. To run the dev server, try (from the project root):

```bash
$ JWT_SECRET=foosecret FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```

``FLASK_DEBUG=1`` enables a slew of lovely development and debugging features.
For example, the dev server automatically restarts when you make changes to the
application code.

Note that neither the dev server or the ``app.py`` entrypoint are acceptable
for use in production.

#### Load test database

A convenience script [``populate_test_database.py``](populate_test_database.py)
is provided to set up an on-disk SQLite database and some sample data. You can
use this as a starting point for more complex set-up operations (or not). Be
sure to run this with the ``FLASK_APP`` variable set, e.g.

```bash
$ FLASK_APP=app.py pipenv run python populate_test_database.py
```



### Authorization token

Use the ``generate_token.py`` script to generate an authentication JWT. Be sure
that you are using the same secret when running this script as when you run
the app.

```bash
$ JWT_SECRET=foosecret FLASK_APP=app.py pipenv run python generate_token.py
Numeric user ID: 4
Email address: erick@foo.com
Username: erick
First name [Jane]:
Last name [Doe]:
Name suffix [IV]:
Affiliation [Cornell University]:
Numeric rank [3]:
Alpha-2 country code [us]:
Default category [astro-ph.GA]:
Submission groups (comma delim) [grp_physics]:
Endorsement categories (comma delim) [astro-ph.CO,astro-ph.GA]:
Authorization scope (comma delim) [upload:read,upload:write,upload:admin]:
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiZTljMGQwMDUtMTk1My00YWRiLWE0YzEtYzdmNWY1OGM5YTk4Iiwic3RhcnRfdGltZSI6IjIwMTgtMDgtMDlUMTQ6NDg6MDguNzY2NjUzLTA0OjAwIiwidXNlciI6eyJ1c2VybmFtZSI6ImVyaWNrIiwiZW1haWwiOiJlcmlja0Bmb28uY29tIiwidXNlcl9pZCI6IjQiLCJuYW1lIjp7ImZvcmVuYW1lIjoiSmFuZSIsInN1cm5hbWUiOiJEb2UiLCJzdWZmaXgiOiJJViJ9LCJwcm9maWxlIjp7ImFmZmlsaWF0aW9uIjoiQ29ybmVsbCBVbml2ZXJzaXR5IiwiY291bnRyeSI6InVzIiwicmFuayI6Mywic3VibWlzc2lvbl9ncm91cHMiOlsiZ3JwX3BoeXNpY3MiXSwiZGVmYXVsdF9jYXRlZ29yeSI6eyJhcmNoaXZlIjoiYXN0cm8tcGgiLCJzdWJqZWN0IjoiR0EifSwiaG9tZXBhZ2VfdXJsIjoiIiwicmVtZW1iZXJfbWUiOnRydWV9fSwiY2xpZW50IjpudWxsLCJlbmRfdGltZSI6IjIwMTgtMDgtMTBUMDA6NDg6MDguNzY2NjUzLTA0OjAwIiwiYXV0aG9yaXphdGlvbnMiOnsiY2xhc3NpYyI6MCwiZW5kb3JzZW1lbnRzIjpbW1siYXN0cm8tcGgiLCJDTyJdLG51bGxdLFtbImFzdHJvLXBoIiwiR0EiXSxudWxsXV0sInNjb3BlcyI6W1sidXBsb2FkOnJlYWQiLCJ1cGxvYWQ6d3JpdGUiLCJ1cGxvYWQ6YWRtaW4iXV19LCJpcF9hZGRyZXNzIjpudWxsLCJyZW1vdGVfaG9zdCI6bnVsbCwibm9uY2UiOm51bGx9.aOgRj73TT-zsRvF7gnPPjplJzcnXkKzYzEvMB61jEsY
```

Start the dev server with:

```
$ JWT_SECRET=foosecret FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```

Use the (rather long) token in your requests to authorized endpoints. Set the
header ``Authorization: [token]``.

### Push File Manager Image to Docker Hub.

