#include <pybind11/pybind11.h>
#include <logngine/units/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_units_core, m) {
    m.doc() = "Bindings for logngine.units's C++ source.";
    m.def(
        "hello",
        &logngine::units::hello,
        "Return a greeting from the C++ units package!"
    );
}