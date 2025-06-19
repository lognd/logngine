# logngine

**logngine** is a fast, extensible engineering computation toolkit designed for personal study, simulation, and experimentation. It aims to distill key tools and insights from across mechanical and aerospace engineering into a reusable, modular codebase — built with performance in mind and designed to scale from classroom problems to real-time simulation.

> **Status:** In early development.  
> **Latest:** Set up for units integration and table parsing → embedded C++ source generation planned.

---

## Motivation

This project is part of a long-term goal to consolidate everything I've studied in engineering — from thermodynamics and materials to numerical methods and uncertainty quantification — into a clean, high-performance library.

### Vision

- Engineering simulation & property modeling
- Personal and academic learning tools
- Scientific computing experiments
- Integration with games/mods (e.g., Minecraft)
- Prototyping physical models and solvers

---

## Features (Planned)

| Module        | Description                                   | Status   |
|---------------|-----------------------------------------------|----------|
| `thermo`      | Property tables, steam cycles, psychrometrics | WIP      |
| `uncertainty` | Propagation, Monte Carlo, statistical bounds  | WIP      |
| `materials`   | Stress/strain models, fatigue, fracture       | WIP      |
| `units`       | Unit validation, conversion, dimensionality   | Drafted  |

---

## ️ Build System

This project uses a hybrid C++/Python architecture with cross-platform tooling:

- Python 3.9+
- `scikit-build-core` (PEP 517 backend)
- `pybind11` 2.13+
- CMake 3.27+
- Supports MSVC, GCC, Clang

### Install in development mode:

```bash
pip install -e .[test]
pytest -v
```

For convenience, you can also use `Makefile` or `make.bat` on Linux and Windows respectively.

---

## Folder Structure

```text
src/logngine/
├── thermo/         # Thermodynamic property models
│   └── _core/      # C++ bindings (.so/.pyd)
├── materials/      # Materials mechanics
│   └── _core/
├── uncertainty/    # Statistical tools
│   └── _core/
├── units/          # Unit integration and dispatch (WIP)
│   └── _core/
├── data/           # Human-editable .svuv tables (planned input)
└── validation/     # .units files, schema definitions
```

C++ sources live in `src/cpp/` and are compiled into Python modules with `pybind11`.

---

## Current Status

- Cross-language build system using `pybind11` + `scikit-build-core`
- Basic submodules build and expose:

```python
logngine.thermo.hello_world()
logngine.uncertainty.hello_world()
logngine.materials.hello_world()
logngine.units.hello_world()
```

- Unit registry and table parser spec complete (`.svuv`, `.units`)
- Plan to convert raw table data into embedded C++ arrays at build time

---

## Specifications

- See [`specifications/`](./specifications) for `.svuv` and `.units` documentation
- Tables live under `src/logngine/data/fluids/`
- All data is validated against schemas before being compiled into C++

---

## Roadmap

- [ ] Add Python preprocessor to compile `.svuv` and `.units` into C++ code
- [ ] Symbolic units fallback (e.g., imperial vs SI)
- [ ] EOS support and interpolated table resolution
- [ ] Hook into Minecraft/Mod loader as backend
- [ ] Better test coverage and perf benchmarking

---

## Who Is This For?

- Myself (*lognd*) — as a personal notebook, simulation engine, and modding sandbox
- Engineering students and hobbyists
- Anyone who wants learnable, testable, efficient models for physics/eng

---

## License

[MIT License](./LICENSE)

---

## Contributions

Not actively accepting PRs yet, but if this project inspires you, feel free to:
- Open an issue
- Suggest `.units` or `.svuv` extensions
- Help expand the dataset in `src/validation/units/`

Especially helpful: submitting real-world engineering property tables for processing!

---
