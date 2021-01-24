import os
import subprocess
from itertools import chain
from logging import DEBUG
from os import getenv
from pathlib import Path
from threading import Lock
from typing import List, Optional, Sequence, Tuple

from nikola import utils
from nikola.log import get_logger
from nikola.plugin_categories import Task
from nikola.utils import req_missing

DEFAULT_PLANTUML_ARGS = []

DEFAULT_PLANTUML_DEBUG = False

DEFAULT_PLANTUML_EXEC = ['plantuml']

DEFAULT_PLANTUML_FILES = (
    ('plantuml/*.puml', 'plantuml', '.svg', ['-tsvg']),
)

DEFAULT_PLANTUML_CONTINUE_AFTER_FAILURE = False

DEFAULT_PLANTUML_RUNNER = 'exec'


# TODO when 3.5 support is dropped
# - Use capture_output arg in subprocess.run()
# - Change typing annotations

class PlantUmlTask(Task):
    """Renders PlantUML files"""

    name = 'plantuml'

    _common_args = ...  # type: List[str]
    plantuml_manager = ...  # Optional[PlantUmlManager]

    def set_site(self, site):
        super().set_site(site)
        self._common_args = list(site.config.get('PLANTUML_ARGS', DEFAULT_PLANTUML_ARGS))

        runner = site.config.get('PLANTUML_RUNNER', DEFAULT_PLANTUML_RUNNER)
        if runner == 'exec':
            self.plantuml_manager = ExecPlantUmlManager(site)
        elif runner == 'jpype':
            self.plantuml_manager = JPypePlantUmlManager(site)
        else:
            raise ValueError('Unknown PLANTUML_RUNNER "{}"'.format(runner))

    def gen_tasks(self):
        yield self.group_task()

        filters = self.site.config['FILTERS']
        output_folder = self.site.config['OUTPUT_FOLDER']
        plantuml_files = self.site.config.get('PLANTUML_FILES', DEFAULT_PLANTUML_FILES)
        output_path = Path(output_folder)

        # Logic derived from nikola.plugins.misc.scan_posts.ScanPosts.scan()
        for pattern, destination, extension, args in plantuml_files:
            combined_args = self._common_args + args

            kw = {
                'combined_args': combined_args,
                'filters': filters,
                'output_folder': output_folder,
            }

            # TODO figure out exactly what the PlantUML include patterns do and expand them similarly here
            includes = list(set(a[2:] for a in combined_args if a.startswith('-I') and '*' not in a and '?' not in a))

            pattern = Path(pattern)
            root = pattern.parent

            for src in root.rglob(pattern.name):
                dst = output_path / destination / src.relative_to(root).parent / src.with_suffix(extension).name
                dst_str = str(dst)
                task = {
                    'basename': self.name,
                    'name': dst_str,
                    'file_dep': includes + [str(src)],
                    'targets': [dst_str],
                    'actions': [(self.render_file, [src, dst, combined_args + ['-filename', src.name]])],
                    'uptodate': [utils.config_changed(kw, 'plantuml:' + dst_str)],
                    'clean': True,
                }
                yield utils.apply_filters(task, filters)

    def render_file(self, src: Path, dst: Path, args: Sequence[str]) -> bool:
        output, error = self.plantuml_manager.render(src.read_bytes(), args)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(output)

        if not error:
            return True

        # Note we never "continue" when output is empty because that likely means PlantUML failed to start
        if len(output) and self.plantuml_manager.continue_after_failure:
            self.logger.warning("'%s': %s", src, error)
            return True

        raise Exception(error)


def process_arg(arg: str) -> str:
    return arg.replace('%site_path%', os.getcwd())


class PlantUmlManager:
    """PlantUmlManager is used by 'plantuml' and 'plantuml_markdown' plugins"""

    def __init__(self, site) -> None:
        self.continue_after_failure = site.config.get('PLANTUML_CONTINUE_AFTER_FAILURE', DEFAULT_PLANTUML_CONTINUE_AFTER_FAILURE)
        self.logger = get_logger('plantuml_manager')
        if site.config.get('PLANTUML_DEBUG', DEFAULT_PLANTUML_DEBUG):
            self.logger.level = DEBUG

    def render(self, source: bytes, args: Sequence[str]) -> Tuple[bytes, Optional[str]]:
        raise NotImplementedError


class ExecPlantUmlManager(PlantUmlManager):
    """PlantUmlManager that runs PlantUML in a subprocess"""

    def __init__(self, site) -> None:
        super().__init__(site)
        self._exec = site.config.get('PLANTUML_EXEC', DEFAULT_PLANTUML_EXEC)

    def render(self, source: bytes, args: Sequence[str]) -> Tuple[bytes, Optional[str]]:
        command = list(map(process_arg, chain(self._exec, args, ['-pipe', '-stdrpt'])))

        self.logger.debug('render() exec: command=%s\n  source=%s', command, source)

        result = subprocess.run(command, input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            return result.stdout, None

        try:
            details = str(result.stderr, encoding='utf8').rstrip()
        except Exception:  # noqa
            details = str(result.stderr)

        return result.stdout, "PlantUML error (return code {}): {}".format(result.returncode, details)


class JPypePlantUmlManager(PlantUmlManager):
    """PlantUmlManager that uses JPype to run PlantUML in the Python process"""

    def __init__(self, site) -> None:
        super().__init__(site)
        plugin_info = site.plugin_manager.getPluginByName('jpype', category='ConfigPlugin')
        if not plugin_info:
            req_missing("jpype plugin", "use the plantuml plugin with PLANTUML_RUNNER option set to 'jpype'", python=False)
        self._lock = Lock()
        self._jpype_plugin = plugin_info.plugin_object
        self._wrapper: Optional[JavaWrapper] = None

    def render(self, source: bytes, args: Sequence[str]) -> Tuple[bytes, Optional[str]]:
        with self._lock:
            if not self._wrapper:
                self._jpype_plugin.ensure_jvm_started()
                self._wrapper = JavaWrapper()
        self.logger.debug('render() jpype: args=%s\n  source=%s', args, source)
        return self._wrapper.render(source, args)


class JavaWrapper:
    """
    JavaWrapper is the only place in this plugin that uses Java / JPype.

    The Java imports below require a running JVM but it's slow to start so this class is only used when needed.
    """

    def __init__(self) -> None:
        import jpype.imports  # noqa
        from java.lang import Thread  # noqa
        from java.io import ByteArrayInputStream, ByteArrayOutputStream, PrintStream  # noqa
        from net.sourceforge.plantuml import ErrorStatus, Option, Pipe  # noqa

        self.ByteArrayInputStream = ByteArrayInputStream
        self.ByteArrayOutputStream = ByteArrayOutputStream
        self.ErrorStatus = ErrorStatus
        self.Option = Option
        self.Pipe = Pipe
        self.PrintStream = PrintStream
        self.Thread = Thread

    def render(self, source: bytes, args: Sequence[str]) -> Tuple[bytes, Optional[str]]:
        baos = self.ByteArrayOutputStream(65536)
        error_status = self.ErrorStatus.init()
        pipe = self.Pipe(self.Option(args), self.PrintStream(baos), self.ByteArrayInputStream(source), 'utf8')
        pipe.managePipe(error_status)  # this call does the rendering
        rendered = bytes(baos.toByteArray())
        # TODO more error details
        error = "PlantUML error (return code {})".format(error_status.getExitCode()) if error_status.getExitCode() else None
        self.Thread.detach()  # If we dont do this then the JVM does not shutdown after a multithreaded build and Nikola hangs forever
        return rendered, error
