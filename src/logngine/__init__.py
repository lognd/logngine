from importlib.metadata import version as _v
from . import materials, thermo, uncertainty

__version__ = _v(__name__)

def hello_all() -> dict[str, str]:
    return {
        "materials": materials.hello_world(),
        "thermo": thermo.hello_world(),
        "uncertainty": uncertainty.hello_world()
    }