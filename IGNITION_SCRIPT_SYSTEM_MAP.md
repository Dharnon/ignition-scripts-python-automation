# Ignition Script System Map

Date: 2026-03-19  
Branch: `codex/mc-cell-counter-refactor`  
Scope: full repo map of the exported Ignition project scripts, plus the non-Python assets that materially affect runtime behavior.

This document is the "system map" version of the repo.  
It is broader than `IGNITION_CODEPY_WALKTHROUGH.md`: that file is a function walkthrough, while this one also captures runtime ownership, shared contracts, dependencies, tag trees, DB tables, UDT behaviors, and where the current business change fits.

---

## 1. What this repo is doing

At a high level, this project does four things:

1. Loads production standards from Excel into DB tables.
2. Builds a theoretical task plan for each cell and machine.
3. Maintains live task state in Ignition dataset tags and machine helper tags.
4. Reacts to live production/tool/verification signals to complete or reprogram tasks.

The real center of gravity is not WebDev rendering.  
The core behavior lives in project script modules under `Tareas`, `Sinoptico`, `Inicio`, and `Administracion`.

Main runtime layers:

- `Tareas/Secuencia/General/code.py`: orchestration entrypoints.
- `Tareas/Data/General/code.py`: scheduling and completion lifecycle.
- `Tareas/Data/Teorico/code.py`: theoretical dataset generation and reprogramming.
- `Tareas/Data/TagsMaquina/code.py`: per-machine helper datasets and counters.
- `Tareas/Data/Desviacion/code.py`: machine cadence deviation engine.
- `Tareas/Data/DesviacionTareas/code.py`: task-specific automation and completion rules.
- `Tareas/Data/fromExcelToDB/code.py`: Excel import pipeline.
- `Sinoptico/Data/General/code.py`: plant topology, counters, tool info, and live reads.
- `Tareas/Data/GearFlow/code.py`: external SOAP integration for rack/graph flows.
- `Tareas/Data/Independiente/code.py`: independent task generation rules.
- `Inicio` and `Administracion`: user and task admin functions.

---

## 2. Runtime model in one pass

### 2.1 Main startup / planning flow

1. `Tareas.Secuencia.General.cargarEstandar(...)`
2. `Tareas.Data.fromExcelToDB.excelToDb_fb(...)`
3. `Tareas.Data.fromExcelToDB.tareasTable(...)`
4. `Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(...)`
5. `Tareas.Secuencia.General.iniciarEstandar(celula)`
6. `Tareas.Data.Teorico.obtenerTiemposMaquina(...)`
7. `Tareas.Data.Teorico.obtenerTareas(...)`
8. `Tareas.Data.Teorico.generarDatasetTiempos(...)`
9. Write `Dataset/Tareas_Celula{celulaLinea}`
10. Sync helper datasets via `Tareas.Data.TagsMaquina.*`

### 2.2 Runtime completion flow

1. A live event or manual action decides that a task should be completed.
2. `Tareas.Secuencia.General.completarTarea(...)` is called.
3. It resolves `rpt` and `ocurrencia` through `Tareas.Data.General.*`.
4. It updates the machine-local helper dataset using `Tareas.Data.TagsMaquina.completarTarea(...)`.
5. It reprograms pending rows with `Tareas.Data.General.programarTiemposTareas(...)`.
6. It marks the nearest pending dataset row as completed in the global task dataset.
7. It logs the completion in DB through `Tareas.Data.General.completarTareaBD(...)`.

### 2.3 Automatic deviation loops

- `Tareas.Data.Desviacion.desviacionesMaquina()`
  - Looks for cadence drift by comparing expected rhythm vs real piece production.
  - Shifts future task times when the machine/cell is behind.

- `Tareas.Data.DesviacionTareas.desviacionesTareas()`
  - Looks for task-specific conditions.
  - Completes or reprograms tasks like `Descarga`, `Verificacion`, `CH`, `Cambio de carga`, `Grafico`.

---

## 3. Shared runtime contracts

## 3.1 Main tag trees

There are two important tag worlds:

- Live machine tree:
  - `Celula142A/...`
  - `Celula142B/...`
  - `Celula142C/...`
  - `Celula142D/...`

- Helper/project-state tree:
  - `Datos_Celula/Celula142A/...`
  - `Datos_Celula/Celula142B/...`
  - `Datos_Celula/Celula142C/...`
  - `Datos_Celula/Celula142D/...`

This distinction matters:

- `Celula...` usually means live telemetry or live machine status.
- `Datos_Celula...` usually means helper datasets, latches, counters, stored state, and local control metadata.

## 3.2 Central dataset tags

### Global planner dataset

Tag pattern:

- `Dataset/Tareas_Celula{celulaLinea}`

Observed contract:

- Columns: `tarea`, `cuando`, `celula`, `maquina`, `elemento`, `completado`
- Purpose: global visible schedule for one production line / cell group
- Owners:
  - write-heavy: `Tareas.Secuencia.General`, `Tareas.Data.Teorico`, `Tareas.Data.General`
  - read-heavy: `Tareas.Data.DesviacionTareas`, `Tareas.Data.General`, admin flows

### Per-machine task counter dataset

Tag family:

- `Datos_Celula/Celula{X}/Maq_{N}/ContadorTareas`

Observed contract:

- Columns: `fecha`, `tarea`, `ocurrencia`, `contador`, `elementos`
- Purpose: local helper dataset to know how many pieces/life units have accumulated toward each machine task
- Owners:
  - build/sync: `Tareas.Data.TagsMaquina.syncTareas(...)`
  - consume/update: `Tareas.Data.TagsMaquina.completarTarea(...)`

### Piece deviation dataset

Tag family:

- `Datos_Celula/Celula{X}/Maq_{N}/DesviacionPiezas`

Observed contract:

- Columns: `fecha`, `piezas`
- Purpose: remember last deviation checkpoint and piece counter value
- Owners:
  - init/update: `Tareas.Data.TagsMaquina.*`, `Tareas.Data.Desviacion.*`

### Verification helper dataset

Tag family:

- `Datos_Celula/Celula{X}/Maq_{N}/Verificaciones`

Observed contract:

- Columns: `tarea`, `fecha`
- Purpose: remember latest measurement date already consumed for verification tasks
- Owners:
  - `Tareas.Data.DesviacionTareas.accionesVerificacion(...)`

## 3.3 Main DB families

### Task planning DBs

Observed via `constantes.*` usage:

- `Database_Tareas`
  - `..._Secuencia`
  - `..._Tareas`
  - `..._Tareas_Resumen`
  - `..._Completados`

- `Database_Tareas_2`
  - `CDatosMaquina`
  - `CMaquinas`
  - `CGF_RACKS_DATA_MARTS`

### Production/OEE DBs

- `Database_Sinoptico`
  - `COEEproduction`
  - `COEErate`

### Quality DB

- `Database_QDAS`

### User/Admin DBs

- `Database_Inicio`
- `Database_Admin_Usuarios`

## 3.4 Important DB table roles

- `_Secuencia`
  - imported standard rows from Excel
  - raw source for later task generation

- `_Tareas`
  - expanded operational task rows
  - contains occurrence/time/task rows used by planners

- `_Tareas_Resumen`
  - active grouped summary used by runtime
  - one of the most important lookup tables in the system

- `_Completados`
  - completion and start event logging

## 3.5 UDT and tag-event behaviors that matter

From `udts.json` and `tags.json`, there are important runtime scripts outside `code.py`:

- `Hexa Maquina CNC/ContadorPiezas`
  - watches `.../Datos_Dinamicos/ContadorPiezas/Pos1`
  - increments `Piezas_Turno`
  - this affects live counting assumptions

- `Hexa Maquina_Auto/Referencia`
  - on value change, calls `iniciarEstandar(celula)`
  - this is a major runtime trigger, not just a passive tag

These UDT/tag scripts are part of the real system map even if they are not in `code.py`.

---

## 4. Current business context from `tarea.md`

The current branch requirement is no longer just a Torno-only tweak.

Current intent captured in `tarea.md` and `tarea limpiada.md`:

- piece-driven planning should stop depending on each machine's local cadence/counter as the source of truth
- the source of truth for piece count should become the automatic cell counter for `celula + referencia`
- the source of truth for time should become the critical machine `MC` time from the standard
- `CH` remains a special case for counter logic, but its time side should still use `MC`

Why this matters for the map:

- many modules currently assume machine-local cadence
- several task flows rely on `ContadorTareas.contador`
- the new change cuts across import, theoretical generation, completion logic, and helper datasets

The modules most affected by that requirement are:

- `Tareas/Data/fromExcelToDB/code.py`
- `Tareas/Data/Teorico/code.py`
- `Tareas/Data/General/code.py`
- `Tareas/Data/TagsMaquina/code.py`
- `Tareas/Secuencia/General/code.py`

## 4.1 Evidence extracted from `R104587.xlsx`

I was able to inspect the workbook structure directly from the `.xlsx` XML.

Observed sheets:

- `R120638-A`
- `R120636-B`
- `R120631-C`
- `R104587-D`
- `COMBINADOR`
- `ENTREGABLE NEW`
- `MM`
- `Hoja1`

Observed evidence that `MC` exists in the standard:

- in `R104587-D`
  - row 2 contains `REFERENCIA = R104587`
  - row 3 contains `CELULA = 142D`
  - row 4 contains `MC = 3.8`

- in `R104587-D`, task rows show the machine/time classification:
  - row 30: `TALLADORA ... D=MC ... L=1.9 ... P=Tiempo de máquina`
  - row 31 onward: verification rows are marked `R`
  - row 28-29: `CH` rows are explicitly labeled in column `P`

- in `ENTREGABLE NEW`, row 32 shows:
  - `142A | AFEITADORA | AFEITAR | ... | MC | 1 | 1.06`

What that means for implementation:

- `MC` is not just a verbal rule from the meeting notes
- it is already represented in the workbook data
- the import path should be able to identify the critical-machine rhythm from the Excel-derived data model

## 4.2 Additional explicit requirements from your full notes

Compared with the earlier shorter summary, your full notes add these explicit requirements:

1. General rule
   - all tasks except tool changes must advance from:
     - the automatic-cell piece counter
     - the critical-machine cycle time (`MC`)

2. Homogenized planner behavior
   - tasks with the same frequency should align in the planner
   - the operator should be able to perform grouped verifications together

3. Tool-change exception
   - tool changes do not depend on the generic piece counter rule
   - they still depend on tool life
   - but the time base used in planning should still be `MC`

4. Admin create/edit behavior
   - editing the critical-machine cycle time must propagate to all related tasks
   - creating a new verification task must assign critical-machine time even if the selected machine is another one

5. Bin picking tray-change behavior
   - when the tray piece count is updated and confirmed, the matching bin-picking task must:
     - update occurrence to the new value
     - complete automatically as if the operator completed it manually

6. Tool-change traceability
   - when an active tool approaches or reaches end-of-life, the system should:
     - create an automatic tool-change task
     - show a visual warning in the synoptic
     - preserve traceability of that event

7. Delivery path
   - all changes must be implemented and validated in Dev first
   - only after validating the front/back connection should the change move to production

---

## 5. File inventory

Project script modules in scope:

| Path | Main role | Line count |
| --- | --- | ---: |
| `Administracion/Data/GestionTareas/code.py` | admin task editing | 401 |
| `Administracion/Data/GestionUsuarios/code.py` | admin users/roles | 201 |
| `Inicio/Data/GestionUsuarios/code.py` | login/user bootstrap | 55 |
| `Sinoptico/Data/General/code.py` | live machine topology + telemetry helpers | 1031 |
| `Tareas/Data/Desviacion/code.py` | machine deviation loop | 579 |
| `Tareas/Data/DesviacionTareas/code.py` | task deviation loop | 677 |
| `Tareas/Data/fromExcelToDB/code.py` | Excel import and task expansion | 702 |
| `Tareas/Data/GearFlow/code.py` | SOAP integration for racks/graphs | 282 |
| `Tareas/Data/General/code.py` | task scheduling lifecycle | 1114 |
| `Tareas/Data/Independiente/code.py` | independent task generation | 327 |
| `Tareas/Data/TagsMaquina/code.py` | machine helper datasets/counters | 537 |
| `Tareas/Data/Teorico/code.py` | theoretical task generation | 675 |
| `Tareas/Secuencia/General/code.py` | top-level orchestration | 197 |

Non-Python assets that matter:

- `tags.json`
- `udts.json`
- `tarea.md`
- `tarea limpiada.md`
- `IGNITION_CODEPY_WALKTHROUGH.md`

---

## 6. Resource metadata map

Every `resource.json` observed in this repo has the same broad shape:

- `scope`: `A`
- `version`: `1`
- `restricted`: `false`
- `overridable`: `true`
- `files`: `["code.py"]`
- `attributes.lastModification.actor`
- `attributes.lastModification.timestamp`

Observed last modified metadata:

| Resource | Actor | Timestamp |
| --- | --- | --- |
| `Administracion/Data/GestionTareas` | `HEXA` | `2025-10-20T11:32:02Z` |
| `Administracion/Data/GestionUsuarios` | `HEXA` | `2025-10-20T11:32:02Z` |
| `Inicio/Data/GestionUsuarios` | `HEXA` | `2025-10-20T11:32:02Z` |
| `Sinoptico/Data/General` | `S4E2IHX` | `2025-11-06T11:12:33Z` |
| `Tareas/Data/Desviacion` | `S4E2IHX` | `2025-11-05T15:56:35Z` |
| `Tareas/Data/DesviacionTareas` | `ZD72N1T` | `2026-02-03T10:15:00Z` |
| `Tareas/Data/fromExcelToDB` | `S4E2IHX` | `2025-11-28T12:36:27Z` |
| `Tareas/Data/GearFlow` | `S4E2IHX` | `2025-11-28T11:35:14Z` |
| `Tareas/Data/General` | `HEXA` | `2025-10-31T12:08:29Z` |
| `Tareas/Data/Independiente` | `HEXA` | `2025-10-20T11:32:02Z` |
| `Tareas/Data/TagsMaquina` | `HEXA` | `2025-10-31T09:18:27Z` |
| `Tareas/Data/Teorico` | `HEXA` | `2025-10-20T11:32:02Z` |
| `Tareas/Secuencia/General` | `S4E2IHX` | `2025-12-02T13:03:05Z` |

This is useful because it shows where the most recent business logic probably moved:

- very recent behavior change hotspots:
  - `Tareas/Data/DesviacionTareas`
  - `Tareas/Secuencia/General`
  - `Tareas/Data/fromExcelToDB`
  - `Sinoptico/Data/General`

---

## 7. Module dependency map

This is the practical call/dependency map.

| Module | Usually called by | Calls into | Main state touched |
| --- | --- | --- | --- |
| `Tareas/Secuencia/General` | Web/UI/tag events/manual ops | `fromExcelToDB`, `Teorico`, `TagsMaquina`, `General`, `Independiente`, `Sinoptico` | global dataset, machine datasets, task DB |
| `Tareas/Data/General` | `Secuencia`, admin flows, deviation flows | `fromExcelToDB`, `Sinoptico` | global dataset, `_Completados`, task schedule |
| `Tareas/Data/Teorico` | `Secuencia`, `fromExcelToDB` | mostly DB only | `_Tareas`, `_Tareas_Resumen`, generated dataset rows |
| `Tareas/Data/TagsMaquina` | `Secuencia`, `Desviacion`, UDT/tag helpers | `Sinoptico`, `General` | `ContadorTareas`, `DesviacionPiezas`, piece tags |
| `Tareas/Data/Desviacion` | timers | `Sinoptico`, `TagsMaquina`, `General` | `DesviacionPiezas`, schedule offsets |
| `Tareas/Data/DesviacionTareas` | timers | `Sinoptico`, `GearFlow`, `General`, `Secuencia` | task completion/reprogramming, verification helper tags |
| `Tareas/Data/fromExcelToDB` | `Secuencia`, admin/import UI | `Teorico` | `_Secuencia`, `_Tareas`, `_Tareas_Resumen` |
| `Tareas/Data/GearFlow` | `DesviacionTareas`, `Independiente` | external SOAP service | rack and graph criteria |
| `Tareas/Data/Independiente` | `Secuencia` | `Sinoptico` | extra task rows like `Grafico`, cleanup logic |
| `Sinoptico/Data/General` | almost everyone | DB + tags only | machine identity, live status, counters, tools |
| `Inicio/Data/GestionUsuarios` | login/start screen | DB + tags only | startup user context |
| `Administracion/Data/GestionUsuarios` | admin UI | DB only | GPilot user-role mappings |
| `Administracion/Data/GestionTareas` | admin UI | `fromExcelToDB`, `Teorico` | `_Tareas`, `_Tareas_Resumen`, planner dataset |

---

## 8. Detailed module mapping

## 8.1 `Tareas/Secuencia/General/code.py`

Role: top-level orchestration layer for loading standards, starting schedules, and completing tasks.

Depends on:

- `Sinoptico.Data.General`
- `Tareas.Data.fromExcelToDB`
- `Tareas.Data.General`
- `Tareas.Data.Independiente`
- `Tareas.Data.TagsMaquina`
- `Tareas.Data.Teorico`

Key functions:

- `cargarEstandar(filepath, pages)` - L1
  - entrypoint for importing one standard from Excel
  - calls the byte-based Excel loaders
  - expands `_Secuencia` into `_Tareas`
  - rebuilds `_Tareas_Resumen`
  - also triggers special `Cambio de bandeja descarga` handling

- `iniciarEstandar_v0(celula)` - L30
  - legacy full rebuild path
  - rewrites the whole global dataset

- `iniciarEstandar(celula)` - L76
  - current entrypoint to rebuild only one cell's schedule while keeping other cells
  - gets reference
  - gets machine times and task groups
  - generates theoretical rows
  - writes back the merged global dataset
  - syncs per-machine helper datasets
  - refreshes graph task alignment

- `completarTarea(celula, referencia, tipoMaq, tarea, num, manual)` - L137
  - highest-value runtime entrypoint
  - orchestrates the real completion lifecycle
  - resolves cadence data
  - updates local counters
  - reprograms future pending rows
  - writes completion to dataset and DB

- `saveFile(bytes)` - L187
  - writes uploaded file content to a fixed local path

What depends on it:

- manual completion buttons / WebDev handlers
- tag change scripts such as reference-change startup
- operator/admin workflows

Risk notes:

- this module is thin, but it controls the sequencing of the whole system
- if a business change spans import + schedule + runtime, this is usually the first place to review

## 8.2 `Tareas/Data/General/code.py`

Role: scheduling lifecycle engine.

Depends on:

- `Sinoptico.Data.General`
- `Tareas.Data.fromExcelToDB`

Main responsibilities:

- resolve rhythm (`rpt`) and occurrence
- generate missing task rows
- mark tasks complete
- log starts/completions in DB
- reprogram pending task dates
- cleanup old completed rows

Key functions:

- `obtenerRitmoProd(celula, referencia, maquina)` - L1
  - gets effective rhythm from `_Tareas`
  - currently uses `ISNULL(ocurrencia, ocurrenciaStd) * ISNULL(min, min_std)`
  - this function is central for the current `MC` refactor

- `obtenerOcurrencia(celula, referencia, maquina, tarea)` - L33
  - looks up occurrence from `_Tareas_Resumen`
  - matches by task prefix

- `crearNuevasTareas(...)` - L65
- `crearNuevasTareas_v0(...)` - L187
  - adds task rows and refreshes summary
  - if needed, creates future rows for an 8h horizon

- `modificarTiemposMaquinas(...)` - L300
  - shifts future pending task times by an increment
  - used by deviation logic

- `completarTarea_v0(...)` - L364
- `completarTarea(...)` - L448
- `completarTareaConFecha(...)` - L539
  - dataset-level completion operations
  - current version completes nearest pending row and appends a new pending row

- `completarTareaBD_v0(...)` - L623
- `completarTareaBD(...)` - L665
  - DB event logging
  - current version writes into `_Completados` using `idTareasR`

- `iniciarTareaBD_v0(...)` - L723
- `iniciarTareaBD(...)` - L764
  - log task starts

- `borrarTareasCompletadasPorHoras()` - L822
- `borrarTareasCompletadas()` - L870
  - cleanup strategies for completed rows

- `programarTiemposTareas(...)` - L938
  - the core pending-row reprogrammer
  - `desfase` controls whether first row is immediate, normal cadence, or custom offset

- `obtenerProximaFecha(...)` - L1011
- `obtenerUltimaTareaCompletada(...)` - L1060
  - helper lookups over the task dataset

What depends on it:

- `Secuencia.General`
- `Desviacion`
- `DesviacionTareas`
- admin adjustments

Risk notes:

- read-modify-write over dataset tags without explicit locking
- contains both current and legacy flows
- one of the first modules to break if cadence semantics change

## 8.3 `Tareas/Data/Teorico/code.py`

Role: theoretical schedule builder.

Main responsibilities:

- read normalized task/time data from DB
- group and aggregate task rows
- create an 8-hour schedule horizon
- reprogram rows from an anchor time

Key functions:

- `obtenerTiemposMaquina_v0()` - L1
- `obtenerTiemposMaquina(celula, referencia)` - L34
  - get machine minute baselines from `_Tareas`
  - exclude `VARIOS/GRAFICO` and some measurement rows

- `obtenerTiemposMaquina_crearTareas(celula, referencia)` - L83
  - Python-list form for create-task helpers

- `obtenerTareas_v0()` - L139
- `obtenerTareas(celula, referencia)` - L209
  - group `_Tareas` rows into operational task groups

- `generarDatasetTiempos_v0(...)` - L292
- `generarDatasetTiempos(...)` - L352
  - build future schedule rows
  - current version always inserts the first occurrence and then keeps filling within horizon

- `reprogramarTareasDesdeHora(...)` - L416
  - shift-based rebuild from an anchor using existing completed/pending memory

- `marcarTareasComoCompletadasAntesDe(...)` - L556
  - test/helper utility

- `accionesCambioBandejaDescarga(referencia)` - L595
  - uses latest rack quantity to derive occurrence for `Cambio de carga bandejas PP`

What depends on it:

- `Secuencia.General`
- `fromExcelToDB`
- admin refresh flows

Risk notes:

- this is where machine-local time assumptions become a visible schedule
- if `MC` should replace machine-local time, this module must reflect that indirectly through its inputs

## 8.4 `Tareas/Data/TagsMaquina/code.py`

Role: machine-local state manager.

Main responsibilities:

- sync helper datasets from DB
- maintain piece counts and task counters
- compute shift piece totals
- initialize deviation datasets

Depends on:

- `Sinoptico.Data.General`
- `Tareas.Data.Desviacion`
- `Tareas.Data.General`

Key functions:

- `tareasPorMaquinaGeneral(celula)` - L4
  - runs per-machine sync for a whole cell

- `tareasPorMaquina(celula, referencia, maquina)` - L28
  - fetches task groups for one machine from `_Tareas_Resumen`

- `syncTareas(celula, referencia, maquina, num)` - L55
  - builds/updates `ContadorTareas`
  - preserves prior counters when possible
  - inserts start events for new rows

- `piezasMaquinaTurno(idMaquina)` - L143
  - PLC-oriented shift piece count from DB history

- `piezasMaquinaTurno_Automatica(celula, referencia)` - L217
  - automatic-cell shift count from `COEEproduction`
  - very important for the current business change

- `completarTarea(celula, num, nombreTarea)` - L277
  - local counter decrement/advance helper
  - return contract:
    - `0`: task just reached zero / ready to complete
    - positive: still in progress
    - `-1`: overflow
    - `-2`: error

- `actualizarPiezasPorTurno(celula, num)` - L386
  - refreshes `Piezas_Turno`

- `inicializarDatasetPiezas(celula, num)` - L417
  - initializes `DesviacionPiezas`

- `inicializarTodosLosDatasetsPiezas(celula)` - L501
  - mass initialization per cell

What depends on it:

- `Secuencia.General`
- `Desviacion`
- UDT/tag logic indirectly

Risk notes:

- local helper counters can drift from global planner truth
- current requirement is specifically trying to reduce that mismatch for piece-based tasks

## 8.5 `Tareas/Data/Desviacion/code.py`

Role: machine-cadence deviation engine.

Main responsibilities:

- compare expected output vs real output
- detect delay in minutes
- shift future task rows when production is behind

Depends on:

- `Sinoptico.Data.General`
- `Tareas.Data.TagsMaquina`
- `Tareas.Data.General`

Key functions:

- `desviacionesMaquina()` - L1
  - main sweep across cells and machines
  - chooses counter source by machine type

- `obtenerDesviacionMaquinaAuto(celula, num)` - L76
  - auto-based fallback / mirror behavior

- `obtenerUltimoRegistro_PLC(...)` - L116
  - deviation from PLC history rows

- `obtenerUltimoRegistro_CNC(...)` - L233
  - deviation from CNC tag counter deltas

- `obtenerUltimoRegistro_PLC_Auto(...)` - L306
  - automatic-cell deviation

- `obtenerUltimoRegistro_PLC_v2(...)` - L382
  - variant for `BROCHADORA/AFEITADORA`

- `obtenerUltimoRegistro_PLC_v3(...)` - L463
  - variant for `MARCADORA/LAVADORA/BIN PICKING`

What depends on it:

- periodic timer automation

Risk notes:

- a lot of business behavior is encoded as machine-type branching
- if the "real" production counter moves to the cell level, this module must stay aligned

## 8.6 `Tareas/Data/DesviacionTareas/code.py`

Role: task-specific automation engine.

This is one of the most business-heavy modules in the repo.

Depends on:

- `Sinoptico.Data.General`
- `Tareas.Data.GearFlow`
- `Tareas.Data.General`
- `Tareas.Secuencia.General`

Key functions:

- `desviacionesTareas()` - L1
  - main loop for task-specific automation
  - branches by task family

- `tareasPorMaquina(celula, referencia, maquina)` - L166
  - active tasks for one machine

- `accionesDescarga(celula, proxTarea)` - L192
  - lavadora/saturation logic
  - may keep, complete, or shift by +20 min / immediate

- `accionesVerificacion(tarea, num, referencia, celula, maquina)` - L227
  - looks at QDAS measurement freshness
  - also updates helper `Verificaciones` dataset

- `accionesCH_PLC(celula, num)` - L421
  - PLC tool-life remaining

- `accionesCH_CNC_Torno_v0(celula, num)` - L446
- `accionesCH_CNC_Torno(celula, num)` - L488
  - Torno tool grouping / useful-life logic
  - one of the current business-change hotspots

- `accionesCH_CNC_Talladora(celula, num)` - L563
  - talladora CH life logic

- `accionesCambioBandejaCarga(celula, num)` - L588
  - uses saturation and `Pre` latch

- `accionesCambioBandejaDescarga(celula, num, referencia)` - L626
  - uses rack-change detection

What depends on it:

- periodic timer automation

Risk notes:

- lots of string-prefix behavior
- lots of type-specific rules
- small changes here can have large behavioral impact in production

## 8.7 `Tareas/Data/fromExcelToDB/code.py`

Role: standard import and normalization pipeline.

Depends on:

- `Tareas.Data.Teorico`

Main responsibilities:

- parse Excel
- validate structure
- clear/inactivate old rows
- insert `_Secuencia`
- transform `_Secuencia` into `_Tareas`
- rebuild `_Tareas_Resumen`

Key functions:

- `excelToDataSet(...)` - L1
  - Apache POI-based parser with handling for bounds, formulas, and dates

- `excelToDataSet_Anterior(...)` - L97
  - legacy parser

- `checkStructure(...)` - L206
  - validates dataset headers and expected schema

- `excelToDb(filepath, page)` - L297
- `excelToDb_fb(fileBytes, page)` - L616
  - insert one sheet into `_Secuencia`
  - the byte-based one is transaction-protected

- `multipleExcelToDb(filepath, pages)` - L399
- `multipleExcelToDb_fb(fileBytes, pages)` - L602
  - multi-page wrappers

- `deleteTable(...)` - L412
- `inactivoTable(...)` - L438
- `deleteTable_Secuencia()` - L464
  - cleanup/inactivation helpers

- `tareasTable(celula, referencia)` - L483
  - expands `_Secuencia` into operational `_Tareas`
  - important note: current repo leaves `_Tareas.min` as `NULL` and uses `min_std`

- `insertarTareasEnTablaResumen(celula, referencia)` - L547
  - rebuilds active summary rows from the theoretical grouping

What depends on it:

- `Secuencia.General`
- standard import screens
- admin task editing workflows

Risk notes:

- this is the correct insertion point if time semantics need to be normalized at import time
- if `MC` should be written into `_Tareas.min`, this module is one of the cleanest places to do it

## 8.8 `Tareas/Data/GearFlow/code.py`

Role: external SOAP integration for rack/graph criteria.

Main responsibilities:

- call the external service
- map cell and date windows into GearFlow query parameters
- return rack/graph criteria

Key functions:

- `cambioHerramientas(...)` - L3
  - narrow window around target date
  - returns first matching criterion

- `grafico(...)` - L66
  - current-shift graph lookup

- `filtrar_racks(...)` - L145
  - SOAP call and XML parsing
  - optional filtering by date, type, reference, cell, tool family

What depends on it:

- `DesviacionTareas`
- `Independiente`

Risk notes:

- external service and XML parsing are natural failure points
- if graph/rack behavior looks strange, this module is a prime suspect

## 8.9 `Tareas/Data/Independiente/code.py`

Role: independent or special generated tasks that are not pure standard cadence rows.

Main responsibilities:

- create/update Torno special tasks
- schedule cleanup logic
- create/update `Grafico`

Depends on:

- `Sinoptico.Data.General`

Key functions:

- `crearTareaTorno(celula, num)` - L1
  - computes combined tool-life max for same-prefix Torno tools

- `crearTareaLimpieza(celula)` - L24
  - schedules cleanup based on candidate tasks and minimum elapsed time

- `crearTareaGrafico(celula)` - L140
  - creates a graph task aligned with CH candidates or fallback time

- `actualizarTareaGrafico(celula)` - L222
  - moves existing pending graph task to the best candidate in shift

What depends on it:

- `Secuencia.General.iniciarEstandar(...)`

Risk notes:

- these tasks are intentionally special-case
- they often sit outside the "pure machine cadence" model

## 8.10 `Sinoptico/Data/General/code.py`

Role: plant topology, live machine metadata, live counters, and tool information.

This is the largest utility module and a foundation for almost every other module.

Function groups and lines:

### Reference and OEE status

- `obtenerReferencia(celula)` - L1
- `obtenerOEEStatus_v0(celula, referencia)` - L20
- `obtenerOEEStatus(celula, referencia)` - L95

### Machine metadata and topology

- `obtenerAuto(celula, num)` - L192
- `obtenerPLC_CNC(celula, num)` - L212
- `obtenerPosicion(celula, num)` - L232
- `obtenerPosicionAuto(celula, num)` - L250
- `obtenerTipoMaquina(celula, num)` - L268
- `obtenerIDMaquina(celula, num)` - L315
- `obtenerIDMaquinaOriginal(celula, num)` - L916
- `obtenerNumeroMaquina(celula, maquina)` - L993
- `obtenerConexion(celula, num)` - L937

### Live machine values

- `obtenerDisponibilidad(celula, num)` - L338
- `obtenerCiclo(celula, num)` - L356
- `obtenerSaturacion(celula, num)` - L889
- `obtenerAlarmas(celula, num)` - L529

### Counters and production

- `obtenerCNCContador(celula, num)` - L374
- `obtenerAutoContador(celula, referencia)` - L564
- `elegirPLCContador(celula, num, idMaquina, referencia)` - L618
- `obtenerPLCContador(celula, num, idMaquina)` - L636
- `obtenerPLCContador_v2(celula, num, idMaquina)` - L737

### Tool data

- `obtenerCNCHerramienta(celula, num)` - L405
- `obtenerCNCHerramientaConNombre(celula, num)` - L459
- `obtenerCNCHtaNombre(celula, num)` - L960
- `obtenerAutoHerramienta(celula, num)` - L839
- `obtenerAutoHerramientaConNombre(celula, num)` - L864

What depends on it:

- almost every runtime module

Risk notes:

- if a machine ID/type/reference lookup is wrong, many higher-level modules will behave wrong while appearing "fine"
- this module is where the real world is translated into runtime identity

## 8.11 `Inicio/Data/GestionUsuarios/code.py`

Role: startup user bootstrap.

Key function:

- `obtenerDatos(numUsuario)` - L1
  - pads user code to 8 digits
  - looks up corporate identity and local GPilot role
  - writes `Variables/Inicio/idUsuario`
  - returns `[nombre, usuario, mail, rol, idUsuario]`

What depends on it:

- login/start screen

## 8.12 `Administracion/Data/GestionUsuarios/code.py`

Role: admin user and role management.

Key functions:

- `filtroCrear(valorFiltro)` - L1
  - search candidate users not yet created in the local app

- `mostrarRoles()` - L49
  - list all roles

- `mostrarUsuarios()` - L76
  - join local role mapping with corporate info

- `crearUsuarios(idUsuario, idRol, idCreador)` - L133
  - create mapping

- `eliminarUsuarios(idUsuario)` - L157
  - delete mapping

- `actualizarRolUsuario(idUsuario, idRol, idCreador)` - L176
  - update role and editor metadata

What depends on it:

- admin UI

## 8.13 `Administracion/Data/GestionTareas/code.py`

Role: admin editing surface for tasks and cadence.

Depends on:

- `Tareas.Data.fromExcelToDB`
- `Tareas.Data.Teorico`

Key functions:

- `mostrarTareas()` - L1
  - builds the admin task view from task rows plus machine base minutes

- `eliminarTarea(...)` - L83
  - delete one task row from `_Tareas`
  - refresh summary

- `eliminarTareaActualizarTag(...)` - L123
  - remove matching element from global dataset row

- `editarOcurrenciaTareas(...)` - L186
  - update occurrence in DB and refresh summary

- `editarOcurrenciaActualizarTag(...)` - L234
  - move one element from old occurrence-group to new one in the planner dataset

- `editarMinutosMaquina(...)` - L364
  - update base machine minute row and refresh summary

What depends on it:

- task admin UI

Risk notes:

- this module edits both DB and planner tag state
- if an admin path and runtime path disagree on grouping, drift can appear quickly

---

## 9. Cross-cutting patterns

Patterns repeated across the repo:

- task-family matching is often done with `startswith(...)`
- machine-type branching is common and business-heavy
- dataset tags are read, transformed in Python, then written back whole
- several modules maintain both current and `_v0` logic
- DB rows and tags both act as sources of truth depending on the path
- the real system includes UDT/tag event scripts, not only `code.py`

This means:

- small naming changes can break behavior silently
- races are possible if multiple timers/users touch the same dataset tag
- "where truth lives" is contextual and not always obvious

---

## 10. Known fragile points

1. Global dataset write races
   - many flows do read-modify-write on the same dataset tag
   - no explicit lock orchestration is visible in these project scripts

2. Local counters vs planner truth
   - `ContadorTareas` is helpful, but it can diverge from the global schedule
   - the current requirement is effectively trying to fix this for piece-driven tasks

3. Heavy business branching by machine type
   - Torno, Talladora, Afeitadora, Lavadora, Bin Picking, CELULA, CNC/PLC paths are all different

4. External data dependencies
   - QDAS
   - OEE tables
   - SOAP GearFlow
   - telemetry tables
   - if one of these changes, runtime logic can degrade

5. Mixed legacy/current implementations
   - `_v0` functions remain in several key modules
   - they complicate understanding and increase maintenance risk

6. Some UI-only calls inside script modules
   - for example `system.gui.errorBox` appears in import logic
   - scope assumptions matter in Ignition

7. Summary rebuild coupling
   - many edits eventually require `_Tareas_Resumen` refresh
   - if that refresh is skipped or called with the wrong context, runtime lookups become stale

---

## 11. Suggested reading order for a new developer

If someone needs to understand this project fast, the best order is:

1. `tarea.md`
2. `tarea limpiada.md`
3. `Tareas/Secuencia/General/code.py`
4. `Tareas/Data/General/code.py`
5. `Tareas/Data/Teorico/code.py`
6. `Tareas/Data/TagsMaquina/code.py`
7. `Tareas/Data/DesviacionTareas/code.py`
8. `Tareas/Data/Desviacion/code.py`
9. `Tareas/Data/fromExcelToDB/code.py`
10. `Sinoptico/Data/General/code.py`
11. `udts.json`
12. `tags.json`

Why this order works:

- it starts with the business goal
- then the orchestration layer
- then the scheduling truth
- then helper state and automation rules
- then the lower-level live machine helpers

---

## 12. Practical "who owns what" summary

- If the issue is "the imported standard is wrong":
  - start in `fromExcelToDB`

- If the issue is "the visible schedule is wrong at startup":
  - start in `Secuencia.General` and `Teorico`

- If the issue is "the machine counter says one thing and the task schedule says another":
  - start in `TagsMaquina`, `General`, and relevant UDT scripts

- If the issue is "the task should have auto-completed but did not":
  - start in `DesviacionTareas`

- If the issue is "everything is delayed by production drift":
  - start in `Desviacion`

- If the issue is "machine identity/type/reference is wrong":
  - start in `Sinoptico.General`

- If the issue is "an admin change did not reach runtime":
  - start in `Administracion/Data/GestionTareas`

---

## 13. Final notes

This repo is not just "a set of scripts".  
It is a layered runtime where:

- DB tables define the standard,
- dataset tags define the live operational view,
- helper machine tags store local memory,
- UDT/tag events trigger orchestration,
- deviation loops keep the plan aligned with reality.

For implementation work, the most important rule is:

- always identify which layer is the source of truth for the behavior you want to change

In the current business request, that exact question is the heart of the refactor:

- piece truth should move toward the automatic cell counter
- time truth should move toward `MC`
- and the current machine-local helper datasets should become supporting state, not the primary planner truth
