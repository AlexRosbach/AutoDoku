"""PyInstaller hook: bundle the manuf OUI database file."""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("manuf")
