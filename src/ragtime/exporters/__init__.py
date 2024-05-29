#!/usr/bin/env python3

from ragtime.base.exporter import Exporter

from ragtime.exporters.json import Json
from ragtime.exporters.html import Html
from ragtime.exporters.spreadsheet import Spreadsheet

exporterTable: dict = {
    "json": Json,
    "html": Html,
    "spreadsheet": Spreadsheet,
}
