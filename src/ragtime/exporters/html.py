from ragtime.base.exporter import Exporter, Expe, Path


from ragtime.config import (
    DEFAULT_HTML_RENDERING,
    DEFAULT_HTML_TEMPLATE,
)

from jinja2 import Environment, FileSystemLoader
import re


class Html(Exporter):
    encoding: str = "utf-8"
    template_encoding: str = "utf-8"
    template_path: Path = DEFAULT_HTML_TEMPLATE
    render_params: dict[str, bool] = DEFAULT_HTML_RENDERING
    _force_extension: str = ".html"

    """
    Saves Expe to an HTML file from a Jinja template - can generate a suffix for the filename
    Returns the Path of the file actually saved
    """

    def save(self, expe: Expe, folder: Path = None, file_name: str = None) -> Path:
        path: Path = self._file_check_before_writing(expe, folder, file_name)
        loader: FileSystemLoader = FileSystemLoader(
            searchpath=self.template_path.parent,
            encoding=self.template_encoding,
        )
        environment = Environment(loader=loader)
        template = environment.get_template(self.template_path.name)
        context = {
            "expe": expe,
            **self.render_params,
            "report_name": self._get_name(expe),
            "sub": (lambda pattern, repl, s: re.sub(pattern, repl, s)),
        }
        with open(path, encoding=self.encoding, mode="w") as file:
            file.write(template.render(context))
        return path
