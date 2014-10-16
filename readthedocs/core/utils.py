import getpass
import logging
import os
import shutil
import subprocess
from datetime import datetime
from urlparse import urlparse

from django.conf import settings

import tastyapi.slum

log = logging.getLogger(__name__)

SYNC_USER = getattr(settings, 'SYNC_USER', getpass.getuser())


def copy(path, target, file=False):
    """
    A better copy command that works with files or directories.

    Respects the ``MULTIPLE_APP_SERVERS`` setting when copying.
    """
    MULTIPLE_APP_SERVERS = getattr(settings, 'MULTIPLE_APP_SERVERS', [])
    if MULTIPLE_APP_SERVERS:
        log.info("Remote Copy %s to %s" % (path, target))
        for server in MULTIPLE_APP_SERVERS:
            mkdir_cmd = ("ssh %s@%s mkdir -p %s" % (SYNC_USER, server, target))
            ret = os.system(mkdir_cmd)
            if ret != 0:
                log.error("COPY ERROR to app servers:")
                log.error(mkdir_cmd)

            if file:
                slash = ""
            else:
                slash = "/"
            # Add a slash when copying directories
            sync_cmd = ("rsync -e 'ssh -T' -av --delete %s%s %s@%s:%s"
                        % (path, slash, SYNC_USER, server, target))
            ret = os.system(sync_cmd)
            if ret != 0:
                log.error("COPY ERROR to app servers.")
                log.error(sync_cmd)
    else:
        log.info("Local Copy %s to %s" % (path, target))
        if file:
            if os.path.exists(target):
                os.remove(target)
            shutil.copy2(path, target)
        else:
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(path, target)

def copy_to_app_servers(full_build_path, target, mkdir=True):
    """
    A helper to copy a directory across app servers
    """
    log.info("Copying %s to %s" % (full_build_path, target))
    for server in getattr(settings, 'MULTIPLE_APP_SERVERS', []):
        mkdir_cmd = ("ssh %s@%s mkdir -p %s" % (SYNC_USER, server, target))
        ret = os.system(mkdir_cmd)
        if ret != 0:
            log.error("COPY ERROR to app servers:")
            log.error(mkdir_cmd)

        sync_cmd = ("rsync -e 'ssh -T' -av --delete %s/ %s@%s:%s"
                    % (full_build_path, SYNC_USER, server, target))
        ret = os.system(sync_cmd)
        if ret != 0:
            log.error("COPY ERROR to app servers.")
            log.error(sync_cmd)


def copy_file_to_app_servers(from_file, to_file):
    """
    A helper to copy a single file across app servers
    """
    log.info("Copying %s to %s" % (from_file, to_file))
    to_path = os.path.dirname(to_file)
    for server in getattr(settings, 'MULTIPLE_APP_SERVERS', []):
        mkdir_cmd = ("ssh %s@%s mkdir -p %s" % (SYNC_USER, server, to_path))
        ret = os.system(mkdir_cmd)
        if ret != 0:
            log.error("COPY ERROR to app servers.")
            log.error(mkdir_cmd)

        sync_cmd = ("rsync -e 'ssh -T' -av --delete %s %s@%s:%s" % (from_file,
                                                                    SYNC_USER,
                                                                    server,
                                                                    to_file))
        ret = os.system(sync_cmd)
        if ret != 0:
            log.error("COPY ERROR to app servers.")
            log.error(sync_cmd)


def run_on_app_servers(command):
    """
    A helper to copy a single file across app servers
    """
    log.info("Running %s on app servers" % command)
    ret_val = 0
    if getattr(settings, "MULTIPLE_APP_SERVERS", None):
        for server in settings.MULTIPLE_APP_SERVERS:
            ret = os.system("ssh %s@%s %s" % (SYNC_USER, server, command))
            if ret != 0:
                ret_val = ret
        return ret_val
    else:
        ret = os.system(command)
        return ret

def make_latest(project):
    """
    Useful for correcting versions with no latest, using the database.

    >>> no_latest = Project.objects.exclude(versions__slug__in=['latest'])
    >>> for project in no_latest:
    >>>     make_latest(project)
    """
    branch = project.default_branch or project.vcs_repo().fallback_branch
    version_data, created = Version.objects.get_or_create(
        project=project,
        slug='latest',
        type='branch',
        active=True,
        verbose_name='latest',
        identifier=branch,
    )


def clean_url(url):
    parsed = urlparse(url)
    if parsed.scheme:
        scheme, netloc = parsed.scheme, parsed.netloc
    elif parsed.netloc:
        scheme, netloc = "http", parsed.netloc
    else:
        scheme, netloc = "http", parsed.path
    return netloc


def cname_to_slug(host):
    from dns import resolver
    answer = [ans for ans in resolver.query(host, 'CNAME')][0]
    domain = answer.target.to_unicode()
    slug = domain.split('.')[0]
    return slug


class ShellCommand(object):
    '''Shell command wrapper to return stdout and stderr

    This exists to track not just the output, but the command run and stats
    around the command as well. This will take the place of just returning the
    exit code and stderr/stdout.
    '''

    def __init__(self, command, cwd=None, shell=False, env=None,
                 combine_output=True):
        self.command = command
        self.output = {
            'output': None,
            'error': None,
        }
        self.exit_code = None
        self.start_time = None
        self.end_time = None
        if cwd is None:
            cwd = os.getcwd()
        self.cwd = cwd
        self.shell = shell
        if env is None:
            env = os.environ.copy()
        env['READTHEDOCS'] = 'True'
        if 'DJANGO_SETTINGS_MODULE' in env:
            del env['DJANGO_SETTINGS_MODULE']
        if 'PYTHONPATH' in env:
            del env['PYTHONPATH']
        self.env = env
        self.combine_output = combine_output

    def from_command(cls, command, **kwargs):
        self = cls(command, **kwargs)
        self.run()
        return self

    def run(self, **kwargs):
        '''Run command, tracking start/end time and exit code

        **kwargs
            Arguments to pass on to command execution
        '''
        # Redirect streams
        stream_out = subprocess.PIPE
        stream_err = subprocess.PIPE
        if self.combine_output:
            stream_err = subprocess.STDOUT

        log.info('Executing command {0}, cwd={1}'.format(self.command, self.cwd))
        try:
            process = subprocess.Popen(
                self.command, stdout=stream_out, stderr=stream_err, cwd=self.cwd,
                shell=self.shell, env=self.env)
            self.start_time = datetime.now()
            (self.output['output'], self.output['error']) = process.communicate()
            self.exit_code = process.returncode
        except:
            self.output['output'] = ''
            self.output['error'] = traceback.format_exc()
            self.exit_code = -1
            log.error("Command failed", exc_info=True)
        finally:
            self.end_time = datetime.now()
        return self

    def successful(self):
        return self.exit_code == 0

    def failed(self):
        return self.exit_code != 0

    def post(self, build, api=None):
        '''Post command to api, given build'''
        if api is None:
            api = tastyapi.slum.apiv2
        command = self.command
        if isinstance(command, list):
            command = ' '.join(command)
        data = {
            'build': build['id'],
            'command': command,
            'output': self.output['output'],
            'exit_code': self.exit_code,
            'start_time': str(self.start_time),
            'end_time': str(self.end_time),
        }
        build_command = api.buildcommand.post(data)
