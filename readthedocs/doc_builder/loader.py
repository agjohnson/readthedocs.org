from django.utils.importlib import import_module
from django.conf import settings

# Managers
mkdocs = import_module(getattr(settings, 'MKDOCS_BACKEND', 'doc_builder.backends.mkdocs'))
sphinx = import_module(getattr(settings, 'SPHINX_BACKEND', 'doc_builder.backends.sphinx'))

BUILDER_BY_NAME = {
    # Possible HTML Builders
    'sphinx': sphinx.HtmlBuilder,
    'sphinx_htmldir': sphinx.HtmlDirBuilder,
    'sphinx_singlehtml': sphinx.SingleHtmlBuilder,
    # Other Sphinx Builders
    'sphinx_pdf': sphinx.PdfBuilder,
    'sphinx_epub': sphinx.EpubBuilder,
    'sphinx_search': sphinx.SearchBuilder,
    'sphinx_singlehtmllocalmedia': sphinx.LocalMediaBuilder,
    # Other markup
    'mkdocs': mkdocs.MkdocsHTML,
    'mkdocs_json': mkdocs.MkdocsJSON,
}


def get_builder_class(name):
    return BUILDER_BY_NAME[name]
