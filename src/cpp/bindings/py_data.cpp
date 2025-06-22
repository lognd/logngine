#include <pybind11/pybind11.h>
#include <logngine/data/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_data_core, m) {
    m.doc() = "Bindings for logngine.data's C++ source.";
    m.def(
        "hello",
        &logngine::data::hello,
        "Return a greeting from the C++ data package!"
    );
}