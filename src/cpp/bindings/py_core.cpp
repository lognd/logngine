#include <pybind11/pybind11.h>
#include <logngine/core/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_core_core, m) {
    m.doc() = "Bindings for logngine.core's C++ source.";
    m.def(
        "hello",
        &logngine::core::hello,
        "Return a greeting from the C++ core package!"
    );
}