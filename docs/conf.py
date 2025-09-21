# Entry point (Sphinx 8+)
root_doc = "index"


# --- Project info ---
project = "pyDynamo"
author = "Peter W. Hogg and Patrick Coleman"

# Option A: hardcode a version for now
release = "dev"
version = release

# Option B (optional): read from the installed package
# from importlib.metadata import version as _v, PackageNotFoundError
# try:
#     release = _v("pydynamo-brain")
# except PackageNotFoundError:
#     release = "dev"
# version = release

# --- HTML title overrides (removes the “… documentation” suffix) ---
html_title = "pyDynamo — User & API Guide"
html_short_title = "pyDynamo"

# Source types
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# Theme + useful extensions
html_theme = "furo"
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "nbsphinx"
]
autosummary_generate = True
myst_enable_extensions = ["colon_fence", "deflist", "linkify"]
nbsphinx_execute = "never"
# Mock heavy GUI deps so autodoc never breaks CI
autodoc_mock_imports = ["numpy", "scipy"]

# (Optional) Intersphinx mappings
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}
