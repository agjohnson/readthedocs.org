from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _, ugettext

from projects.models import Project


class Bookmark(models.Model):
    project = models.ForeignKey(Project, verbose_name=_('Project'),
                                related_name='bookmarks', null=True)
    user = models.ForeignKey(User, verbose_name=_('User'),
                             related_name='bookmarks')
    date = models.DateTimeField(_('Date'), auto_now_add=True)
    url = models.CharField(_('URL'), max_length=255)
    desc = models.TextField(_('Description'), null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return ugettext("Bookmark {url} for {user} ({pk})".format(
            url=self.url,
            user=self.user,
            pk=self.pk,
        ))

    def get_absolute_url(self):
        return self.url
