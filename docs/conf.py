import byoc

## General

project = 'BYOC'
copyright = '2025, Kale Kundert'
version = byoc.__version__
release = byoc.__version__

master_doc = 'index'
source_suffix = '.rst'
templates_path = ['_templates']
exclude_patterns = ['_build']
html_static_path = ['_static']
default_role = 'any'
trim_footnote_reference_space = True
nitpicky = True

## Extensions

from autoclasstoc import Section, is_method, is_public, is_special

class PublicMethods(Section):
    key = 'public-methods'
    title = 'Public Methods:'

    def predicate(self, name, attr, meta):
        return is_method(name, attr) and is_public(name) and not is_special(name)

extensions = [
        'autoclasstoc',
        'myst_parser',
        'sphinx.ext.autodoc',
        'sphinx.ext.autosummary',
        'sphinx.ext.intersphinx',
        'sphinx.ext.napoleon',
        'sphinx.ext.viewcode',
        'sphinx_autodoc_typehints',
        'sphinx_inline_tabs',
        'sphinx_paramlinks',
        'sphinx_rtd_theme',

]
rst_epilog = """\
.. _docopt: http://docopt.org/
"""
intersphinx_mapping = {
        'python': ('https://docs.python.org/3', None),
}
autodoc_member_order = 'bysource'
autosummary_generate = True
autoclasstoc_sections = ['public-attrs', 'public-methods']
html_theme = 'sphinx_rtd_theme'
pygments_style = 'sphinx'
paramlinks_hyperlink_param = 'name'
always_use_bars_union = True

def remove_tabs_js(app, exc):
    from pathlib import Path
    if app.builder.format == 'html' and not exc:
        tabs_js = Path(app.builder.outdir) / '_static' / 'tabs.js'
        tabs_js.unlink()

def setup(app):
    app.add_css_file('css/corrections.css')
    app.connect('build-finished', remove_tabs_js)
