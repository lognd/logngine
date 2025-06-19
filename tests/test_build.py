import logngine
import pkgutil
import importlib

def test_hello_world():
    # Dynamically detect submodules inside logngine
    modules = [
        name for _, name, ispkg in pkgutil.iter_modules(logngine.__path__)
        if not name.startswith('_') and ispkg
    ]

    for module_name in modules:
        # Dynamically import the submodule (e.g., logngine.thermo)
        full_name = f"logngine.{module_name}"
        module = importlib.import_module(full_name)

        # Get the result of hello()
        result = module.hello_world()
        expected = f"Hello from `logngine::{module_name}`!"

        assert result == expected, f"Unexpected hello from `{full_name}`: got {result!r}, expected {expected!r}"