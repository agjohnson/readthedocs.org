import csv
import re
from StringIO import StringIO

from projects.exceptions import ProjectImportError
from vcs_support.base import BaseVCS, VCSVersion


class Backend(BaseVCS):
    supports_tags = True
    fallback_branch = ''

    def update(self):
        super(Backend, self).update()
        cmd = self.run('bzr', 'status')
        if cmd.successful():
            self.up()
        else:
            self.clone()

    def up(self):
        cmd = self.run('bzr', 'revert')
        if cmd.failed():
            raise ProjectImportError(
                ("Failed to get code from '%s' (bzr revert): %s"
                 % (self.repo_url, cmd.exit_code))
            )
        up_output = self.run('bzr', 'up')
        if up_output[0] != 0:
            raise ProjectImportError(
                ("Failed to get code from '%s' (bzr up): %s"
                 % (self.repo_url, cmd.exit_code))
            )
        return up_output

    def clone(self):
        self.make_clean_working_dir()
        cmd = self.run('bzr', 'checkout', self.repo_url, '.')
        if cmd.failed():
            raise ProjectImportError(
                ("Failed to get code from '%s' (bzr checkout): %s"
                 % (self.repo_url, cmd.exit_code))
            )

    @property
    def tags(self):
        cmd = self.run('bzr', 'tags')
        # error (or no tags found)
        if cmd.failed():
            return []
        return self.parse_tags(stdout)

    def parse_tags(self, data):
        """
        Parses output of bzr tags, eg:

            0.1.0                171
            0.1.1                173
            0.1.2                174
            0.2.0-pre-alpha      177

        Can't forget about poorly formatted tags or tags that lack revisions,
        such as:

            3.3.0-rc1            ?
            tag with spaces      123
        """
        # parse the lines into a list of tuples (commit-hash, tag ref name)
        squashed_data = re.sub(r' +', ' ', data)
        raw_tags = csv.reader(StringIO(squashed_data), delimiter=' ')
        vcs_tags = []
        for row in raw_tags:
            name = ' '.join(row[:-1])
            commit = row[-1]
            if commit != '?':
                vcs_tags.append(VCSVersion(self, commit, name))
        return vcs_tags

    @property
    def commit(self):
        cmd = self.run('bzr', 'revno')
        return cmd.output['output'].strip()

    def checkout(self, identifier=None):
        super(Backend, self).checkout()
        self.update()
        if not identifier:
            return self.up()
        else:
            return self.run('bzr', 'switch', identifier)
