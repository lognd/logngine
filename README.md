# logngine

**logngine** is a fast, extensible engineering computation toolkit designed for personal study, simulation, and experimentation. It aims to distill key tools and insights from across mechanical and aerospace engineering into a reusable, modular codebase — built with performance in mind and designed to scale from classroom problems to real-time simulation.

**Status:** In early development. Currently includes a C++/Python build scaffold with placeholder modules for `thermo`, `uncertainty`, and `materials`.

---

## Motivation

This project is part of a long-term goal to consolidate everything I've studied in engineering — from thermodynamics and materials to numerical methods and uncertainty quantification — into a clean, high-performance library.

The vision (although with some lofty goals) is to support:

- Personal and academic learning
- Scientific computing experiments
- Eventual integration with games/mods (e.g., Minecraft)
- Prototyping physical models and solvers

---

## Features (planned)

| Module        | Description                                   | Status     |
|---------------|-----------------------------------------------|------------|
| `thermo`      | Property tables, steam cycles, psychrometrics | planned    |
| `uncertainty` | Propagation, Monte Carlo, statistical bounds  | planned    |
| `materials`   | Stress/strain models, fatigue, fracture       | planned    |

---

## Build System

This project uses a hybrid C++/Python architecture:

- Python 3.9+
- [scikit-build-core](https://github.com/scikit-build/scikit-build-core) (PEP 517 backend)
- CMake 3.27+
- pybind11 2.13+
- Cross-platform: supports MSVC, GCC, Clang

To install in development mode:

```bash
pip install -e .[test]
```

Then run tests:

```bash
pytest -v
```

You can look more at `Makefile` for some ideas.

## Folder Structure

```
src/logngine/
├── thermo/         ← Thermodynamic property models (WIP)
├── materials/      ← Materials mechanics (WIP)
├── uncertainty/    ← Statistical tools (WIP)
└── _core/          ← Compiled C++ bindings (.so/.pyd)
```

C++ source files live under `src/cpp/` and are compiled into extension modules accessible via `_core/`.

---

## Current Status

Right now the repository builds and runs minimal "hello-world" modules for:

- `logngine.thermo.hello()`
- `logngine.uncertainty.hello()`
- `logngine.materials.hello()`

These serve as a proof of concept for the cross-language build system using `pybind11` and `scikit-build-core`.

---

## Future Plans

- Import thermodynamic property tables (e.g., ASHRAE, EES-style)
- Implement robust interpolation over saturated/superheated states
- Add symbolic fallbacks and EOS approximations for generality
- Integrate unit-handling (SI/imperial) across all modules

---

## Who Is This For?

- Myself (*lognd*) — as a personal notebook, simulation engine, and modding sandbox
- Engineering students and hobbyists
- Anyone who wants learnable, testable, and efficient engineering models

---

## License

[MIT License](LICENSE)

---

## Contributions

Not actively accepting pull requests yet — but if this inspires you or you'd like to collaborate, feel free to open an issue or start a discussion.
