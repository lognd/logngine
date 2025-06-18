#include <pybind11/pybind11.h>
#include <logngine/uncertainty/hello.h>

namespace py = pybind11;

PYBIND11_MODULE(_uncertainty_core, m) {
    m.doc() = "Bindings for logngine.uncertainty's C++ source.";
    m.def(
        "hello",
        &logngine::uncertainty::hello,
        "Return a greeting from the C++ uncertainty package!"
    );
}