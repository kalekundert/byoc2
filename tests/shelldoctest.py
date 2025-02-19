"""
Shell Doctest module.

:Copyright: (c) 2009, the Shell Doctest Team All rights reserved.
:license: BSD, see LICENSE for more details.
"""

import doctest
import subprocess
import re

master = None
_EXC_WRAPPER = 'shell("%s")'

def shell(cmd):
    p = subprocess.run(
            cmd,
            shell=True,
            universal_newlines=True,  # python3.6-compatible alias for 'text'
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
    )
    print((p.stdout + p.stderr).rstrip())

class ShellExample(doctest.Example):
    def __init__(self, source, want, exc_msg=None, lineno=0, indent=0,
                     label=None,
                     options=None):
        doctest.Example.__init__(self, source, want, exc_msg=None, lineno=lineno, indent=indent,
                     options=None)
        self.label = label

class ShellDocTestParser(doctest.DocTestParser):
    _PROMPT = "$"
    _EXC_WRAPPER = _EXC_WRAPPER
    _EXAMPLE_RE = re.compile(r'''\
        # Source consists of a PS1 line followed by zero or more PS2 lines.
        (?P<source>
            (?:^  (?P<indent> [ ]*))                   # PS0 line: indent
            (?:   \[(?P<label>.+)\]\n)?                # PS0 line: label
            (?:   (?P<user>[\w]*)@(?P<host>[\w\.-]*)\n)? # PS0 line: user@host
            (?:   [ ]* \$ .*)                          # PS1 line
            (?:\n [ ]* \. [ ].*)*)                        # PS2 lines
        \n?
        # Want consists of any non-blank lines that do not start with PS1.
        (?P<want> (?:(?![ ]*$)    # Not a blank line
                     (?![ ]*\$)   # Not a line starting with PS1
                     .*$\n?       # But any other line
                  )*)
        ''', re.MULTILINE | re.VERBOSE)

    def parse(self, string, name='<string>'):
        string = string.expandtabs()
        min_indent = self._min_indent(string)
        if min_indent > 0:
            string = '\n'.join([l[min_indent:] for l in string.split('\n')])
        output = []
        charno, lineno = 0, 0
        for m in self._EXAMPLE_RE.finditer(string):
            output.append(string[charno:m.start()])
            lineno += string.count('\n', charno, m.start())
            (source, options, want, exc_msg) = \
                     self._parse_example(m, name, lineno)
            if not self._IS_BLANK_OR_COMMENT(source):
                source = source.replace("\n","; ")
                user = m.group('user')
                host = m.group('host')
                if host:
                    if user:
                        cmd_base = "ssh %(user)s@%(host)s '%(source)s'"
                    else:
                        cmd_base = "ssh %(host)s '%(source)s'"
                    source = cmd_base % vars()

                example = ShellExample(
                        self._EXC_WRAPPER % source.replace("\n","; "),
                        want,
                        exc_msg,
                        lineno=lineno,
                        label=m.group('label'),
                        indent=min_indent+len(m.group('indent')),
                        options=options,
                )
                output.append(example)

            lineno += string.count('\n', m.start(), m.end())
            charno = m.end()
        output.append(string[charno:])
        return output

    def _parse_example(self, m, name, lineno):
        indent = len(m.group('indent'))
        source_lines = [sl for sl in m.group('source').split('\n') if sl.strip()[1] == " "]
        self._check_prompt_blank(source_lines, indent, name, lineno)
        self._check_prefix(source_lines[1:], ' '*indent + '.', name, lineno)
        source = '\n'.join([sl[indent+len(self._PROMPT)+1:] for sl in source_lines])
        want = m.group('want')
        want_lines = want.split('\n')
        if len(want_lines) > 1 and re.match(r' *$', want_lines[-1]):
            del want_lines[-1]
        self._check_prefix(want_lines, ' '*indent, name,
                           lineno + len(source_lines))
        want = '\n'.join([wl[indent:] for wl in want_lines])
        m = self._EXCEPTION_RE.match(want)
        if m:
            exc_msg = m.group('msg')
        else:
            exc_msg = None
        options = self._find_options(source, name, lineno)
        return source, options, want, exc_msg

    def _check_prompt_blank(self, lines, indent, name, lineno):
        for i, line in enumerate(lines):
            if len(line) >= indent+len(self._PROMPT)+1 and line[indent+len(self._PROMPT)] != ' ':
                raise ValueError('line %r of the docstring for %s '
                                 'lacks blank after %s: %r' %
                                 (lineno+i+1, name,
                                  line[indent:indent+len(self._PROMPT)], line))

