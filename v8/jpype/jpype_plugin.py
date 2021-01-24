from logging import DEBUG
from textwrap import dedent
from threading import Lock

from jpype import isJVMStarted, startJVM  # noqa

from nikola.plugin_categories import ConfigPlugin

DEFAULT_JPYPE_CLASSPATH = []
DEFAULT_JPYPE_DEBUG = False
DEFAULT_JPYPE_IGNORE_UNRECOGNIZED = False
DEFAULT_JPYPE_INTERRUPT = True
DEFAULT_JPYPE_JVM_ARGS = ['-Djava.awt.headless=true']


class JPypePlugin(ConfigPlugin):
    """Makes JPype available for use by other plugins"""

    name = 'jpype'

    def __init__(self):
        super().__init__()
        self._lock = Lock()

    def set_site(self, site):
        super().set_site(site)
        if self.site.config.get('JPYPE_DEBUG', DEFAULT_JPYPE_DEBUG):
            self.logger.level = DEBUG

    def ensure_jvm_started(self):
        with self._lock:
            if not isJVMStarted():
                args = self.site.config.get('JPYPE_JVM_ARGS', DEFAULT_JPYPE_JVM_ARGS)
                startJVM(
                    *args,
                    classpath=self.site.config.get('JPYPE_CLASSPATH', DEFAULT_JPYPE_CLASSPATH),
                    convertStrings=False,
                    ignoreUnrecognized=self.site.config.get('JPYPE_IGNORE_UNRECOGNIZED', DEFAULT_JPYPE_IGNORE_UNRECOGNIZED),
                    interrupt=self.site.config.get('JPYPE_INTERRUPT', DEFAULT_JPYPE_INTERRUPT),
                )

                if self.logger.isEnabledFor(DEBUG):
                    import jpype.imports  # noqa
                    from java.lang import System  # noqa
                    self.logger.debug(
                        dedent("""\
                            Started JVM
                              home:    : %s
                              name     : %s
                              version  : %s
                              classpath: %s
                              args     : %s
                        """),
                        System.getProperty('java.home'),
                        System.getProperty('java.vm.name'),
                        System.getProperty('java.runtime.version'),
                        System.getProperty('java.class.path'),
                        args
                    )
