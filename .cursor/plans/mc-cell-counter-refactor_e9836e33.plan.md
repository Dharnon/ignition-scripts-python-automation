---
name: mc-cell-counter-refactor
overview: Implement the end-to-end refactor so piece-driven tasks use the automatic cell counter and a single critical-machine (MC) time across import, theoretical schedule generation, runtime reprogramming, and helper counters, using the provided Excel R104587 as the reference case.
todos:
  - id: excel-behavior-note
    content: Summarize how to derive MC and which tasks are piece-dependent using R104587 and tarea.md as the business source.
    status: completed
  - id: import-normalization
    content: Normalize MC-based minutes for piece-driven tasks during import in fromExcelToDB and keep DB schemas consistent.
    status: completed
  - id: teorico-mc-consumption
    content: Update Teorico module to build theoretical schedules using MC-based times so equal frequencies align.
    status: completed
  - id: runtime-mc-cell-counter
    content: Refactor General, TagsMaquina, and Secuencia.General so runtime completion and reprogramming use MC + automatic cell counter.
    status: completed
  - id: remove-artificial-celula-line
    content: Remove dependence on synthetic CELULA/pieza-terminada rows while keeping Grafico and tray-change behaviors correct.
    status: completed
  - id: admin-mc-consistency
    content: Ensure GestionTareas admin edits propagate MC semantics consistently across DB and planner dataset.
    status: completed
  - id: mc-refactor-testing
    content: Execute functional tests using R104587 to validate MC + cell-counter behavior end-to-end.
    status: completed
  - id: mc-doc-update
    content: Document the new MC + cell-counter model location of truth and remaining open questions for future work.
    status: completed
isProject: false
---

### MC + cell-counter refactor implementation plan

#### 1. Clarify behavior on the Excel side (read-only)

- **Files**: `[IGNITION_SCRIPT_SYSTEM_MAP.md](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/IGNITION_SCRIPT_SYSTEM_MAP.md)`, the reference workbook `R104587.xlsx` (already analyzed in the system map), and `[tarea.md](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/tarea.md)`.
- **Goal**: Treat `R104587.xlsx` purely as a specification/example: confirm from the doc what `MC` means, how it appears in the sheet (cell-level value, per-task flags like `D=MC`), and which tasks are considered "dependientes de piezas" vs excluded (medición, varios, gráfico, etc.).
- **Outcome**: A short internal note in the plan describing: (a) how to derive the single `MC` value for a `(celula, referencia)` pair from Excel-derived DB rows, and (b) a textual rule for which `_Tareas` rows must use that `MC` vs remain on their own semantics (e.g. CH tool life, non-piece tasks).

#### 2. Normalize MC at import time in `fromExcelToDB`

- **Files**: `[Tareas/Data/fromExcelToDB/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/fromExcelToDB/code.py)` and, if needed, `[Tareas/Data/Teorico/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/Teorico/code.py)`.
- **Change**:
  - In `tareasTable(celula, referencia)`, after expanding `_Secuencia` into `_Tareas`, compute the critical-machine time per `(celula, referencia)` using the business rule from step 1.
  - For all `_Tareas` rows classified as piece-dependent, write that `MC` into a dedicated minute column used by runtime cadence — either repurpose `_Tareas.min` (currently left `NULL` and relying on `min_std`) or add/ensure an `min_mc`/similar field in the intermediate dataset before insert, but keep the DB schema usage consistent with existing queries.
  - Preserve existing behavior for CH/tool-change rows so their occurrence still comes from tool life, but ensure their time component will later multiply by `MC` instead of a local per-machine minute.
- **Outcome**: After importing a standard with `excelToDb_fb` and `tareasTable`, `_Tareas` contains consistent MC-based minutes for all piece-driven tasks in that cell, and `_Tareas_Resumen` reflects this via the existing `insertarTareasEnTablaResumen` path.

#### 3. Make theoretical schedule generation consume MC instead of local machine minutes

- **Files**: `[Tareas/Data/Teorico/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/Teorico/code.py)`.
- **Change**:
  - In `obtenerTiemposMaquina(celula, referencia)` and `obtenerTiemposMaquina_crearTareas(celula, referencia)`, switch the source of machine time for piece-driven tasks to the MC-normalized field introduced in step 2 (or to the `(ocurrencia * MC)` rhythm if the DB already stores it that way).
  - Ensure that grouping logic in `obtenerTareas(...)` uses this unified MC-based time for tasks marked as piece-dependent and keeps exclusions for measurement/VARIOS/GRAFICO/other non-piece tasks as described in `tarea.md`.
  - In `generarDatasetTiempos(...)`, rely on these MC-based times so that tasks with the same frequency line up on the same time blocks across machines for a given `(celula, referencia)`.
- **Outcome**: When `iniciarEstandar(celula)` rebuilds the planner dataset, `Dataset/Tareas_Celula{celulaLinea}` shows aligned times for all piece-dependent tasks with the same frequential, and the visible schedule no longer depends on per-machine `min`.

#### 4. Switch runtime rhythm and reprogramming to MC + cell counter

- **Files**: `[Tareas/Data/General/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/General/code.py)`, `[Tareas/Secuencia/General/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Secuencia/General/code.py)`, and `[Tareas/Data/TagsMaquina/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/TagsMaquina/code.py)`.
- **Change in `General`**:
  - Update `obtenerRitmoProd(celula, referencia, maquina)` so that, for piece-dependent tasks, it no longer multiplies a per-machine occurrence by a per-machine `min`/`min_std`, but instead uses the unified MC-based time from `_Tareas` or `_Tareas_Resumen`. Keep CH/tool-change as a special case: occurrence still from life logic, but time base = MC.
  - Make sure `programarTiemposTareas(...)` treats the new rhythm consistently, without reintroducing machine-local cadence.
- **Change in `TagsMaquina`**:
  - For piece-driven tasks, stop using `ContadorTareas.contador` as the primary cadence source during completion; instead, use `piezasMaquinaTurno_Automatica(celula, referencia)` and/or the automatic-cell production counters from `Sinoptico.Data.General` to know when the group of tasks should have advanced.
  - Keep or simplify `ContadorTareas` as helper/diagnostic state (e.g. to show remaining pieces per task), but its divergence should no longer affect planner truth.
  - Preserve `completarTarea`'s return contract (`0`, positive, `-1`, `-2`) or document and adjust all call sites if a different contract is chosen.
- **Change in `Secuencia.General`**:
  - In `completarTarea(...)`, use the updated helper from `TagsMaquina` and the new MC-based rhythm from `General.obtenerRitmoProd` to reprogram the next pending rows; ensure that the cell-level counter is the effective source for how far to advance, not a per-machine tag.
- **Outcome**: Runtime completion and reprogramming use the automatic cell counter and MC for all piece-dependent tasks; CH continues to be driven by tool life but scheduled in time with MC.

#### 5. Remove reliance on artificial CELULA/pieza-terminada lines and adjust special tasks

- **Files**: `[Tareas/Data/Teorico/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/Teorico/code.py)`, `[Tareas/Data/Independiente/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Tareas/Data/Independiente/code.py)`, and any place currently using a synthetic "CELULA / pieza terminada / tiempo de maquina" line (as described in `tarea.md`).
- **Change**:
  - Identify where the artificial CELULA line is created/consumed (e.g. for `Grafico`) and refactor that logic to derive its cadence directly from the MC-based schedule and the automatic cell counter, without needing a fake row in the standard.
  - Ensure `accionesCambioBandejaDescarga(...)` and `crear/actualizarTareaGrafico(...)` still work, but now look at the unified MC-based model instead of a special CELULA row.
- **Outcome**: The planner no longer requires an invented CELULA/pieza-terminada time row; graph and tray-change tasks still behave as expected but are anchored on the new model.

#### 6. Keep admin editing consistent with MC semantics

- **Files**: `[Administracion/Data/GestionTareas/code.py](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/Administracion/Data/GestionTareas/code.py)`.
- **Change**:
  - In `editarMinutosMaquina(...)`, ensure that when an admin updates the critical-machine time for a `(celula, referencia)`, the MC-normalized value used for piece-dependent tasks is updated consistently across `_Tareas`, `_Tareas_Resumen`, and the planner dataset, without reintroducing machine-local differences.
  - In `editarOcurrenciaTareas(...)` and `editarOcurrenciaActualizarTag(...)`, verify that occurrence edits for piece-dependent tasks keep the "same frequential -> same block" alignment (e.g. by updating all affected tasks for a given frequency group when needed).
- **Outcome**: Admin-side edits continue to work and now fully respect the MC + cell-counter model instead of drifting back to per-machine semantics.

#### 7. Testing strategy using `R104587.xlsx` as the reference

- **Files / tools**: Manual tests via the Ignition gateway/designer and, if present, any ad-hoc test scripts under `tests` or similar (none are listed yet).
- **Tests**:
  - Import `R104587.xlsx` through the usual UI or script entrypoint (`cargarEstandar` / `excelToDb_fb`) and confirm in DB (`*_Tareas`, `*_Tareas_Resumen`) that all piece-driven tasks for `celula=142D` share the same MC-derived minute value.
  - Run `iniciarEstandar(142D)` and inspect `Dataset/Tareas_Celula...` to verify that two tasks with the same frequency but on different machines now land on the same scheduled time blocks.
  - Complete a representative piece-driven task via `completarTarea(...)` and observe that reprogramming uses the automatic cell counter and MC time (e.g. by comparing expected next-time vs actual), with DB logging intact.
  - Exercise a CH/tool-change scenario to ensure tool life logic still drives when tasks appear, but durations use MC.
  - Exercise a Grafico/tray-change path so that it no longer depends on a CELULA artificial line yet still updates correctly when the tray piece count changes.
- **Outcome**: A checklist of manual verifications matching the "Pruebas funcionales mínimas" from `tarea.md`, adapted to the new implementation.

#### 8. Documentation and future-proofing

- **Files**: A short spec or summary (can be appended to `[IGNITION_SCRIPT_SYSTEM_MAP.md](c:/Users/Usuario/Desktop/proyectos/ignition-scripts-python-automation/IGNITION_SCRIPT_SYSTEM_MAP.md)` or saved as a new doc under `docs/superpowers/specs/`), plus `tarea.md` if you want to mark the status.
- **Change**:
  - Document, in 1–2 paragraphs, where `MC` truth now lives (DB tables/columns) and how the automatic cell counter is used in place of `ContadorTareas` for planning truth.
  - Note any remaining open questions (e.g. fallback when MC is missing, edge cases for non-piece tasks) so future changes can be localized.
- **Outcome**: Future developers can quickly see how the MC + cell-counter model is wired through import, theoretical planning, runtime execution, and admin tools.

