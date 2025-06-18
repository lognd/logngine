#include <pybind11/pybind11.h>
#include <logngine/thermo/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_thermo_core, m) {
    m.doc() = "Bindings for logngine.thermo's C++ source.";
    m.def(
        "hello",
        &logngine::thermo::hello,
        "Return a greeting from the C++ thermo package!"
    );
}