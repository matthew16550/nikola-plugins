import os
from pathlib import Path
from shutil import copyfile
from typing import Dict

import pytest
from PIL import Image
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
title filename="%filename()"
participant "test \u2713"
participant "defined $defined"
""".lstrip()


def test_render_png_file(render_file, verify_image_file):
    file = render_file(GOOD_PLANTUML, 'foo', 'png')
    verify_image_file(file)


def test_render_png_file_error(render_file, verify_image_file):
    file = render_file(BAD_PLANTUML, 'foo', 'png')
    verify_image_file(file)


def test_render_svg_file(render_file, verify_file):
    file = render_file(GOOD_PLANTUML, '', 'svg')
    verify_file(file)


def test_render_svg_file_error(render_file, verify_file):
    file = render_file(BAD_PLANTUML, '', 'svg')
    verify_file(file)


def test_render_txt_file(render_file, verify_file):
    file = render_file(GOOD_PLANTUML, 'foo/bar', 'txt')
    verify_file(file)


def test_render_txt_file_error(render_file, verify_file):
    file = render_file(BAD_PLANTUML, 'foo/bar', 'txt')
    verify_file(file)


@fixture
def render_file(monkeypatch, tmp_path):
    def f(text, destination, output_format) -> Path:
        monkeypatch.chdir(tmp_path)

        (tmp_path / 'pages').mkdir()
        (tmp_path / 'pages' / 'test.puml').write_text(text, encoding='utf8')
        (tmp_path / 'pages' / 'includes').mkdir()
        (tmp_path / 'pages' / 'includes' / 'include1.iuml').write_text('participant "include1 \u2713"', encoding='utf8')
        (tmp_path / 'pages' / 'includes' / 'include2.iuml').write_text('participant "include2 \u2713"', encoding='utf8')

        plugin = create_plugin({
            'PLANTUML_ARGS': [
                '-c!$defined="should-be-overridden-by-specific-define"',
                '-chide footbox',
                '-nometadata',
                '-Ipages/includes/include1.iuml',
                '-SDefaultFontName=DejaVu Sans',
                '-SLifeLineStrategy=solid',
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

        execute_plugin_tasks(plugin)

        return (tmp_path / 'output' / destination / 'test').with_suffix('.' + output_format)

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
        copyfile(str(path), received)

        if not FileApprover().verify_files(approved, received, get_default_reporter()):
            raise ApprovalException("Approval Mismatch")

    return f


@fixture
def verify_image_file(request):
    # PlantUML in GitHub Actions and PlantUML in Docker on my laptop use different PNG compression levels, no idea why :-(
    # The files are not byte for byte matches but the images they contain are identical so we just compare that
    def f(path: Path):
        namer = PyTestNamer(request, path.suffix)
        approved = namer.get_approved_filename()
        received = namer.get_received_filename()
        copyfile(str(path), received)

        if not Path(approved).exists():
            Image.new('RGB', (1, 1)).save(approved)

        if Image.open(approved) == Image.open(received):
            os.remove(received)
        else:
            get_default_reporter().report(received, approved)
            raise ApprovalException("Images do not match")

    return f
