MC + automatic cell counter model
=================================

Fecha: 2026-03-19
Rama: `codex/mc-cell-counter-refactor`

1. Ubicación de la “verdad” de MC
---------------------------------

- **Origen de verdad (excel → DB)**
  - Tabla: `<LINEA>_Secuencia` en `Database_Tareas`.
  - Para cada pareja `(celula, referencia)` existe una única fila con `tipo = 'MC'`.
  - El valor de `MC` es `min_std` de esa fila.
  - Ejemplo `R104587-D`:
    - `REFERENCIA = R104587`
    - `CELULA = 142D`
    - Fila `tipo='MC'` (máquina crítica `TALLADORA`) con `min_std = 3.8`.

- **Normalización en la tabla de trabajo**
  - Función: `Tareas.Data.fromExcelToDB.tareasTable(celula, referencia)`.
  - Tabla destino: `<LINEA>_Tareas` en `Database_Tareas`.
  - Al generar las filas recurrentes:
    - `min_std` conserva el minuto original importado desde el estándar.
    - `min` se rellena con el minuto MC resuelto por:
      - `Tareas.Data.fromExcelToDB.obtenerMinutoMC(celula, referencia)`.
  - Resultado:
    - Todas las tareas dependientes de piezas de una `(celula, referencia)` comparten el mismo `min` (MC).
    - Los consumidores que usan `ISNULL(min, min_std)` ven automáticamente el tiempo crítico.

2. Dónde se consume MC en planificación y runtime
-------------------------------------------------

- **Planificación teórica**
  - Módulo: `Tareas/Data/Teorico/code.py`.
  - `obtenerTiemposMaquina(celula, referencia)`:
    - Lee de `<LINEA>_Tareas` el campo:
      - `minutos = CASE WHEN min IS NULL THEN min_std ELSE min END`.
    - Con `min` normalizado, `minutos` = `MC` para toda la célula.
  - `generarDatasetTiempos(datasetMinutos, datasetTareas)`:
    - Calcula el intervalo como `minutos * ocurrencia`.
    - Como `minutos` ya es MC, dos tareas con el mismo frecuencial quedan alineadas entre máquinas en `Dataset/Tareas_Celula...`.

- **Ritmo de producción en runtime**
  - Módulo: `Tareas/Data/General/code.py`.
  - `obtenerRitmoProd(celula, referencia, maquina)`:
    - Consulta `<LINEA>_Tareas` filtrando `tarea LIKE 'Tiempo de m%'`.
    - Devuelve `ISNULL(ocurrencia, ocurrenciaStd) * ISNULL(min, min_std)`.
    - Como `min` está normalizado a MC, el `rpt` efectivo ya está calculado con tiempo crítico.
  - `programarTiemposTareas(...)`:
    - Usa `ocurrencia * rpt` para reprogramar fechas en `Dataset/Tareas_Celula...`.
    - Dado que `rpt` proviene de MC, la reprogramación preserva la alineación por frecuencial.

3. Contador efectivo: de máquina local a contador de célula
----------------------------------------------------------

- **Antes**
  - El avance de tareas recurrentes dependía del dataset:
    - Tag: `Datos_Celula/Celula{X}/Maq_{N}/ContadorTareas`.
    - Columna `contador` almacenaba un acumulado local por máquina.
  - `Tareas.Data.TagsMaquina.completarTarea(celula, num, nombreTarea)`:
    - Restaba `ocurrencia` al `contador` local.
    - Devolvía:
      - `0`, valor intermedio, `-1` o `-2` según el resultado.

- **Ahora (modelo MC + contador de célula)**
  - Fuente de piezas robusta:
    - `Tareas.Data.TagsMaquina.piezasMaquinaTurno_Automatica(celula, referencia)`.
    - Lee producción real desde `COEEproduction` para la célula automática.
  - Nueva semántica de `ContadorTareas.contador`:
    - Para tareas dependientes de piezas (todas excepto `CH`):
      - `contador` se interpreta como **baseline** del contador de célula en el momento en que empezó el ciclo actual.
    - Para tareas `CH`:
      - Se mantiene la semántica anterior basada en contadores/vida útil específicos de máquina.
  - Nuevo helper:
    - `Tareas.Data.TagsMaquina.usaContadorCelula(nombreTarea)`:
      - `True` para tareas piece-dependent.
      - `False` para tareas de cambio de herramienta (`CH...`).
  - Nueva firma:
    - `Tareas.Data.TagsMaquina.completarTarea(celula, referencia, num, nombreTarea)`.
  - Lógica para tareas piece-dependent:
    - Lee el dataset `ContadorTareas` y obtiene:
      - `ocurrencia` (piezas por ciclo).
      - `contador` (baseline anterior).
    - Obtiene `contadorCelula = piezasMaquinaTurno_Automatica(celula, referencia)`.
    - Calcula `delta = contadorCelula - contador`.
      - Si `delta < 0`: se considera reinicio/retroceso → se normaliza a 0.
      - Si `delta < ocurrencia`:
        - Devuelve `delta` (o `0` si no hay avance); la tarea se considera completada “antes de tiempo”.
      - Si `delta >= ocurrencia`:
        - Devuelve `-1` → se ha sobrepasado el ciclo, se fuerza reprogramación tipo “YA”.
    - Actualiza `contador` en el dataset al valor actual de `contadorCelula` como nuevo baseline.
  - Lógica para tareas `CH`:
    - Se conserva la operación anterior:
      - `contador = contador - ocurrencia` en el dataset local.
      - mismos retornos (`0`, valor intermedio, `-1`, `-2`).

4. Uso del contador efectivo en la reprogramación
-------------------------------------------------

- Módulo: `Tareas/Secuencia/General/code.py`.
- `completarTarea(celula, referencia, tipoMaq, tarea, num, manual)` ahora:
  - Obtiene `rpt` desde `Tareas.Data.General.obtenerRitmoProd(...)` (ya basado en MC).
  - Obtiene `ocurrencia` desde `_Tareas_Resumen`.
  - Llama a:
    - `contador = Tareas.Data.TagsMaquina.completarTarea(celula, referencia, num, tarea)`.
  - Interpreta el resultado exactamente igual que antes:
    - `0`      → reprograma desde ahora (`desfase = 0`).
    - `>0`     → reprograma con `desfase = (ocurrencia - contador) * rpt`.
    - `-1`     → reprograma “YA” (`desfase = -1`).
    - `-2`     → error, reprograma por defecto (`desfase = 0`).
  - Llama a:
    - `Tareas.Data.General.programarTiemposTareas(...)` con el `desfase` calculado.
  - Completa la fila en el dataset global:
    - `Tareas.Data.General.completarTarea(...)`.
  - Deja traza en BD:
    - `Tareas.Data.General.completarTareaBD(...)`.

5. Efectos en tareas especiales (Grafico y bandejas)
----------------------------------------------------

- **Grafico**
  - La tarea `Grafico` ya no depende de una fila artificial tipo:
    - `"CELULA / pieza terminada / tiempo de máquina"`.
  - Se programa y actualiza en función de:
    - Las tareas de `CH` (Talladora/Afeitadora), que ahora están alineadas en tiempo por MC.
    - El turno actual (inicio/fin de turno).
  - Módulo: `Tareas/Data/Independiente/code.py`:
    - `crearTareaGrafico(celula)`:
      - busca candidatos `CH` en `Dataset/Tareas_Celula...` y programa `Grafico` en el mismo `cuando`.
      - si no hay candidatos válidos, programa a 2 horas del inicio de turno.
    - `actualizarTareaGrafico(celula)`:
      - vuelve a alinear la tarea `Grafico` con la mejor tarea `CH` del turno, o con `inicio_turno + 2h`.
  - Como todas las tareas recurrentes comparten MC y usan el contador de célula, las ventanas de `CH` que usan `Grafico` como ancla están ya en el mismo bloque temporal que el resto de tareas con igual frecuencial.

- **Cambio de bandeja de carga/descarga**
  - `Cambio de carga` (bin picking, máquina `BIN PICKING`):
    - `accionesCambioBandejaCarga(...)` sigue devolviendo:
      - `0` (sin cambios), `1` (mitad de piezas), `2` (completar).
    - Cuando devuelve `2`, la lógica principal completa la tarea a través de:
      - `Tareas.Secuencia.General.completarTarea(...)`.
    - Eso hace que el recálculo del siguiente ciclo use el mismo modelo MC + contador de célula.
  - `Cambio de carga` (bandeja de descarga, máquina `CELULA`):
    - `accionesCambioBandejaDescarga(...)` decide si el rack ha cambiado y, en ese caso, completa la tarea.
    - La reprogramación posterior también usa MC + contador de célula a través del flujo estándar de `completarTarea`.

6. Comportamiento de edición en administración
---------------------------------------------

- Módulo: `Administracion/Data/GestionTareas/code.py`.
- `editarMinutosMaquina(referencia, maquina, celula, minutos)` ahora:
  - **Actualiza el origen de verdad de MC**:
    - En `<LINEA>_Secuencia`:
      - `UPDATE ... SET min_std = ? WHERE referencia = ? AND celula = ? AND tipo = 'MC'`.
  - **Propaga el nuevo MC** a todas las tareas recurrentes de esa célula/referencia:
    - En `<LINEA>_Tareas`:
      - `UPDATE ... SET min = ? WHERE referencia = ? AND celula = ?`.
  - **Refresca el resumen activo** solo para esa `(celula, referencia)`:
    - Llamada:
      - `Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)`.
  - Resultado:
    - Cambiar el tiempo de máquina crítica desde administración actualiza:
      - MC en `_Secuencia` (fuente).
      - Minutos normalizados en `_Tareas.min`.
      - La tabla `_Tareas_Resumen` y, tras reiniciar el estándar, el dataset visible.

7. Resumen operativo
--------------------

- **Tiempo**:
  - MC vive en:
    - `min_std` de la fila `tipo='MC'` en `<LINEA>_Secuencia`.
    - `min` de todas las filas recurrentes correspondientes en `<LINEA>_Tareas`.
  - Es consumido por:
    - `Teorico.obtenerTiemposMaquina` y `generarDatasetTiempos`.
    - `General.obtenerRitmoProd` y `programarTiemposTareas`.
    - Admin (`editarMinutosMaquina`) para actualizaciones centralizadas.

- **Contador**:
  - El contador efectivo para tareas piece-dependent:
    - Viene de `piezasMaquinaTurno_Automatica(celula, referencia)` (OEE/COEEproduction).
    - Usa `ContadorTareas.contador` como baseline (último valor conocido).
  - El contador para `CH`:
    - Sigue viniendo de la lógica de vida de herramienta específica de máquina (tags y QDAS/vida útil).

En conjunto, la planificación y el runtime quedan anclados a:
1) un único tiempo de máquina crítica (MC) por `(celula, referencia)`, y  
2) un único contador de piezas de célula automática, con `CH` como única excepción de contador.

