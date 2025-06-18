#include <pybind11/pybind11.h>
#include <logngine/materials/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_materials_core, m) {
    m.doc() = "Bindings for logngine.materials's C++ source.";
    m.def(
        "hello",
        &logngine::materials::hello,
        "Return a greeting from the C++ materials package!"
    );
}