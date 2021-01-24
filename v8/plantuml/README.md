This plugin converts [PlantUML](https://plantuml.com/) files.

The default configuration will output all `*.puml` files found under the `plantuml` dir as SVG files.

Developed against PlantUML version 1.2020.24.  Probably works with some earlier versions.

PlantUML can be run as a subprocess or via [JPype](https://plugins.getnikola.com/#jpype).
JPype should be much faster than the subprocess way.  See `PLANTUML_RUNNER` in `conf.py.sample` for more details.

Parallel builds seem to work fine (e.g. `nikola build -n 3 -P thread`) and do speed things up.

Beware that includes are always relative to the site_dir, not relative to the current plant file.

# Unicode

The plugin expects PlantUML files to be encoded with UTF-8.

# Known Issues

- Changes to files included via `!include ...` or via a pattern (e.g. `-Ipath/to/*.iuml`) will NOT trigger a rebuild.
  Instead, if you include them explicitly in `PLANTUML_ARGS` (e.g. `-Ipath/to/foo.iuml`) then they will trigger a
  rebuild.

- `nikola auto` does not watch dirs in `PLANTUML_FILES` or files included via `PLANTUML_ARGS` / `!include`.
  As a workaround you could put PlantUML files under any dir listed in `POSTS` or `PAGES` because those dirs
  are watched.
  (Use `.iuml` suffix for include files to prevent them matching the `*.puml` wildcard in `PLANTUML_FILES`)

- If your file does not begin with `@start` then PlantUML prepends a line containing `@startuml` which causes 
  the line number in error messages to be one higher than the actual error location.

- The file name in PlantUML error messages is always `string` rather than the actual problem file.
  PlantUML does this when input is piped via stdin, which as a compromise for simplicity we always do.
  
- `nikola auto` with `PLANTUML_RUNNER='jpype'` will launch a new JVM for each rebuild.  Ideally we would reuse a single
  long-running JVM.  More thought is needed around this, perhaps using PlantUMLs "server" mode.
  