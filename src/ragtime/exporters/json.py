from ragtime.base.exporter import Exporter, Expe, Path


class Json(Exporter):
    indent: int = 2
    encoding: str = "utf-8"
    _force_extension: str = ".json"

    """
    Saves Expe to JSON - can generate a suffix for the filename
    Returns the Path of the file actually saved
    """

    def save(self, expe: Expe, folder: Path = None, file_name: str = None) -> Path:
        path: Path = self._file_check_before_writing(expe, folder, file_name)
        # def save(self, expe: Expe, name: str = None) -> Path:
        # file_name: str
        # file_path: str
        # path: Path = self.path
        # if name:
        #     if self.json_path:
        #         file_name = f"{name}{self.json_path.stem}"
        #         file_path = self.json_path.parent
        #     else:
        #         file_name = f"{name}.json"
        #         file_path = ""
        # path = Path(file_path) / Path(file_name)
        with open(path, encoding=self.encoding, mode="w") as file:
            file.write(expe.model_dump_json(indent=self.indent))
        return path
