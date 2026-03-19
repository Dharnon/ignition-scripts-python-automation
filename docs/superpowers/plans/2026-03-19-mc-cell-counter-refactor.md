# MC Cell Counter Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make task planning and runtime advancement depend on the automatic cell piece counter and the critical-machine cycle time (`MC`) for all recurring tasks except tool-change counter logic.

**Architecture:** Keep the existing Ignition flow and data model, but move the source of truth for cadence to the critical machine. Normalize task time from the standard into `_Tareas.min`, preserve `min_std` as imported data, and make runtime completion/reprogramming use the automatic-cell counter for all non-`CH` recurring tasks. Keep `CH` as a counter exception, but still use `MC` as the time base. Implement bin-picking occurrence updates as a focused follow-up in the task automation layer.

**Tech Stack:** Ignition project scripts (Jython), dataset tags, SQL Server queries, Excel-to-DB import pipeline, OEE production tables, task planner datasets.

---

## Scope split

This spec contains two related but not identical subsystems:

1. Core scheduling refactor
   - source of truth becomes `MC` time + automatic-cell counter
   - affects import, scheduling, completion, admin edit/create

2. Special automations
   - bin-picking tray-change occurrence update + auto-completion
   - automatic `CH auto` traceability and synoptic warning

This plan keeps them in one document, but in execution they should be implemented in this order:

1. Core scheduling refactor
2. Bin-picking tray-change automation
3. `CH auto` traceability and visual alert

---

## Files to modify

### Core scheduling refactor

- Modify: `Tareas/Data/fromExcelToDB/code.py`
  - import standard rows
  - derive/normalize critical-machine time
  - rebuild `_Tareas` with `min = MC`

- Modify: `Tareas/Data/General/code.py`
  - use normalized `MC` time as the effective rhythm
  - add helper logic to resolve which tasks use automatic-cell counter vs tool-life rules

- Modify: `Tareas/Data/TagsMaquina/code.py`
  - switch non-`CH` task advancement away from machine-local counters
  - use `piezasMaquinaTurno_Automatica(celula, referencia)` for recurring task progress

- Modify: `Tareas/Secuencia/General/code.py`
  - keep orchestration stable
  - ensure startup/load paths call the normalized import logic cleanly
  - ensure completion flow can pass the right counter/time semantics

- Modify: `Tareas/Data/Teorico/code.py`
  - only if needed after normalization
  - verify generated datasets align equal frequencies across machines once `MC` is normalized

- Modify: `Administracion/Data/GestionTareas/code.py`
  - editing minutes must update the critical-machine time globally, not per individual machine row
  - creating/editing recurring tasks must use critical-machine time

### Bin-picking tray-change automation

- Modify: `Tareas/Data/DesviacionTareas/code.py`
  - extend `accionesCambioBandejaCarga(...)`
  - add occurrence update + auto-completion behavior

- Possibly modify: `Administracion/Data/GestionTareas/code.py`
  - if the tray-piece change also needs an admin-side edit path

### `CH auto` traceability

- Modify: `Tareas/Data/DesviacionTareas/code.py`
  - detect end-of-life / near-end-of-life transition
  - create or trigger automatic `CH` task behavior

- Modify: `Tareas/Data/General/code.py`
  - if a dedicated task-creation/logging helper is needed for `CH auto`

- Inspect and possibly modify: `tags.json` / `udts.json`
  - only if the visual alert on the synoptic depends on a helper tag or existing UDT event

---

## Code map for this change

### Current hard points already identified

- `Tareas/Data/fromExcelToDB/code.py:483`
  - `tareasTable(celula, referencia)`
  - currently inserts recurring rows with `min_std` populated and `min = NULL`

- `Tareas/Data/General/code.py:1`
  - `obtenerRitmoProd(celula, referencia, maquina)`
  - currently reads `Tiempo de m%` filtered by the requested machine

- `Tareas/Data/TagsMaquina/code.py:217`
  - `piezasMaquinaTurno_Automatica(celula, referencia)`
  - already exists and reads the robust automatic-cell counter from `COEEproduction`

- `Tareas/Data/TagsMaquina/code.py:277`
  - `completarTarea(celula, num, nombreTarea)`
  - currently consumes machine-local dataset counters

- `Tareas/Secuencia/General/code.py:137`
  - `completarTarea(celula, referencia, tipoMaq, tarea, num, manual)`
  - currently assumes `rpt` comes from the selected machine and `contador` comes from the machine-local helper dataset

- `Administracion/Data/GestionTareas/code.py:364`
  - `editarMinutosMaquina(referencia, maquina, celula, minutos)`
  - currently updates only `Tiempo de máquina 1/1` rows for the selected machine

- `Tareas/Data/DesviacionTareas/code.py:588`
  - `accionesCambioBandejaCarga(celula, num)`
  - currently only returns state `0/1/2`, without updating task occurrence from a new tray-piece value

### Evidence from `R104587.xlsx`

- `R104587-D`
  - `REFERENCIA = R104587`
  - `CELULA = 142D`
  - `MC = 3.8`
  - `TALLADORA` appears as the `MC` machine row in the standard

This confirms the workbook already contains the critical-machine concept needed by the refactor.

### Excel behavior note: how to derive MC and which tasks are piece-dependent

- **How to derive MC for one `(celula, referencia)`**
  - In the imported `_Secuencia` table (one sheet per reference, e.g. `R104587-D` for `R104587/142D`), the critical machine is already encoded as a dedicated row.
  - That row is the one whose `tipo` marks it as `MC` and whose `maquina` matches the critical resource for the cell (in `R104587-D`, this is `TALLADORA` with `min_std = 3.8`).
  - For a given `(celula, referencia)`, we treat that single row as the **source of truth** for the minute value: `MC = min_std` of the `tipo='MC'` row. If there is more than one candidate or none at all, the import should log a clear error and abort normalization for that standard.

- **Which tasks are considered piece-dependent**
  - All recurring tasks whose frequency is expressed in pieces (the `... 1/N` style tasks that currently use `ocurrencia` as “pieces between executions”) are considered **piece-dependent** and must advance from the automatic cell counter and use `MC` as time base.
  - `CH` (tool change) is a **special case**: its *counter* still comes from tool-life logic, but its **time side** must also use `MC`, so when it is scheduled it lines up with the rest of the piece-driven cadence.
  - Non-piece tasks such as pure measurement rows (`MEDICIÓN`/`MEDICI%`), `VARIOS`, and synthetic helper rows like the historical `CELULA / pieza terminada / tiempo de máquina` are **not** treated as piece-driven for counter semantics; they either keep their existing logic or are refactored to derive their timing directly from the MC-based schedule without inventing a new per-machine cadence.

---

## Chunk 1: Critical-machine time normalization

### Task 1: Add helpers to resolve `MC` for one `celula + referencia`

**Files:**
- Modify: `Tareas/Data/fromExcelToDB/code.py`

- [ ] **Step 1: Add a helper that resolves the critical-machine time from imported standard rows**

Add a focused helper near `tareasTable(...)`, for example:

```python
def obtenerMinutoMC(celula, referencia):
    """
    Returns the critical-machine cycle time for one cell/reference.
    Uses the imported `_Secuencia` rows and the workbook's `tipo='MC'` row.
    """
```

Expected behavior:

- read from `constantes.LINEA + "_Secuencia"`
- filter by `celula` and `referencia`
- locate the row that represents the `MC` machine time
- return a single float minute value
- raise/log clearly if no `MC` row exists

- [ ] **Step 2: Add a helper that identifies whether a `_Tareas` row should inherit `MC` time**

Add a second helper, for example:

```python
def usaTiempoMC(tarea):
    return not tarea.startswith("CH")
```

Then refine it to the real rule:

- all recurring tasks use `MC`
- `CH` still uses `MC` for time
- if any truly independent task must stay outside this rule, list it explicitly instead of encoding broad exclusions

Important:

- do not use machine name as the selector
- use task family or standard semantics

- [ ] **Step 3: Update `tareasTable(celula, referencia)` to write normalized `min`**

Keep `min_std` as imported from the standard, but set `min` during the insert phase.

Target outcome:

- recurring task rows in `_Tareas` get:
  - `min_std = imported original`
  - `min = critical-machine minute`

- `Tiempo de máquina` rows should also be reviewed so admin views and later lookups stay coherent

- [ ] **Step 4: Add logging for missing or ambiguous `MC`**

Log at least:

- `celula`
- `referencia`
- whether `MC` was found
- resolved value

Fail safe:

- if `MC` cannot be resolved, abort the normalization for that load and leave a clear error

- [ ] **Step 5: Manual validation in Dev**

Run in Ignition Dev:

1. Load `R104587.xlsx`
2. Confirm `_Secuencia` imports normally
3. Confirm `_Tareas.min` is no longer `NULL` for recurring rows
4. Confirm `_Tareas.min` matches the `MC` value for `142D/R104587`
5. Confirm `min_std` stays unchanged

- [ ] **Step 6: Commit**

```bash
git add Tareas/Data/fromExcelToDB/code.py
git commit -m "feat: normalize task time from critical machine"
```

### Task 2: Keep startup generation using normalized time

**Files:**
- Inspect: `Tareas/Secuencia/General/code.py:1-28`
- Inspect: `Tareas/Data/Teorico/code.py:34-416`
- Modify if needed: `Tareas/Data/Teorico/code.py`

- [ ] **Step 1: Verify `obtenerTiemposMaquina(...)` already prefers `min` over `min_std`**

If it already does, keep changes minimal.  
If it still prefers machine-local or raw standard time, update it to consume normalized `min`.

- [ ] **Step 2: Verify equal frequencies align after normalization**

Use one Dev load and confirm:

- `1/100` tasks across different machines align
- `1/200` tasks across different machines align

- [ ] **Step 3: Only change `Teorico` if the alignment is still wrong**

Do not refactor more than needed.  
This plan prefers fixing the source data first, then letting the current scheduler operate over normalized values.

- [ ] **Step 4: Commit**

```bash
git add Tareas/Data/Teorico/code.py Tareas/Secuencia/General/code.py
git commit -m "feat: align theoretical scheduling with critical machine time"
```

---

## Chunk 2: Runtime advancement from automatic-cell counter

### Task 3: Add task-family helpers for counter semantics

**Files:**
- Modify: `Tareas/Data/General/code.py`
- Modify: `Tareas/Data/TagsMaquina/code.py`

- [ ] **Step 1: Add one helper for time semantics**

In `Tareas/Data/General/code.py`, add something like:

```python
def usaTiempoCritico(tarea):
    return True
```

Then make it explicit:

- all recurring tasks use critical time
- `CH` included for time

- [ ] **Step 2: Add one helper for counter semantics**

In `Tareas/Data/TagsMaquina/code.py`, add something like:

```python
def usaContadorCelula(tarea):
    return not tarea.startswith("CH")
```

This makes the rule obvious and avoids scattering string checks everywhere.

- [ ] **Step 3: Add a helper that returns effective progress from the right source**

Example direction:

```python
def obtenerContadorEfectivo(celula, referencia, num, tarea):
    if usaContadorCelula(tarea):
        return piezasMaquinaTurno_Automatica(celula, referencia)
    return None
```

This helper should support:

- cell automatic counter for generic recurring tasks
- existing machine/tool-life logic for `CH`

- [ ] **Step 4: Commit**

```bash
git add Tareas/Data/General/code.py Tareas/Data/TagsMaquina/code.py
git commit -m "refactor: centralize task time and counter semantics"
```

### Task 4: Replace non-`CH` completion logic with automatic-cell progress

**Files:**
- Modify: `Tareas/Data/TagsMaquina/code.py:277-385`
- Modify: `Tareas/Secuencia/General/code.py:137-183`

- [ ] **Step 1: Refactor `Tareas.Data.TagsMaquina.completarTarea(...)`**

Current behavior:

- reads machine-local `ContadorTareas`
- subtracts `ocurrencia`

New behavior for non-`CH` recurring tasks:

- read current automatic-cell counter through `piezasMaquinaTurno_Automatica(celula, referencia)`
- compare it against the stored baseline in the machine dataset row
- determine whether:
  - task just completed
  - task is already partway into the next cycle
  - task has overshot and needs immediate rebase

Keep the current return contract if possible:

- `0`
- positive value
- `-1`
- `-2`

That minimizes change in `Secuencia.General.completarTarea(...)`.

- [ ] **Step 2: Store a meaningful baseline in `ContadorTareas`**

The `contador` column should become:

- for generic recurring tasks: last automatic-cell counter checkpoint
- for `CH`: keep current local counter/tool-life semantics

Do not rename columns yet unless absolutely necessary.  
Keep schema changes minimal in the first pass.

- [ ] **Step 3: Update `Secuencia.General.completarTarea(...)` to pass/reference `referencia` where needed**

Current `TagsMaquina.completarTarea(...)` only receives `celula`, `num`, `tarea`.

You will likely need either:

- to extend its signature to include `referencia`, or
- to resolve `referencia` inside `TagsMaquina`

Preferred:

- pass `referencia` explicitly, because the automatic-cell counter depends on `celula + referencia`

- [ ] **Step 4: Verify runtime reprogramming still uses `rpt = ocurrencia * MC`**

After the counter logic changes, confirm `programarTiemposTareas(...)` still receives the right `rpt`.

- [ ] **Step 5: Manual validation in Dev**

Check at least:

1. start a standard
2. complete a non-`CH` verification task
3. confirm advancement is based on automatic-cell count, not machine-local drift
4. confirm the next scheduled date uses `MC` cadence
5. confirm same-frequency tasks stay aligned

- [ ] **Step 6: Commit**

```bash
git add Tareas/Data/TagsMaquina/code.py Tareas/Secuencia/General/code.py
git commit -m "feat: advance recurring tasks from automatic cell counter"
```

### Task 5: Keep `CH` as counter exception but not as time exception

**Files:**
- Modify: `Tareas/Data/DesviacionTareas/code.py`
- Inspect: `Tareas/Data/General/code.py`

- [ ] **Step 1: Leave `accionesCH_*` counter logic intact**

Do not rewrite tool-life behavior in the same pass.

- [ ] **Step 2: Ensure `rpt` for `CH` still comes from critical-machine time**

Because `obtenerRitmoProd(...)` will now resolve normalized `min`, `CH` should automatically inherit `MC` time if `_Tareas.min` has been normalized correctly.

- [ ] **Step 3: Add logging around `CH` scheduling**

Log:

- task
- cell
- machine
- `vidaTotal`
- `rpt`
- next reprogramming decision

- [ ] **Step 4: Manual validation in Dev**

Check:

- `CH` still waits on tool-life conditions
- `CH` next time uses `MC`, not machine-specific time

- [ ] **Step 5: Commit**

```bash
git add Tareas/Data/DesviacionTareas/code.py Tareas/Data/General/code.py
git commit -m "refactor: keep CH counter logic while using critical machine time"
```

---

## Chunk 3: Admin create/edit behavior

### Task 6: Make minute edits update the critical-machine time globally

**Files:**
- Modify: `Administracion/Data/GestionTareas/code.py:364-401`
- Possibly modify: `Tareas/Data/fromExcelToDB/code.py`

- [ ] **Step 1: Change `editarMinutosMaquina(...)` to update the critical-machine time source**

Current behavior:

- updates only the selected machine's `Tiempo de máquina 1/1`

New behavior:

- editing the critical-machine time updates the effective `min` used by all related recurring tasks for that `celula + referencia`

Recommended implementation:

- update the `MC`/critical-time source row
- then update all affected `_Tareas.min` rows for that `celula + referencia`

Avoid:

- trying to recompute it task by task from the UI layer

- [ ] **Step 2: Refresh summary and live dataset after the edit**

After updating the DB:

- rebuild `_Tareas_Resumen`
- if the edited reference is the active one, rebuild the active dataset for that cell

- [ ] **Step 3: Fix the broken summary-refresh call**

Current code calls:

```python
Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen()
```

without `celula, referencia`.

Fix this while touching the admin flow.

- [ ] **Step 4: Manual validation in Dev**

Check:

- editing the MC minute updates all recurring task cadence
- equal frequencies stay aligned after restart/rebuild
- no stale summary rows remain

- [ ] **Step 5: Commit**

```bash
git add Administracion/Data/GestionTareas/code.py Tareas/Data/fromExcelToDB/code.py Tareas/Secuencia/General/code.py
git commit -m "feat: propagate critical machine minute edits globally"
```

### Task 7: Make new recurring tasks inherit critical-machine time

**Files:**
- Modify: `Tareas/Data/General/code.py:65-186`
- Inspect: `Administracion/Data/GestionTareas/code.py:186-363`

- [ ] **Step 1: Update `crearNuevasTareas(...)` to insert `min = MC`**

Current behavior inserts:

- `min_std = 0`
- `min = None`

New behavior:

- recurring verification tasks should use the current critical-machine time for that `celula + referencia`

- [ ] **Step 2: Update the dataset-scheduling interval in `crearNuevasTareas(...)`**

When creating future rows in the live dataset:

- use `MC`-based `rpt`
- do not use the selected machine's local time

- [ ] **Step 3: Verify admin occurrence edits do not break grouping**

`editarOcurrenciaActualizarTag(...)` currently fetches machine minutes from `Teorico.obtenerTiemposMaquina(...)`.

After normalization this may already behave correctly, but verify it.

- [ ] **Step 4: Manual validation in Dev**

Create a new verification task on a non-critical machine and confirm:

- stored `min` uses `MC`
- visible schedule aligns with other equal-frequency tasks

- [ ] **Step 5: Commit**

```bash
git add Tareas/Data/General/code.py Administracion/Data/GestionTareas/code.py
git commit -m "feat: create recurring tasks with critical machine time"
```

---

## Chunk 4: Bin-picking tray-change behavior

### Task 8: Update bin-picking occurrence when tray size changes

**Files:**
- Modify: `Tareas/Data/DesviacionTareas/code.py:588-625`
- Possibly modify: `Administracion/Data/GestionTareas/code.py`
- Possibly inspect helper tags in `tags.json`

- [ ] **Step 1: Identify the source tag/value for the new tray-piece count**

Before writing code, confirm where the operator writes the new tray quantity.  
This value is not obvious in the current scripts and may live in tags/UDT/UI bindings.

- [ ] **Step 2: Extend `accionesCambioBandejaCarga(...)` to return the new occurrence**

Current behavior only returns:

- `0`
- `1`
- `2`

Refactor it to return structured intent, for example:

```python
{
    "accion": "completar",
    "ocurrenciaNueva": 42
}
```

or a tuple if you want to stay close to current style.

- [ ] **Step 3: Update the matching task occurrence in DB before completing**

When the tray change is confirmed:

1. update occurrence for the matching bin-picking task
2. refresh summary if needed
3. complete the task through the same path as manual completion

Preferred:

- reuse `Tareas.Secuencia.General.completarTarea(...)`
- do not add a second completion path

- [ ] **Step 4: Reprogram the next task with the new occurrence**

After the completion:

- the next cycle must reflect the new tray-piece value

- [ ] **Step 5: Manual validation in Dev**

Check:

1. operator changes tray-piece count
2. task occurrence updates
3. task auto-completes
4. next pending schedule uses the new occurrence

- [ ] **Step 6: Commit**

```bash
git add Tareas/Data/DesviacionTareas/code.py Administracion/Data/GestionTareas/code.py
git commit -m "feat: update bin-picking occurrence on tray change"
```

---

## Chunk 5: Automatic `CH` traceability and synoptic alert

### Task 9: Create a minimal `CH auto` event path

**Files:**
- Modify: `Tareas/Data/DesviacionTareas/code.py`
- Possibly modify: `Tareas/Data/General/code.py`
- Inspect/modify if needed: `tags.json`, `udts.json`

- [ ] **Step 1: Define the smallest shippable version**

First pass should do only:

- detect imminent or reached end-of-life
- create or flag a visible `CH auto` task/state
- preserve traceability

Do not overbuild warning UX before the backend event is stable.

- [ ] **Step 2: Reuse existing `CH` completion/logging infrastructure if possible**

Preferred:

- create a distinct task label such as `CH auto`
- log it through the same DB mechanisms

Avoid:

- inventing a parallel traceability table unless needed

- [ ] **Step 3: Add one synoptic-visible signal**

Best first implementation:

- set a dedicated helper tag the front can show

Do not tightly couple the planner refactor to a large UI rewrite.

- [ ] **Step 4: Manual validation in Dev**

Check:

- a near-EOL tool triggers the event once
- operator can see the alert
- event is traceable in planner/DB

- [ ] **Step 5: Commit**

```bash
git add Tareas/Data/DesviacionTareas/code.py Tareas/Data/General/code.py tags.json udts.json
git commit -m "feat: add automatic tool-change traceability signal"
```

---

## Regression checklist

- [ ] Load `R104587.xlsx` in Dev and confirm no import regressions
- [ ] Start standard for `142D/R104587`
- [ ] Confirm `MC = 3.8` becomes the effective time base
- [ ] Confirm equal-frequency verification tasks align across machines
- [ ] Confirm non-`CH` task advancement follows automatic-cell counter
- [ ] Confirm machine-local counter drift no longer drives recurring-task planning
- [ ] Confirm `CH` still depends on tool life
- [ ] Confirm bin-picking tray change updates occurrence and completes task
- [ ] Confirm admin minute edit propagates globally
- [ ] Confirm no regressions in `_Completados`

---

## Open questions to resolve during execution

1. Exact selector for the critical-machine source row
   - from the workbook we know `MC` exists, but the import path must choose the durable DB representation of that field

2. Exact source of the new tray-piece count in bin picking
   - this likely lives in tags/UI, not in the currently inspected scripts

3. Exact visibility path for the `CH auto` alert
   - may require a helper tag and a small front-end binding change

4. Whether any task besides `CH` should remain outside the generic automatic-cell counter rule
   - current notes say no, but verify `Grafico` and any independent tasks during Dev validation

---

## Recommended execution order

1. Normalize `MC` time in import/runtime
2. Switch recurring-task advancement to automatic-cell counter
3. Update admin create/edit paths
4. Implement bin-picking tray-change occurrence update
5. Implement `CH auto` traceability and synoptic alert

This order gives you working planner semantics early and keeps the higher-risk special automations for later.

---

Plan complete and saved to `docs/superpowers/plans/2026-03-19-mc-cell-counter-refactor.md`. Ready to execute?

