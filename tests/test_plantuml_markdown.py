import os
from textwrap import dedent

import pytest
from approvaltests import verify_with_namer
from approvaltests.pytest.namer import PyTestNamer
from markdown import Markdown
from markdown.extensions.fenced_code import FencedBlockPreprocessor
from pytest import fixture

from v8.plantuml.plantuml import PlantUmlTask
from v8.plantuml_markdown.plantuml_markdown import PlantUmlMarkdownExtension, first_line_for_listing_block


def test_svg(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ```plantuml
    A -> B : foo
    ```
    """)


def test_with_other_markdown(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    # A Diagram
    ``` plantuml
    A -> B : foo
    ```
    
    # Some Python
    ``` python
    x = 1 + 2
    ```
    """)


def test_listing(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ```{ .plantuml listing }
    participant A
    participant B
    ```
    """)


def test_line_numbering(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ```{ .plantuml #baz listing linenums=y linenostart=10 }
    participant A
    participant B
    ```
    """)


def test_svg_and_listing(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ``` { .plantuml svg+listing }
    participant A
    ```
    """)


def test_listing_and_svg(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ``` { .plantuml listing+svg }
    participant A
    ```
    """)


def test_prefix(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ```plantuml_prefix
    skinparam ParticipantBorderColor DeepSkyBlue
    skinparam ParticipantBackgroundColor DodgerBlue
    ```
    
    ```plantuml
    participant A
    ```

    ```plantuml
    participant B
    ```
    """)


def test_error(verify_plantuml_markdown):
    verify_plantuml_markdown("""
    ```plantuml
    this is bad
    ```
    """)


@pytest.mark.parametrize('line, expected', [
    ("```plantuml", "``` text"),
    ("```.plantuml", "``` text"),
    ("```plantuml hl_lines='3 4'", "``` text hl_lines=\"3 4\""),
    ("``` { .plantuml .foo #bar linenums=y hl_lines=\"3 4\" }", "``` { .text anchor_ref=bar linenums=y hl_lines=\"3 4\" }"),
])
def test_first_line_for_listing_block(line, expected):
    match = FencedBlockPreprocessor.FENCED_BLOCK_RE.match(line + "\n```")
    assert match
    assert first_line_for_listing_block(match) == expected


@fixture
def verify_plantuml_markdown(request):
    def f(text):
        text = dedent(text).lstrip()
        site = FakeSite()
        plantuml_task = PlantUmlTask()
        plantuml_task.set_site(site)
        extension = PlantUmlMarkdownExtension()
        extension.set_site(site)
        md = Markdown(extensions=[extension, 'fenced_code', 'codehilite'])
        extension.processor.set_plugin_manager(plantuml_task.plantuml_manager)

        # When
        body = md.convert(text)

        # Then
        html = html_page(body)  # put it in an html page so we can easily see it in a browser
        verify_with_namer(html, PyTestNamer(request, '.html'), encoding='utf8')

    return f


class FakeSite:
    debug = True

    def __init__(self):
        self.config = {
            'PLANTUML_DEBUG': True,
            'PLANTUML_RENDER_ERRORS': True,
            'PLANTUML_MARKDOWN_SVG_ARGS': [
                '-chide footbox',
                '-nometadata',
                '-SDefaultFontName=DejaVu Sans',
                '-SDefaultFontSize=17',
                '-SShadowing=false',
            ],
        }
        if 'PLANTUML_EXEC' in os.environ:
            self.config['PLANTUML_EXEC'] = os.environ['PLANTUML_EXEC'].split()


def html_page(body):
    return dedent('''
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://themes.getnikola.com/v8/base/demo/assets/css/rst_base.css" rel="stylesheet" type="text/css">
            <link href="https://themes.getnikola.com/v8/base/demo/assets/css/nikola_rst.css" rel="stylesheet" type="text/css">
            <link href="https://themes.getnikola.com/v8/base/demo/assets/css/code.css" rel="stylesheet" type="text/css">
            <link href="https://themes.getnikola.com/v8/base/demo/assets/css/theme.css" rel="stylesheet" type="text/css">
            <link href="data/plantuml_markdown/local.css" rel="stylesheet" type="text/css">
          </head>
          <body>
            {}
          </body>
        </html>
        ''').lstrip().format(body)
