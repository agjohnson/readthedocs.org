import logging

from django.db.models.signals import post_save
from actstream import action

from .models import Build, Version


log = logging.getLogger(__name__)


def generate_build_activity(sender, instance, created, **kwargs):
    '''Handle build model activity

    Accepts arguments from :py:func:`djagno.db.models.signals.post_save`
    '''
    if created:
        action.send(instance, verb='triggered', target=instance.project)


def generate_version_activity(sender, instance, created, **kwargs):
    '''Handle version model activity

    Accepts arguments from :py:func:`djagno.db.models.signals.post_save`
    '''
    if created:
        action.send(instance, verb='imported', target=instance.project)


post_save.connect(generate_build_activity, sender=Build)
post_save.connect(generate_version_activity, sender=Version)
