import os
from pathlib import Path
from shutil import copyfile
from typing import Dict

import pytest
from approvaltests import ApprovalException, FileApprover, get_default_reporter
from approvaltests.pytest.namer import PyTestNamer
from pytest import fixture

from tests.base import execute_plugin_tasks
from v8.plantuml.plantuml import PlantUmlTask

BAD_PLANTUML = """
A -> B
B -> C
foo bar
""".lstrip()

GOOD_PLANTUML = """
A -> B : test \u2713
A -> B : defined=$defined
""".lstrip()

CHECK_MARK = '\u2713'  # for unicode testing


def test_render_png_file(verify_plantuml_file):
    verify_plantuml_file('skinparam dpi 300\n' + GOOD_PLANTUML, 'foo', 'png')  # TODO 300 is a temporary kludge


def test_render_png_file_error(verify_plantuml_file):
    verify_plantuml_file(BAD_PLANTUML, 'foo', 'png')


def test_render_svg_file(verify_plantuml_file):
    verify_plantuml_file(GOOD_PLANTUML, '', 'svg')


def test_render_svg_file_error(verify_plantuml_file):
    verify_plantuml_file(BAD_PLANTUML, '', 'svg')


def test_render_txt_file(verify_plantuml_file):
    verify_plantuml_file(GOOD_PLANTUML, 'foo/bar', 'txt')


def test_render_txt_file_error(verify_plantuml_file):
    verify_plantuml_file(BAD_PLANTUML, 'foo/bar', 'txt')


@fixture
def verify_plantuml_file(monkeypatch, tmp_path, verify_file):
    def f(text, destination, output_format):
        monkeypatch.chdir(tmp_path)

        (tmp_path / 'pages').mkdir()
        (tmp_path / 'pages' / 'test.puml').write_text(text, encoding='utf8')
        (tmp_path / 'pages' / 'includes').mkdir()
        (tmp_path / 'pages' / 'includes' / 'include1.iuml').write_text('A -> B : this is include1 ' + CHECK_MARK, encoding='utf8')
        (tmp_path / 'pages' / 'includes' / 'include2.iuml').write_text('A -> B : this is include2 ' + CHECK_MARK, encoding='utf8')

        plugin = create_plugin({
            'PLANTUML_ARGS': [
                '-c!$defined="should-be-overridden-by-specific-define"',
                '-chide footbox',
                '-nometadata',
                '-Ipages/includes/include1.iuml',
                '-SDefaultFontName=DejaVu Sans',
                '-SShadowing=false',
            ],
            'PLANTUML_FILES': (
                ('pages/*.puml', destination, output_format, [
                    '-c!$defined="FOO \u2713"',
                    '-Ipages/includes/include2.iuml',
                ]),
            ),
            'PLANTUML_RENDER_ERRORS': True,
        })

        # When
        execute_plugin_tasks(plugin)

        # Then
        verify_file((tmp_path / 'output' / destination / 'test').with_suffix('.' + output_format))

    return f


@pytest.mark.parametrize('config, expected_targets', [
    # Test the default config
    (
            {},
            [
                'output/test1.svg',
                'output/foo/test2.svg',
            ]
    ),
    # Test multiple rules & subdirs
    (
            {
                'PLANTUML_FILES': (
                        ('pages/*.puml', '', 'txt', []),
                        ('other/diagrams/*.puml', 'foo/bar', 'png', []),
                ),
            },
            [
                'output/test1.txt',
                'output/foo/test2.txt',
                'output/foo/bar/test3.png',
                'output/foo/bar/baz/test4.png',
            ]
    )
])
def test_gen_tasks_targets(config, expected_targets, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    for f in [
        'pages/test1.puml',
        'pages/foo/test2.puml',
        'other/diagrams/test3.puml',
        'other/diagrams/baz/test4.puml',
    ]:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).touch()

    plugin = create_plugin(config)

    # When
    tasks = plugin_tasks(plugin)

    # Then
    assert sorted((task['targets'][0] for task in tasks), reverse=True) == expected_targets


def test_gen_tasks_deps(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    plugin = create_plugin({
        'PLANTUML_ARGS': [
            '-Iincludes/include1.iuml',
            '-Iincludes/include2.iuml'
        ],
        'PLANTUML_FILES': (
            ('*.puml', '', 'txt', ['-Iincludes/include3.iuml']),
        )
    })

    (tmp_path / 'foo.puml').touch()

    # When
    tasks = plugin_tasks(plugin)

    # Then
    assert tasks[0]['file_dep'] == [
        'includes/include1.iuml',
        'includes/include2.iuml',
        'includes/include3.iuml',
        Path('foo.puml'),
    ]


def create_plugin(config: Dict):
    plugin = PlantUmlTask()
    plugin.set_site(FakeSite(config))
    return plugin


class FakeSite:
    debug = True

    def __init__(self, config: Dict):
        self.config = {
            'FILTERS': {},
            'OUTPUT_FOLDER': 'output',
            'PLANTUML_DEBUG': True,
        }
        self.config.update(config)
        if 'PLANTUML_EXEC' in os.environ:
            self.config['PLANTUML_EXEC'] = os.environ['PLANTUML_EXEC'].split()


def plugin_tasks(plugin):
    tasks = list(plugin.gen_tasks())
    assert tasks.pop(0) == plugin.group_task()
    return tasks


@fixture
def verify_file(request):
    def f(path: Path):
        namer = PyTestNamer(request, path.suffix)
        approved = namer.get_approved_filename()
        received = namer.get_received_filename()
        copyfile(path, received)
        if not FileApprover().verify_files(approved, received, get_default_reporter()):
            raise ApprovalException("Approval Mismatch")

    return f
