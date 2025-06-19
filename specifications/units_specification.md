# .units File Specification

This specification defines the format for `.units` files used in validating and converting physical quantities.

---

## Overview

Each `.units` file corresponds to a **single base quantity type** (e.g., pressure, temperature) and defines:
- A canonical base unit (with name, abbreviation, and dimension formula)
- A list of derived units with abbreviations and formulas for converting to the base unit

The format is designed to be **C++-parsable**, UTF-8 friendly, and human-editable.

---

## Format Rules

### 1. File Naming
- The filename (e.g., `temperature.units`) must match the **physical quantity** it describes.

### 2. Comments
- Anything after `#` is ignored.
- Use `#` to annotate units or explain logic.

### 3. Blank lines
- Lines containing only whitespace are ignored.

### 4. First Line – Base Unit Declaration
```
<unit_id> <abbreviation> <dimension>
```

- `unit_id`: lowercase name (e.g., `kelvin`, `pascal`)
- `abbreviation`: printable short form (e.g., `K`, `Pa`)
- `dimension`: how to express this unit in base terms, e.g.:
  - `~` for primitive units
  - `m*s`, `kg^1*m*s^-2`, etc. (later used for dimensional analysis)

### 5. Following Lines – Derived Units
```
<unit_id> <abbreviation> <conversion_formula>
```

- `unit_id`: lowercase, underscores allowed, unique globally
- `abbreviation`: human-readable unit symbol
- `conversion_formula`: 
  - `multiplier*x` or `multiplier*x+offset`
  - Constants must be numeric and support scientific notation (e.g., `1.8*x+32`, `1e3*x`)
  - No function calls or variable names allowed

### 6. Delimiters
- Columns are **space-separated**, consecutive spaces are collapsed.
- No quotes needed; all fields must be space-safe.

### 7. Restrictions
- **No duplicate unit IDs allowed**, even across other `.units` files.
- Compound units (e.g., `kJ/kg`, `m/s`) must be handled at a higher level, not in `.units`.

---

## Example: `temperature.units`

```units
kelvin K ~
celsius °C 1.0*x+273.15
fahrenheit °F 0.55555555556*x+255.372
rankine R 0.555555555556*x
```

## Example: `pressure.units`

```units
pascal Pa ~
kilopascal kPa 1e3*x
bar bar 1e5*x
atmosphere atm 101325*x
psi psi 6894.76*x
```
