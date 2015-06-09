import getpass
import logging
import os

from urlparse import urlparse

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context

from builds.models import Build

log = logging.getLogger(__name__)

SYNC_USER = getattr(settings, 'SYNC_USER', getpass.getuser())


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


def trigger_build(project, version=None, record=True, force=False, basic=False,
                  queue=None):
    """
    An API to wrap the triggering of a build.

    :param project: Project to build
    :type project: readthedocs.projects.models.Project
    :param version: Project version to build
    :type version: readthedocs.builds.models.Version
    :param record: Record build
    :type record: bool
    :param force: Pass on force build to task
    :type force: bool
    :param basic: TODO
    :param queue: Celery queue name to user for triggering build, defaults to
                  the default Cerlery queue in settings
    :returns: Project build instance or None
    :rtype: readthedocs.builds.models.Build
    """
    # Avoid circular import
    from projects.tasks import update_docs

    if project.skip:
        return None
    if not version:
        version = project.versions.get(slug='latest')

    build = None
    opts = {}
    kwargs = dict(
        pk=project.pk,
        version_pk=version.pk,
        record=record,
        force=force,
        basic=basic)
    )
    if record:
        build = Build.objects.create(
            project=project,
            version=version,
            type='html',
            state='triggered',
            success=True,
        )
        kwargs['build_pk'] = build.pk
    # Task options
    if queue is not None:
        opts['queue'] = queue
    update_docs.apply_async(kwargs=kwargs, **opts)

    return build


def send_email(recipient, subject, template, template_html, context=None,
               request=None):
    '''
    Send multipart email

    recipient
        Email recipient address

    subject
        Email subject header

    template
        Plain text template to send

    template_html
        HTML template to send as new message part

    context
        A dictionary to pass into the template calls

    request
        Request object for determining absolute URL
    '''
    if request:
        scheme = 'https' if request.is_secure() else 'http'
        context['uri'] = '{scheme}://{host}'.format(scheme=scheme,
                                                    host=request.get_host())
    ctx = Context(context)
    msg = EmailMultiAlternatives(
        subject,
        get_template(template).render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [recipient]
    )
    msg.attach_alternative(get_template(template_html).render(ctx), 'text/html')
    msg.send()
