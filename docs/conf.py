# Entry point (Sphinx 8+)
root_doc = "index"

project = "pyDynamo"
author = "Peter W. Hogg and Patrick Coleman"
release = "dev"
version = release

html_title = "pyDynamo — User & API Guide"
html_short_title = "pyDynamo"

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
html_theme = "furo"

extensions = [
    "myst_parser",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "nbsphinx",
]

# You can re-enable autosummary/autodoc later if needed.
# autosummary_generate = True

# MyST: keep only what you need; 'linkify' requires an extra pip package.
myst_enable_extensions = ["colon_fence", "deflist"]  # remove "linkify" for now

nbsphinx_execute = "never"
nbsphinx_requirejs = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}
