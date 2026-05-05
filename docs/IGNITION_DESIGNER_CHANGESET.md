# Ignition Designer Changeset

Date: 2026-03-19  
Compared against: `main..HEAD`  
Branch reviewed: `codex/mc-cell-counter-refactor`

This file lists the files changed in the branch and separates:

- files that matter for the Ignition Designer / runtime
- files that are only documentation, local tooling, or support material

It also includes the review notes that should be checked before exporting to production.

---

## 1. Functional files to review in Ignition Designer

These are the project-script files that changed and affect runtime behavior in Ignition:

### 1.1 `Tareas/Data/fromExcelToDB/code.py`

What changed:

- new helper `obtenerMinutoMC(celula, referencia)`
- `tareasTable(celula, referencia)` now resolves the critical-machine minute (`MC`)
- recurring rows inserted into `_Tareas` now write:
  - `min_std = imported standard value`
  - `min = MC value`

Why it matters in Designer:

- this changes the import pipeline
- this is the point where the standard gets normalized to the critical machine

Designer area:

- Project Library
- `Tareas > Data > fromExcelToDB > code.py`

### 1.2 `Tareas/Data/TagsMaquina/code.py`

What changed:

- new helper `usaContadorCelula(nombreTarea)`
- `completarTarea(...)` signature changed from:
  - `completarTarea(celula, num, nombreTarea)`
  - to `completarTarea(celula, referencia, num, nombreTarea)`
- non-`CH` tasks now use:
  - `piezasMaquinaTurno_Automatica(celula, referencia)`
  - instead of machine-local counter behavior
- `CH` keeps local counter/tool-life behavior

Why it matters in Designer:

- this changes live completion semantics
- this is one of the highest-risk runtime files in the branch

Designer area:

- Project Library
- `Tareas > Data > TagsMaquina > code.py`

### 1.3 `Tareas/Secuencia/General/code.py`

What changed:

- `completarTarea(...)` now calls:
  - `Tareas.Data.TagsMaquina.completarTarea(celula, referencia, num, tarea)`
- comments were updated to reflect `MC`-normalized rhythm

Why it matters in Designer:

- this is the orchestration entrypoint
- if this file is not updated together with `TagsMaquina`, the signature will not match

Designer area:

- Project Library
- `Tareas > Secuencia > General > code.py`

### 1.4 `Administracion/Data/GestionTareas/code.py`

What changed:

- `editarMinutosMaquina(...)` no longer updates only one machine row
- it now:
  - updates the `MC` source row in `_Secuencia`
  - propagates `min` to `_Tareas` for the whole `(celula, referencia)`
  - refreshes `_Tareas_Resumen` with the correct arguments

Why it matters in Designer:

- this changes admin behavior
- editing the critical-machine time becomes a global action for the cell/reference

Designer area:

- Project Library
- `Administracion > Data > GestionTareas > code.py`

---

## 2. Files changed in the branch that do NOT require Designer edits

These changed in Git, but they are not Ignition runtime scripts to be copied into the Designer as project-library code:

- `IGNITION_SCRIPT_SYSTEM_MAP.md`
- `IGNITION_DESIGNER_CHANGESET.md`
- `docs/superpowers/plans/2026-03-19-mc-cell-counter-refactor.md`
- `docs/superpowers/specs/2026-03-19-mc-cell-counter-model.md`
- `tarea.md`
- `tarea limpiada.md`
- `R104587.xlsx`
- `.cursor/plans/mc-cell-counter-refactor_e9836e33.plan.md`
- `.vscode/settings.json`
- `cambio2.py`
- `cambios`

These are useful as support material, but they are not the files to paste/update in the Ignition Designer runtime library.

---

## 3. Recommended Designer import order

If you are applying these changes manually in Ignition Designer, the safest order is:

1. `Tareas/Data/fromExcelToDB/code.py`
2. `Tareas/Data/TagsMaquina/code.py`
3. `Tareas/Secuencia/General/code.py`
4. `Administracion/Data/GestionTareas/code.py`

Why this order:

- import/data normalization first
- counter/runtime logic second
- orchestration caller third
- admin edit path last

---

## 4. Review findings before moving to production

These are the two most important risks found while reviewing the changed runtime files.

### Finding 1: New recurring-task baselines still start at `0`, which can cause false overshoot after a restart or standard reload

Files involved:

- `Tareas/Data/TagsMaquina/code.py`

Relevant lines in current branch:

- `Tareas/Data/TagsMaquina/code.py:118-128`
- `Tareas/Data/TagsMaquina/code.py:357-360`

Why this matters:

- `syncTareas(...)` still creates new rows with `contador = 0`
- the new `completarTarea(...)` now interprets `contador` as the baseline of the automatic-cell counter for non-`CH` tasks
- after `iniciarEstandar(...)`, a standard reload, or a mid-shift sync, the first completion of a recurring task may compare:
  - `contadorCelula actual`
  - against baseline `0`
- that can produce a false `delta >= ocurrencia` and force an immediate overshoot/reprogramming path

Recommendation:

- when a non-`CH` task row is created or reinitialized, seed `contador` with the current automatic-cell counter instead of `0`

### Finding 2: Editing MC minutes updates DB summary, but it does not refresh the live planner dataset or machine helper datasets

Files involved:

- `Administracion/Data/GestionTareas/code.py`

Relevant lines in current branch:

- `Administracion/Data/GestionTareas/code.py:377-409`

Why this matters:

- `editarMinutosMaquina(...)` now updates `_Secuencia` and `_Tareas`
- it refreshes `_Tareas_Resumen`
- but it does not call:
  - `Tareas.Secuencia.General.iniciarEstandar(celula)`
  - or a lighter live refresh equivalent
- if the edited reference is currently active, the planner shown to operators can stay stale until the next explicit restart/reload

Recommendation:

- after a successful MC edit, refresh the active dataset for that cell if the reference is live

---

## 5. Practical checklist for Designer

- [ ] Update `Tareas/Data/fromExcelToDB/code.py`
- [ ] Update `Tareas/Data/TagsMaquina/code.py`
- [ ] Update `Tareas/Secuencia/General/code.py`
- [ ] Update `Administracion/Data/GestionTareas/code.py`
- [ ] Verify no other scripts still call the old `TagsMaquina.completarTarea(celula, num, nombreTarea)` signature
- [ ] Validate a Dev import with `R104587.xlsx`
- [ ] Validate startup of `142D / R104587`
- [ ] Validate non-`CH` completion against automatic-cell counter
- [ ] Validate admin edit of MC minute
- [ ] Fix the two review findings before production export if they are confirmed in Dev

---

## 6. Short conclusion

The branch changes that must be reflected in Ignition Designer are concentrated in 4 project-script files:

- `Tareas/Data/fromExcelToDB/code.py`
- `Tareas/Data/TagsMaquina/code.py`
- `Tareas/Secuencia/General/code.py`
- `Administracion/Data/GestionTareas/code.py`

Everything else changed in Git is either documentation, support material, or local tooling.

