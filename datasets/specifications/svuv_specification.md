# .svuv File Specification (Updated)

**.svuv** stands for **Separated Values with Units and Variables** — a structured table format for physical data that supports embedded units, symbolic headers, and directives for parsing or conversion.

---

## Format Rules

### 1. Comments
- Any text after `#` is ignored.

### 2. Blank lines
- Empty or whitespace-only lines are ignored.

### 3. Row 1 – Headings
- Lowercase identifiers (e.g., `specific_volume`)
- Use `~` to skip a column entirely
- No duplicates allowed

### 4. Row 2 – Variables
- Symbolic representations (e.g., `v_g`, `h_f`)
- Must consist of A–Z, a–z, 0–9, and `_`
- Cannot begin with a number

### 5. Row 3 – Units
- Must be either:
  - A **unit abbreviation** (e.g., `Pa`, `°C`)
  - Or a **unit ID** (e.g., `pascal`, `celsius`)
- All units must be defined in corresponding `.units` files under `src/validation/units/`
- Units are expected to be **basic** — i.e. not compound like `kJ/kg` or `m/s`. Unit combination is resolved elsewhere.

---

## 6. Commands (`!`)

Commands must appear on a line by themselves.

### `!set-heading`
- Next non-empty line replaces the heading row

### `!set-units`
- Next non-empty line replaces the unit row

### `!set-uncertainty`
- Next non-empty line hard-sets the magnitude of the uncertainty, use`~` literal to keep auto-calculating behavior for some rows.

### `!ignore-separator "<char>"`
- Removes a character from the allowed separator set

### `!add-separator "<char>"`
- Adds a character to the allowed separator set

### `!cite "<name>"`
- Tags all the data until next `!cite` with the source to allow for proper attribution and back-tracing

---

## 7. Data rows
- Parsed as numeric rows
- Any non-numeric character (except `.` and `-`) is discarded
- Skipped (`~`) columns are ignored

---

## ✅ Example

```svuv
# Saturation properties for water

temperature    pressure     ~     specific_volume
T              P            ~     v
celcius        kPa          ~     m^3/kg

100.0          101.3        ---   1.043
120.0          198.5        ---   1.060

!add-separator |

!set-heading
temperature|pressure|specific_volume
!set-units
degC|kPa|m^3/kg
150.0|476.2|0.392
```
