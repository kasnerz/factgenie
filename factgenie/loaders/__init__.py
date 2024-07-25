import os
import importlib

dir_path = os.path.dirname(os.path.abspath(__file__))
modules = [
    os.path.splitext(_file)[0]
    for _file in os.listdir(dir_path)
    if (_file.endswith(".py") and not _file.startswith("__"))
]

for mod in modules:
    module = importlib.import_module(f"factgenie.loaders.{mod}")
