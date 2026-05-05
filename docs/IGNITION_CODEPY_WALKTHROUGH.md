# Ignition `code.py` Walkthrough (Scripting Project)

Date: 2026-03-03  
Scope: All `code.py` scripts under this workspace (13 modules).

## 1) Runtime model (quick map)

- **Main orchestration**: `Tareas/Secuencia/General/code.py`
- **Task scheduling lifecycle**: `Tareas/Data/General/code.py`
- **Theoretical generation/reprogramming**: `Tareas/Data/Teorico/code.py`
- **Machine-local counters/datasets**: `Tareas/Data/TagsMaquina/code.py`
- **Deviation engines**: `Tareas/Data/Desviacion/code.py`, `Tareas/Data/DesviacionTareas/code.py`
- **Excel import pipeline**: `Tareas/Data/fromExcelToDB/code.py`
- **External integration (SOAP GearFlow)**: `Tareas/Data/GearFlow/code.py`
- **Helpers for independent tasks**: `Tareas/Data/Independiente/code.py`
- **Plant/synoptic reads**: `Sinoptico/Data/General/code.py`
- **User/admin scripts**: `Inicio/Data/GestionUsuarios/code.py`, `Administracion/Data/GestionUsuarios/code.py`, `Administracion/Data/GestionTareas/code.py`

Common shared state:
- Global dataset tag: `Dataset/Tareas_Celula{celulaLinea}`
- Per-machine dataset tags: `Datos_Celula/Celula{X}/Maq_{N}/...`
- Dynamic tables: `constantes.LINEA + "_..."`

---

## 2) Per-file function walkthrough

## `Tareas/Secuencia/General/code.py`

- `cargarEstandar(filepath, pages)`
  - Loads standard from Excel pages into DB pipeline.
  - Calls: `fromExcelToDB.excelToDb_fb`, `Teorico.accionesCambioBandejaDescarga`, `fromExcelToDB.tareasTable`, `insertarTareasEnTablaResumen`.
  - Returns `True/False`.

- `iniciarEstandar_v0(celula)`
  - Legacy starter: generates theoretical dataset and writes full global task dataset.
  - Side effects: writes global task dataset tag; initializes machine counters + piece datasets.

- `iniciarEstandar(celula)`
  - Current starter: replaces rows only for selected cell in global dataset, keeps other cells.
  - Calls `Teorico.obtenerTiemposMaquina`, `Teorico.obtenerTareas`, `Teorico.generarDatasetTiempos`, `TagsMaquina.tareasPorMaquinaGeneral`, `TagsMaquina.inicializarTodosLosDatasetsPiezas`, `Independiente.actualizarTareaGrafico`.
  - Returns `True/False`.

- `completarTarea(celula, referencia, tipoMaq, tarea, num, manual)`
  - Full completion flow.
  - Gets `rpt` and `ocurrencia`, updates per-machine counter (`TagsMaquina.completarTarea`), reprograms future schedule (`programarTiemposTareas`), marks task complete in dataset + DB (`completarTarea`, `completarTareaBD`).
  - Counter result contract: `0`, positive, `-1`, `-2`.

- `saveFile(bytes)`
  - Writes uploaded bytes to a fixed local path; returns message string.

## `Tareas/Data/General/code.py`

- `obtenerRitmoProd(celula, referencia, maquina)`
  - Query `_Tareas` for `Tiempo de m%`; returns `ISNULL(ocurrencia,ocurrenciaStd)*ISNULL(min,min_std)`.
  - Fallback on error: `1.0`.

- `obtenerOcurrencia(celula, referencia, maquina, tarea)`
  - Reads active tasks from `_Tareas_Resumen`, matches `startswith(tarea)`, returns occurrence.

- `crearNuevasTareas(...)` / `crearNuevasTareas_v0(...)`
  - Insert task into `_Tareas`, refresh `_Tareas_Resumen`, then patch task dataset tag if reference is currently active.
  - If no existing task row, generates recurring rows for ~8h window.

- `modificarTiemposMaquinas(CelulaObjetivo, MaquinaObjetivo, incremento)`
  - Adds minute/second offset to all non-completed matching tasks in global dataset tag.

- `completarTarea_v0(...)`
  - Finds nearest pending task (`startswith`) and marks it completed at `now`.

- `completarTarea(...)`
  - Marks nearest pending task completed and appends a new pending row at `now + 8h`.

- `completarTareaConFecha(...)`
  - Same as completion flow, but completion timestamp is provided by caller.

- `completarTareaBD_v0(...)`
  - Logs completion to legacy `_Completado` with denormalized task fields.

- `completarTareaBD(...)`
  - Logs completion to `_Completados` with FK to `_Tareas_Resumen` (`idTareasR`).

- `iniciarTareaBD_v0(...)` / `iniciarTareaBD(...)`
  - Inserts start events for tasks; v0 legacy schema, current version uses `_Completados` + FK.

- `borrarTareasCompletadasPorHoras()`
  - Deletes completed rows older than configured `Variables/Tareas/horasBorrarTareas`.

- `borrarTareasCompletadas()`
  - For each `(tarea, celula, maquina)`, keeps only latest completed row; removes older completed rows.

- `programarTiemposTareas(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo, ocurrencia, rpt, desfase)`
  - Recomputes `cuando` for pending matched rows.
  - `desfase`: `-1` immediate-first, `0` normal cadence, `>0` custom first offset.

- `obtenerProximaFecha(...)`
  - Returns nearest pending date for task prefix.

- `obtenerUltimaTareaCompletada(...)`
  - Returns latest completed date for task prefix (default epoch if not found).

## `Tareas/Data/Teorico/code.py`

- `obtenerTiemposMaquina_v0()` / `obtenerTiemposMaquina(celula, referencia)`
  - Reads machine durations from `_Tareas` (`Tiempo de m%`) excluding `VARIOS/GRAFICO` and `MEDICI%` elements.

- `obtenerTiemposMaquina_crearTareas(celula, referencia)`
  - Returns machine list (as Python list of dicts) for create-task workflows.

- `obtenerTareas_v0()` / `obtenerTareas(celula, referencia)`
  - Aggregates tasks from `_Tareas` excluding time/load/transfer rows; concatenates elements and normalizes task labels.

- `generarDatasetTiempos_v0(datasetMinutos, datasetTareas)`
  - Generates 8h recurring schedule from machine minutes × occurrence.

- `generarDatasetTiempos(datasetMinutos, datasetTareas)`
  - Current version; always inserts first occurrence then additional within 8h horizon.

- `reprogramarTareasDesdeHora(datasetMinutos, datasetTareas, horaBase=None)`
  - Shift reprogramming logic using current dataset memory (completed and pending anchors), writes refreshed global dataset.

- `marcarTareasComoCompletadasAntesDe(horaLimite)`
  - Test helper: marks all rows with `cuando < horaLimite` as completed.

- `accionesCambioBandejaDescarga(referencia)`
  - Reads latest rack quantity (`RS_CANTIDAD`) from external table, computes `1/valor`, updates occurrence in `_Secuencia` for `CELULA`/`Cambio de carga bandejas PP`.

## `Tareas/Data/TagsMaquina/code.py`

- `tareasPorMaquinaGeneral(celula)`
  - Iterates all machines in cell and runs machine-level sync.

- `tareasPorMaquina(celula, referencia, maquina)`
  - Returns task/occurrence/elements from active `_Tareas_Resumen` rows.

- `syncTareas(celula, referencia, maquina, num)`
  - Synchronizes machine `ContadorTareas` dataset with DB.
  - Preserves existing `fecha/contador`, inserts new tasks with `contador=0`, removes obsolete tasks, initializes DB start event for newly added tasks.

- `piezasMaquinaTurno(idMaquina)`
  - PLC counting via DB (`CDatosMaquina`, `IdTipoDatoMaquina=3`) between shift boundaries; counts `1 -> 0` transitions.

- `piezasMaquinaTurno_Automatica(celula, referencia)`
  - Cell-automatic shift count from `COEEproduction` filtered by `job`, `AssetID`, shift window.

- `completarTarea(celula, num, nombreTarea)`
  - Decrements task counter by `ocurrencia` inside machine dataset.
  - Return contract: `0` reset to zero, positive in-progress counter, `-1` overflow, `-2` error.

- `actualizarPiezasPorTurno(celula, num)`
  - Updates `Piezas_Turno`; CNC uses `0` baseline, PLC reads live counter tag.

- `inicializarDatasetPiezas(celula, num)`
  - Creates/overwrites `DesviacionPiezas` dataset with current `(fecha,piezas)` depending on machine type + source.

- `inicializarTodosLosDatasetsPiezas(celula)`
  - Runs initialization for all machines in cell (plus CNC turnover update).

## `Tareas/Data/Desviacion/code.py`

- `desviacionesMaquina()`
  - Main machine deviation sweep across cells/machines.
  - Chooses counter source by machine type (`CELULA`, `BROCHADORA/AFEITADORA`, `MARCADORA/LAVADORA/BIN PICKING`, generic PLC, CNC) and applies `modificarTiemposMaquinas` when delay >= 1 min.

- `obtenerDesviacionMaquinaAuto(celula, num)`
  - Fallback: mirrors auto-cell deviation to another machine and refreshes machine `DesviacionPiezas` timestamp.

- `obtenerUltimoRegistro_PLC(...)`
  - Generic PLC deviation from DB history (type 3), shift since last stored timestamp.

- `obtenerUltimoRegistro_CNC(celula, num, rpt)`
  - CNC deviation from tag counter delta between stored/current values.

- `obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt)`
  - Auto-cell deviation using `piezasMaquinaTurno_Automatica`.

- `obtenerUltimoRegistro_PLC_v2(...)`
  - Variant for `BROCHADORA/AFEITADORA` using `HtaVidaActual`.

- `obtenerUltimoRegistro_PLC_v3(...)`
  - Variant for `MARCADORA/LAVADORA/BIN PICKING` using DB data type 2.

## `Tareas/Data/DesviacionTareas/code.py`

- `desviacionesTareas()`
  - Main task-level deviation automation loop.
  - Rule branches by task prefix: `Descarga`, `Verificación`, `CH`, `Cambio de carga` (BIN PICKING/CELULA), `Grafico`.
  - Executes either completion or schedule reprogramming.

- `tareasPorMaquina(celula, referencia, maquina)`
  - Reads active task list from `_Tareas_Resumen`.

- `accionesDescarga(celula, proxTarea)`
  - Uses lavadora saturation state and time-to-next-task.
  - Returns: `0` keep, `1` complete, `2` set +20 min, `3` immediate.

- `accionesVerificacion(tarea, num, referencia, celula, maquina)`
  - Queries QDAS latest measurement date and syncs machine `Verificaciones` dataset.
  - Returns `True` only when a newer measurement requires completing task.

- `accionesCH_PLC(celula, num)`
  - Remaining life for PLC tool from `[vidaTeorica, vidaUtil]`.

- `accionesCH_CNC_Torno_v0(...)` / `accionesCH_CNC_Torno(...)`
  - Torno-specific tool-life estimation; current version computes grouped tool-name life and chooses worst case.

- `accionesCH_CNC_Talladora(celula, num)`
  - Simple remaining life from first CNC tool pair.

- `accionesCambioBandejaCarga(celula, num)`
  - Uses saturation + `Pre` latch tag.
  - Returns: `0` keep, `1` half-time adjust, `2` complete.

- `accionesCambioBandejaDescarga(celula, num, referencia)`
  - Checks latest rack label vs stored rack tag; completes only on rack change.

## `Tareas/Data/fromExcelToDB/code.py`

- `excelToDataSet(...)`
  - Apache POI reader with column bound protection and formula/date handling.

- `excelToDataSet_Anterior(...)`
  - Legacy Excel parser version.

- `checkStructure(dataSet, tablaSecuencia, referencia, celula)`
  - Validates expected headers and DB table schema presence.

- `excelToDb(filepath, page)`
  - File-based load: parse sheet, extract `referencia/celula`, clear old `_Secuencia` rows, insert normalized rows.

- `multipleExcelToDb(filepath, pages)`
  - Calls `excelToDb` for each page.

- `deleteTable(table, reference, celula)`
  - Deletes rows for reference/cell on whitelisted tables.

- `inactivoTable(table, reference, celula)`
  - Marks rows inactive (`activo=0`) for reference/cell on whitelisted tables.

- `deleteTable_Secuencia()`
  - Truncation-like delete for whole `_Secuencia` table.

- `tareasTable(celula, referencia)`
  - Transforms `_Secuencia` rows into `_Tareas` rows (task label + occurrence generation).

- `insertarTareasEnTablaResumen(celula, referencia)`
  - Rebuilds active `_Tareas_Resumen` from `Teorico.obtenerTareas` output (inactivates old rows first).

- `multipleExcelToDb_fb(fileBytes, pages)`
  - Byte-array multi-sheet loader.

- `excelToDb_fb(fileBytes, page)`
  - Byte-array transactional insert into `_Secuencia` (commit/rollback protected).

## `Tareas/Data/GearFlow/code.py`

- `cambioHerramientas(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None)`
  - Computes narrow window around target date, maps cell to external id, calls SOAP filter, returns first `criterio`.

- `grafico(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None)`
  - Uses current shift window, calls SOAP filter, returns first `criterio`.

- `filtrar_racks(...)`
  - SOAP call (`ListaGraficosdelrackLaboratorio`), XML parse, optional filtering by date/type/ref/cell/tool-family, returns list of `{codigo_rack, criterio, fecha}`.

## `Tareas/Data/Independiente/code.py`

- `crearTareaTorno(celula, num)`
  - Computes combined max life for same-prefix tools on torno.

- `crearTareaLimpieza(celula)`
  - Programs a cleanup task based on candidate tasks (CH talladora/afeitadora, grafico) and minimum 4h since last cleanup.

- `crearTareaGrafico(celula)`
  - Creates `Grafico` task aligned with CH candidates or fallback at `now+2h`.

- `actualizarTareaGrafico(celula)`
  - Updates existing pending `Grafico` row to best in-turn CH candidate; fallback at `inicio_turno+2h`.

## `Sinoptico/Data/General/code.py`

Reference + state:
- `obtenerReferencia(celula)`
- `obtenerOEEStatus_v0(celula, referencia)`
- `obtenerOEEStatus(celula, referencia)`

Machine metadata + topology:
- `obtenerAuto(celula, num)`
- `obtenerPLC_CNC(celula, num)`
- `obtenerPosicion(celula, num)`
- `obtenerPosicionAuto(celula, num)`
- `obtenerTipoMaquina(celula, num)`
- `obtenerIDMaquina(celula, num)`
- `obtenerIDMaquinaOriginal(celula, num)`
- `obtenerNumeroMaquina(celula, maquina)`
- `obtenerConexion(celula, num)`

Live machine values:
- `obtenerDisponibilidad(celula, num)`
- `obtenerCiclo(celula, num)`
- `obtenerSaturacion(celula, num)`
- `obtenerAlarmas(celula, num)`

Counters and production:
- `obtenerCNCContador(celula, num)`
- `obtenerAutoContador(celula, referencia)`
- `elegirPLCContador(celula, num, idMaquina, referencia)`
- `obtenerPLCContador(celula, num, idMaquina)`
- `obtenerPLCContador_v2(celula, num, idMaquina)`

Tool data:
- `obtenerCNCHerramienta(celula, num)`
- `obtenerCNCHerramientaConNombre(celula, num)`
- `obtenerCNCHtaNombre(celula, num)`
- `obtenerAutoHerramienta(celula, num)`
- `obtenerAutoHerramientaConNombre(celula, num)`

## `Inicio/Data/GestionUsuarios/code.py`

- `obtenerDatos(numUsuario)`
  - Pads employee number to 8 digits, fetches identity from `Norm_TUsuarios`, role from admin DB (`TUsuarios` + `TRoles`), writes `Variables/Inicio/idUsuario`, returns `[nombre, usuario, mail, rol, idUsuario]`.

## `Administracion/Data/GestionUsuarios/code.py`

- `filtroCrear(valorFiltro)`
  - Search candidate users (up to 30 active from corporate users table), excludes already created GPilot users.

- `mostrarRoles()`
  - Returns all roles from `TRoles`.

- `mostrarUsuarios()`
  - Joins local GPilot users with corporate user info to return role/name/mail/id.

- `crearUsuarios(idUsuario, idRol, idCreador)`
  - Inserts user-role assignment with timestamp.

- `eliminarUsuarios(idUsuario)`
  - Deletes GPilot user mapping.

- `actualizarRolUsuario(idUsuario, idRol, idCreador)`
  - Updates role + editor + timestamp.

## `Administracion/Data/GestionTareas/code.py`

- `mostrarTareas()`
  - Builds admin task view by combining non-time tasks with machine base minutes (`Tiempo de m% ... 1/1`).

- `eliminarTarea(tarea, referencia, maquina, celula, elemento)`
  - Deletes specific row from `_Tareas` and refreshes `_Tareas_Resumen`.

- `eliminarTareaActualizarTag(tarea, maquina, celula, elemento)`
  - Removes element from dataset-tag row; deletes whole row if no elements remain.

- `editarOcurrenciaTareas(tarea, referencia, maquina, celula, elemento, ocurrencia)`
  - Updates occurrence/task label in `_Tareas` then refreshes summary.

- `editarOcurrenciaActualizarTag(...)`
  - Moves one element from old occurrence-group to new one in task dataset tag; merges with existing target group or creates recurring rows.

- `editarMinutosMaquina(referencia, maquina, celula, minutos)`
  - Updates machine minute baseline (`Tiempo de m% ... 1/1`) and refreshes summary.

---

## 3) Key dependencies and contracts

DB usage patterns:
- `constantes.Database_Tareas`: `_Secuencia`, `_Tareas`, `_Tareas_Resumen`, `_Completados`
- `constantes.Database_Tareas_2`: machine telemetry + racks (`CDatosMaquina`, `CMaquinas`, `CGF_RACKS_DATA_MARTS`)
- `constantes.Database_Sinoptico`: OEE production/rates (`COEEproduction`, `COEErate`)
- `constantes.Database_QDAS`: verification lookups
- `constantes.Database_Inicio` + `constantes.Database_Admin_Usuarios`: identity/roles

Tag contracts heavily assumed:
- Dataset columns in global task dataset: `tarea`, `cuando`, `celula`, `maquina`, `elemento`, `completado`
- Per-machine counter dataset columns: `fecha`, `tarea`, `ocurrencia`, `contador`, `elementos`
- Deviation datasets: `fecha`, `piezas`

---

## 4) Important observations (for future refactor)

- Many `_v0` functions remain active side-by-side with current versions.
- Shared dataset tags are read-modify-write without explicit lock control (possible race conditions under timers/concurrent calls).
- Several modules mix gateway-safe logic with UI-oriented calls (`system.gui.errorBox`), so script scope must be validated per execution context.
- Some admin functions call summary refresh without required args in current code (`insertarTareasEnTablaResumen()` appears called without parameters in some paths).

---

## 5) Practical entry points

Typical startup/refresh flow:
1. `Tareas.Secuencia.General.cargarEstandar(...)`
2. `Tareas.Secuencia.General.iniciarEstandar(celula)`
3. Periodic timers:
   - `Tareas.Data.Desviacion.desviacionesMaquina()`
   - `Tareas.Data.DesviacionTareas.desviacionesTareas()`
4. User/manual completions:
   - `Tareas.Secuencia.General.completarTarea(...)`
