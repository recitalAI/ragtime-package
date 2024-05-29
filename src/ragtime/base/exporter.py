from typing import Optional
from pydantic import BaseModel
from abc import abstractmethod

from ragtime.expe import Expe
from ragtime.config import RagtimeException

from pathlib import Path
from datetime import datetime


class Exporter(BaseModel):
    path: Optional[Path] = None
    b_overwrite: Optional[bool] = False
    b_add_suffix: Optional[bool] = True
    _force_extension: Optional[str] = None

    def _get_name(self, expe: Expe) -> str:
        """
        Returns the name of the Expe based on the number of questions, answers...
        """
        date_to_time_format: str = "%Y-%m-%d_%Hh%M,%S"
        stats: dict = expe.stats()
        name: str = (
            f'{stats["questions"]}Q_{stats["chunks"]}C_{stats["facts"]}F_{stats["models"]}M_{stats["answers"]}A_{stats["human eval"]}HE_{stats["auto eval"]}AE_{datetime.now().strftime(date_to_time_format)}'
        )
        return name

    def _file_check_before_writing(
        self, expe: Expe, folder: Path = None, file_name: str = None
    ) -> Path:
        # Check and prepare the destination file path
        path: Path = None
        if folder and file_name:
            path = folder / Path(file_name)
        path = path or expe.path
        if not (path or self.path):
            raise RagtimeException(
                f"Cannot save to JSON since no default path nor path has been provided in argument."
            )
        elif self.path:
            path = Path(self.path.parent) / self.path.stem
        # If the provided path is a string, convert it to a Path
        result_path = Path(path) if isinstance(path, str) else path

        # Make sure at least 1 QA is here
        if len(expe) == 0:
            raise Exception(
                """The Expe object you're trying to write is empty! Please add at least one QA"""
            )

        # If a suffix is to be added, add it
        if self.b_add_suffix:
            file_no_ext: str = result_path.stem
            # genrates the new suffix like --5M_50Q_141F_50A_38HE
            sep: str = "--"
            new_suf: str = self._get_name(expe)
            if file_no_ext.find(sep) != -1:  # if already a suffix, replace it
                old_suf: str = file_no_ext[file_no_ext.find(sep) + len(sep) :]
                file_no_ext = file_no_ext.replace(old_suf, new_suf)
            else:
                file_no_ext = f"{file_no_ext}{sep}{new_suf}"
            str_name: str = f"{file_no_ext}{result_path.suffix}"
            result_path = result_path.parent / Path(str_name)

        # Force ext
        if self._force_extension:
            if result_path.suffix:  # if already an extension, replace it
                result_path = Path(
                    str(result_path).replace(result_path.suffix, self._force_extension)
                )
            else:  # if no extension, just add it
                result_path = Path(f"{result_path}{self._force_extension}")

        # If path exists and overwrite not allowed, raise an Exception
        if result_path.is_file() and not self.b_overwrite:
            raise FileExistsError(
                f'"{path}" already exists! Set b_overwrite=True to allow overwriting.'
            )
        return result_path

    @abstractmethod
    def save(self, expe: Expe, folder: Path = None, file_name: str = None) -> Path:
        raise NotImplementedError("Must implement this!")
