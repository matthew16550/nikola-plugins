This plugin converts [PlantUML](https://plantuml.com/) files to SVG, PNG or TXT (Ascii Art) files.

There is also a [plantuml_markdown](https://plugins.getnikola.com/#plantuml_markdown) plugin which supports
PlantUML inside Markdown files.

The default configuration will output all `*.puml` files under the `pages` dir as SVG files.

Developed against PlantUML version 1.2020.23.  Probably works with some earlier versions.

# Unicode

The plugin expects PlantUML files to be encoded with UTF-8.

# Known Issues

- It's slow!  Every PlantUML rendering uses a new Java process, on my laptop it takes 4-8 seconds per file.
  I have some ideas to speed this up, and they may be available in future plugin versions.

- Changes to files included via `!include ...` will NOT trigger a rebuild.
  Instead, you could include them via `PLANTUML_ARGS` and those will trigger a rebuild.

- `nikola auto` does not watch dirs in `PLANTUML_FILES` or files included via `PLANTUML_ARGS` / `!include`.
  As a workaround you could put PlantUML files under any dir listed in `POSTS` or `PAGES` because those dirs
  are watched.
  (Use `.iuml` suffix for include files to prevent them matching the `*.puml` wildcard in `PLANTUML_FILES`)

- The line number in PlantUML error messages is one higher than the actual error location.
  Suspect a bug in PlantUML.

- The file name in PlantUML error messages is always `string` rather than the actual problem file.
  PlantUML does this when input is piped via stdin, which as a compromise for simplicity we always do.
