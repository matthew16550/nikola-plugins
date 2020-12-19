Markdown compiler plugin to support [PlantUML](https://plantuml.com/).

Installation
============

Enable the plugin by adding `plantuml_markdown` anywhere BEFORE `fenced_code` in `MARKDOWN_EXTENSIONS` e.g.

    MARKDOWN_EXTENSIONS = ['plantuml_markdown', 'fenced_code', 'codehilite']

The [plantuml](https://plugins.getnikola.com/#plantuml) plugin must also be installed and configured.

Usage
=====

Diagram in the page:

    ``` plantuml
    A -> B : foo
    ```

Listing of PlantUML code:

    ``` { .plantuml listing }
    A -> B : foo
    ```

Diagram with code listing on the right:

    ``` { .plantuml svg+listing }
    A -> B : foo
    ```

Diagram with code listing on the left:

    ``` { .plantuml listing+svg }
    A -> B : foo
    ```

[Fenced Code Block Attributes](https://python-markdown.github.io/extensions/fenced_code_blocks/#attributes)
can also be used.  e.g.

    ``` { .plantuml #my_id svg+listing linenums=y }
    A -> B : foo
    ```

Specify a common prefix for all subsequent PlantUML blocks in the page:

    ``` plantuml_prefix
    skinparam ParticipantBorderColor DeepSkyBlue
    skinparam ParticipantBackgroundColor DodgerBlue
    ```

Known Issues
============

- Changes to include files (`!include ...` or `-I...` in `PLANTUML_ARGS`/ `PLANTUML_MARKDOWN_SVG_ARGS`)
  will NOT trigger a rebuild of associated markdown files. You will need to force a rebuild (`nikola build -a`).
