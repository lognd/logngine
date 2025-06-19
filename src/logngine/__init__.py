from importlib.metadata import version as _v
from . import materials, thermo, uncertainty

__version__ = _v(__name__)