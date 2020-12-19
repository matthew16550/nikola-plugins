import re
from logging import Logger
from re import Match
from typing import List, Optional

from markdown import Markdown
from markdown.extensions import Extension
from markdown.extensions.attr_list import get_attrs
from markdown.extensions.fenced_code import FencedBlockPreprocessor

from nikola import Nikola
from nikola.plugin_categories import MarkdownExtension

DEFAULT_MARKDOWN_SVG_ARGS = []


class PlantUmlMarkdownExtension(MarkdownExtension, Extension):
    name = 'plantuml_markdown'

    def __init__(self):
        super().__init__()
        self.processor: Optional[PlantUmlMarkdownProcessor] = None

    def extendMarkdown(self, md: Markdown):
        try:
            self.processor = PlantUmlMarkdownProcessor(md, self.site, self.logger)
            md.preprocessors.register(self.processor, 'fenced_code_block_plantuml', 26)
            md.registerExtension(self)
        except TypeError as e:  # Kludge to avoid Extension._extendMarkdown() hiding of TypeErrors
            raise Exception(e)

    def reset(self):
        self.processor.reset()


# Extends FencedBlockPreprocessor but this only handles plantuml blocks,
# all other blocks will be handled elsewhere by the usual "fenced_code" extension.
class PlantUmlMarkdownProcessor(FencedBlockPreprocessor):
    def __init__(self, md: Markdown, site: Nikola, logger: Logger):
        super().__init__(md, {})
        self._logger = logger
        self._plantuml_args: Optional[List[str]] = None
        self._plantuml_manager = None
        self._plantuml_prefix = []
        self._site = site

    def _lazy_init(self):
        if not self._plantuml_manager:
            plantuml_plugin = self._site.plugin_manager.getPluginByName('plantuml', 'Task')
            if not plantuml_plugin:
                raise Exception("'plantuml' plugin is required")
            self.set_plugin_manager(plantuml_plugin.plugin_object.plantuml_manager)

    def set_plugin_manager(self, manager):
        self._plantuml_args = manager.common_args + self._site.config.get('PLANTUML_MARKDOWN_SVG_ARGS', DEFAULT_MARKDOWN_SVG_ARGS)
        self._plantuml_manager = manager

    def reset(self):
        self._plantuml_prefix = []

    def run(self, lines):
        def replace(match):
            lang, _id, classes, config = None, '', [], {}
            if match.group('attrs'):
                _id, classes, config = self.handle_attrs(get_attrs(match.group('attrs')))
                if classes:
                    lang = classes.pop(0)
            else:
                lang = match.group('lang')

            if lang == 'plantuml':
                return self.render_code_block(match, _id, classes, config)
            elif lang == 'plantuml_prefix':
                self._plantuml_prefix = ['-c' + line for line in match.group('code').split('\n')]
                return ''
            else:  # The normal 'fenced_code' plugin will process this later
                return match.group()

        return self.FENCED_BLOCK_RE.sub(replace, '\n'.join(lines)).split('\n')

    def render_code_block(self, match, _id, classes, config):
        def listing():
            return self.render_listing(match)

        def svg():
            return self.render_svg(match)

        div = '<div{}{}>'.format(
            ' id="{}"'.format(_id) if _id else '',
            ' classes="{}"'.format(' '.join(classes)) if classes else '',
        )

        if 'listing+svg' in config:
            html = [div] + listing() + svg() + ['</div>']
        elif 'svg+listing' in config:
            html = [div] + svg() + listing() + ['</div>']
        elif 'listing' in config:
            html = [div] + listing() + ['</div>']
        elif 'svg' in config:
            html = [div] + svg() + ['</div>']
        else:
            html = [div] + svg() + ['</div>']

        return self.md.htmlStash.store('\n'.join(html))

    def render_listing(self, match: Match) -> List[str]:
        lines = [first_line_for_listing_block(match)] + match.group().split('\n')[1:]
        html = super().run(lines)[1]
        return [
            '<div class="plantuml_listing" style="display: inline-block; vertical-align: top">',
            html,
            '</div>'
        ]

    def render_svg(self, match: Match) -> List[str]:
        self._lazy_init()
        args = self._plantuml_args + self._plantuml_prefix
        svg = self._plantuml_manager.render(match.group('code').encode('utf8'), 'svg', args)
        svg = str(svg[svg.index(b'<svg'):], encoding='utf8')  # Remove leading "<?xml version=..."
        return [
            '<div class="plantuml_diagram" style="display: inline-block; vertical-align: top">',
            svg,
            '</div>',
        ]


ID_OR_CLASS_RE = re.compile(' *([.#])([^ =]+) *')


def first_line_for_listing_block(match: Match) -> str:
    def replace(m: Match) -> str:
        return 'anchor_ref={} '.format(m.group(2)) if m.group(1) == '#' else ''

    attrs = match.group('attrs')
    attrs_without_id_or_classes = ID_OR_CLASS_RE.sub(replace, attrs) if attrs else ''

    return ''.join([
        match.group('fence'),
        ' {{ .text {}}}'.format(attrs_without_id_or_classes) if attrs_without_id_or_classes else ' text',
        ' hl_lines="{}"'.format(match.group('hl_lines')) if match.group('hl_lines') else '',
    ])
