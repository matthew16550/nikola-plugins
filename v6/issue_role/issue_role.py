# -*- coding: utf-8 -*-

# Copyright © 2016 Lenz Grimmer

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from docutils import nodes
from docutils.parsers.rst import roles

from nikola.plugin_categories import RestExtension


class Plugin(RestExtension):
    """Plugin for issue role."""

    name = 'issue_role'

    def set_site(self, site):
        """Set Nikola site."""
        self.site = site
        roles.register_local_role('issue', IssueRole)
        global ISSUE_URL
        IssueRole.site = site
        return super(Plugin, self).set_site(site)


def IssueRole(name, rawtext, text, lineno, inliner,
              options={}, content=[]):
    """Replace Issue ID with URL to issue tracker

    Usage:

      :issue:`ISSUE_ID`

    """

    format_options = {
        'issue': text
    }
    issue_url = self.site.GLOBAL_CONTEXT['ISSUE_URL']
    return [nodes.reference(rawtext, text, refuri=issue_url.format(**format_options), *options)], []