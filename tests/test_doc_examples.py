from __future__ import annotations

import pytest
import doctest
import shelldoctest
import os, re

from pathlib import Path
from dataclasses import dataclass, field
from textwrap import dedent, indent
from traceback import format_exception
from typing import List

ROOT_DIR = Path(__file__).parents[1]
DOC_DIR = ROOT_DIR / 'docs'
SRC_DIR = ROOT_DIR / 'byoc'

@dataclass
class Document:
    path: Path
    lineno: int
    lines: List[str]

    @property
    def relpath(self):
        return self.path.relative_to(ROOT_DIR)

@dataclass
class Example:
    id: str
    doc: Document
    lineno: int
    indent: int
    blocks: List[Block] = field(default_factory=list)

@dataclass
class Block:
    name: str
    indent: int
    lines: List[str] = field(default_factory=list)
    lineno: int = 0

def find_doc_examples():
    yield from find_rst_doc_examples()
    yield from find_py_doc_examples()

def find_rst_doc_examples():
    for path in DOC_DIR.glob('**/*.rst'):
        with open(path) as f:
            lines = f.readlines()

        doc = Document(
                path=path,
                lineno=1,
                lines=lines,
        )
        yield from parse_doc_examples(doc)

def find_py_doc_examples():

    # Use a very naive algorithm to detect docstrings.  This relies heavily on 
    # the project using a consistent format for docstrings, namely:
    # 
    # - Always use triple double quotes.
    # - Always put the quotes on their own line.
    # - Don't ever use triple double quotes for ordinary multi-line strings.
    # 
    # Note that the reason why we need to parse docstrings is to prevent 
    # examples in adjacent functions from sharing state.  I considered using 
    # the `ast` module to do this, but decided against because (i) the AST 
    # changes between version of python and (ii) the AST doesn't necessarily 
    # provide accurate line numbers.

    for path in SRC_DIR.glob('**/*.py'):
        doc = None

        with open(path) as f:
            for lineno, line in enumerate(f, 1):

                if doc is None:
                    if line.strip().startswith('"""'):
                        doc = Document(
                                path=path,
                                lineno=lineno + 1,
                                lines=[],
                        )

                else:
                    if line.strip().startswith('"""'):
                        yield from parse_doc_examples(doc)
                        doc = None
                    else:
                        doc.lines.append(line)

        assert doc is None

def parse_doc_examples(doc):
    # States:
    # - text: default state; unknown text that's not part of any test.
    # - text-block: a code block found directly within the text.
    # - tab: A tab directive.  This begins a group of related snippets.
    # - tab-block: A code block found within a tab directive.

    curr_state = 'text'
    curr_example = None
    curr_block = None

    examples = []

    directive_pattern = r'^(?P<indent>\s*)\.\. (?P<directive>{})::(\s(?P<arg>.*))?'
    tab_pattern = directive_pattern.format('tab')
    block_pattern = directive_pattern.format('code-block')
    indent_pattern = r'^(?P<indent>\s*).*'

    def parse_line(line, lineno):
        nonlocal curr_block
        nonlocal curr_example

        if not line.strip():
            return curr_state

        example_kwargs = dict(
                id=f'{doc.relpath}:{lineno}',
                doc=doc,
                lineno=lineno, 
        )

        if curr_state == 'text':

            # Found tab: create a new example
            m = re.match(tab_pattern, line)
            if m:
                curr_example = Example(
                        **example_kwargs,
                        indent=m['indent'],
                )
                curr_block = Block(
                        name=m['arg'],
                        indent=m['indent'],
                )
                curr_example.blocks.append(curr_block)
                examples.append(curr_example)
                return 'tab'

            # Found code block: if there is an existing example, add to it; 
            # otherwise create a new example
            m = re.match(block_pattern, line)
            if m:
                if curr_example is None:
                    curr_example = Example(
                        **example_kwargs,
                        indent=m['indent'],
                    )
                    examples.append(curr_example)

                curr_block = Block(m['arg'] or 'python', m['indent'])
                curr_example.blocks.append(curr_block)
                return 'text-block'

            # Otherwise: stay in 'text' state
            return 'text'

        if curr_state == 'tab':

            # Found code block within tab:
            m = re.match(block_pattern, line)
            if m:
                if len(m['indent']) > len(curr_example.indent):
                    return 'tab-block'

            if not line.strip():
                return curr_state

            raise AssertionError(f"{doc.path}:{lineno}: unexpected content in '.. tab::' directive: {line!r}\nexpected: '.. code-block::'")

        if curr_state == 'text-block':
            assert curr_block

            # Found end of code block: back to text mode
            m = re.match(indent_pattern, line)
            if len(m['indent']) <= len(curr_block.indent):
                return 'text'

            if not curr_block.lines:
                curr_block.lineno = lineno

            curr_block.lines.append(line)
            return 'text-block'

        if curr_state == 'tab-block':
            assert curr_block

            # Found tab: add to current example
            m = re.match(tab_pattern, line)
            if m:
                curr_block = Block(m['arg'], m['indent'])
                curr_example.blocks.append(curr_block)
                return 'tab'

            # Found end of code block: back to text mode
            m = re.match(indent_pattern, line)
            if len(m['indent']) <= len(curr_example.indent):
                curr_example = None
                return 'text'

            if len(m['indent']) <= len(curr_block.indent):
                raise AssertionError(f"{doc.path}:{lineno}: unexpected content in '.. tab:: directive: {line!r}")

            if not curr_block.lines:
                curr_block.lineno = lineno

            curr_block.lines.append(line)
            return 'tab-block'

    for lineno, line in enumerate(doc.lines, doc.lineno):
        curr_state = parse_line(line, lineno)

    return examples


@pytest.mark.parametrize(
        'example', [
            pytest.param(ex, id=ex.id)
            for ex in find_doc_examples()
        ],
)
def test_doc_examples(tmp_path, example):
    runner = doctest.DocTestRunner()
    parsers = {
            'python': doctest.DocTestParser(),
            'python-console': doctest.DocTestParser(),
            'bash': shelldoctest.ShellDocTestParser(),
    }
    commands = [
            doctest.Example(f'chdir({str(tmp_path)!r})', ''),
    ]

    for block in example.blocks:
        source = dedent(''.join(block.lines))
        source = source.replace('/path/to', str(tmp_path))

        if block.name in parsers:
            parser = parsers[block.name]
            commands_i = parser.get_examples(source, example.id)

            for command in commands_i:
                command.lineno += block.lineno

            commands += commands_i

        else:
            file_path = tmp_path / block.name
            file_path.write_text(source)

    class PytestRunner(doctest.DocTestRunner):

        def report_failure(self, out, test, example, got):
            pytest.fail(f"doctest gave unexpected output\nexample:\n{indent(example.source, '  ')}\nwanted:\n{indent(example.want, '  ')}\ngot:\n{indent(got, '  ')}\nlocation:\n  {test.name}")

        def report_unexpected_exception(self, out, test, example, exc_info):
            pytest.fail(f"doctest raised unexpected exception\nexample:\n{indent(example.source, '  ')}\nerror:\n{indent(''.join(format_exception(*exc_info)), '  ')}\nlocation:\n  {test.name}")

    class EvalOutputChecker(doctest.OutputChecker):

        def check_output(self, want, got, optionflags):
            if super().check_output(want, got, optionflags):
                return True

            # If the strings don't match, see if they compare equal when 
            # evaluated.  This accounts for things like the non-deterministic 
            # order in which items are stored in sets.
            try:
                return eval(want) == eval(got)
            except Exception:
                return False

    globals = {
            'chdir': os.chdir,
            'shell': shelldoctest.shell,
    }
    tests = doctest.DocTest(commands, globals, example.id, example.doc.path, example.lineno, None)

    runner = PytestRunner(
            checker=EvalOutputChecker(),
            optionflags=doctest.IGNORE_EXCEPTION_DETAIL,
    )
    runner.run(tests)
