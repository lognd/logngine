import logngine

def test_hello_world():

    packages: list[str] = ['materials', 'thermo', 'uncertainty']

    _hellos: dict[str, str] = logngine.hello_all()
    for package in packages:
        _expected_hello: str = f"Hello from `logngine::{package}`!"
        assert _hellos[package] == _expected_hello, f"Unexpected \"hello-ping\" from `logngine::{package}`."
