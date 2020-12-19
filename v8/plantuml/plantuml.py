import os
import subprocess
from logging import DEBUG
from math import ceil
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

from nikola import Nikola, utils
from nikola.plugin_categories import Task

DEFAULT_ARGS = []

DEFAULT_DEBUG = False

DEFAULT_EXEC = ['plantuml']

DEFAULT_FILES = (
    ('pages/*.puml', '', 'svg', []),
)

DEFAULT_RENDER_ERRORS = True

FORMAT_ARG = {
    'png': '-tpng',
    'svg': '-tsvg',
    'txt': '-tutxt',
}


class PlantUmlTask(Task):
    """Renders PlantUML files"""

    name = 'plantuml'

    def __init__(self):
        super().__init__()
        self.plantuml_manager: Optional[PlantUmlManager] = None

    def set_site(self, site):
        super().set_site(site)
        self.plantuml_manager = PlantUmlManager(site)

    def gen_tasks(self):
        yield self.group_task()

        common_args = self.plantuml_manager.common_args
        filters = self.site.config['FILTERS']
        output_folder = self.site.config['OUTPUT_FOLDER']
        plantuml_files = self.site.config.get('PLANTUML_FILES', DEFAULT_FILES)
        output_path = Path(output_folder)

        # Logic derived from nikola.plugins.misc.scan_posts.ScanPosts.scan()
        for pattern, destination, output_format, args in plantuml_files:
            if output_format not in ['png', 'svg', 'txt']:
                raise Exception("Unsupported PlantUML output format '{}'".format(output_format))
            pattern = Path(pattern)
            root = pattern.parent
            combined_args = common_args + args
            includes = [a[2:] for a in combined_args if a.startswith('-I')]
            kw = {
                'combined_args': combined_args,
                'filters': filters,
                'output_folder': output_folder,
            }

            for src in root.rglob(pattern.name):
                dst = output_path / destination / src.relative_to(root).parent / src.with_suffix('.' + output_format).name
                dst_str = str(dst)
                task = {
                    'basename': self.name,
                    'name': dst_str,
                    'file_dep': includes + [src],
                    'targets': [dst_str],
                    'actions': [(self.render_file, [src, dst, output_format, combined_args])],
                    'uptodate': [utils.config_changed(kw, 'plantuml:' + dst_str)],
                    'clean': True,
                }
                yield utils.apply_filters(task, filters)

    def render_file(self, src: Path, dst: Path, output_format, args: List[str]) -> bool:
        output = self.plantuml_manager.render(src.read_bytes(), output_format, args)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(output)
        return True


class PlantUmlManager:
    """
    PlantUmlManager is used by "plantuml" & "plantuml_markdown" plugins
    """

    def __init__(self, site: Nikola):
        self.common_args = site.config.get('PLANTUML_ARGS', DEFAULT_ARGS)
        self._exec = site.config.get('PLANTUML_EXEC', DEFAULT_EXEC)
        self._logger = utils.get_logger('plantuml_manager')
        if site.config.get('PLANTUML_DEBUG', DEFAULT_DEBUG):
            self._logger.level = DEBUG
        self._render_errors = site.config.get('PLANTUML_RENDER_ERRORS', DEFAULT_RENDER_ERRORS)
        self._site = site

    # noinspection PyBroadException
    def render(self, source: bytes, output_format: str, args: List[str]) -> bytes:
        _exec = [e.replace('%site_path%', os.getcwd()) for e in self._exec]
        command = _exec + args + ['-pipe', '-stdrpt', FORMAT_ARG[output_format]]
        self._logger.debug('render() exec: %s\n%s', command, source)
        result = subprocess.run(command, capture_output=True, input=source)

        if result.returncode == 0:
            return result.stdout

        try:
            details = str(result.stderr, encoding='utf8').rstrip()
        except Exception:
            details = str(result.stderr)

        error = "PlantUML error (return code {}): {}".format(result.returncode, details)

        if not self._render_errors:
            raise Exception(error)

        self._logger.exception('Ignoring: %s', error)

        if output_format == 'png':
            return error_to_png(error)
        elif output_format == 'svg':
            return error_to_svg(error)
        else:
            return error.encode('utf8')


def error_to_png(error: str) -> bytes:
    import io
    from PIL import Image, ImageDraw
    size = ImageDraw.Draw(Image.new('RGB', (1, 1))).multiline_textsize(error)
    image = Image.new('RGB', (size[0] + 20, size[1] + 20), color=(0xdc, 0x35, 0x45))
    draw = ImageDraw.Draw(image)
    draw.multiline_text((10, 10), error, fill=(255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    return buf.getvalue()


def error_to_svg(error: str) -> bytes:
    # This whole function is kludgy because I don't know SVG very well.  Improvements welcome :-)
    lines = error.split('\n')
    text = '\n'.join('<tspan x="1em" dy="1.2em">{}</tspan>'.format(escape(line)) for line in lines)
    height = ceil(1.2 * (len(lines))) + 2
    width = max(len(line) for line in lines) + 2
    result = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
             '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}em" height="{}em">\n'.format(width, height) + \
             '<rect x="0" y="0" width="{}em" height="{}em" fill="#dc3545"/>\n'.format(width, height) + \
             '<text x="0" y="1em" font-family="monospace" fill="#ffffff">\n' + \
             text + '\n' + \
             '</text>\n' + \
             '</svg>'
    return result.encode('utf8')
