## Tarea: Cambio de logica a maquina critica (G Pilot)

## Contexto
Actualmente G Pilot calcula y reprograma tareas usando tiempos y contadores por maquina.
Eso provoca que tareas con el mismo frecuencial (por ejemplo 1/100) queden separadas en el tiempo entre maquinas, aunque operativamente el operario las ejecuta en ronda.

La regla de negocio definida en reunion es unificar el comportamiento:
- todas las tareas dependientes de piezas deben avanzar con un unico contador,
- y ese contador es el de la celula automatica,
- multiplicando siempre por el tiempo de la maquina critica (MC) del estandar.

Archivo de referencia del caso: `R104587 1.xlsx`.

## Problema actual
1. Se usan tiempos de cada maquina (`min`/`min_std`) para calcular cuando tocaria cada tarea.
2. Se usan contadores por maquina para avance y recalcado.
3. Resultado: tareas equivalentes por frecuencial no quedan alineadas.
4. Se introdujo una linea artificial tipo "CELULA / pieza terminada / tiempo de maquina" para cubrir tareas de grafico.

## Regla nueva obligatoria
1. El contador que marca el avance de tareas es el de la celula automatica.
2. El tiempo de calculo para todas las tareas dependientes de piezas es el de la maquina critica (MC).
3. Para una misma celula-referencia, ese tiempo debe quedar igual en todas las lineas de tarea.
4. Tareas con mismo frecuencial deben caer en el mismo bloque temporal (alineadas).
5. Cambio de herramienta:
- no usa contador de piezas normal,
- usa logica de vida util,
- pero el tiempo final sigue multiplicando por tiempo MC.
6. Eliminar dependencia de lineas "inventadas" (ejemplo: tiempo de maquina de CELULA/pieza terminada).

## Fuente de contador
- En celula automatica, el contador robusto viene de `COEEproduction` (DB G Pilot), no de un tag por maquina.
- En codigo ya existe soporte de consulta para automatica en:
- `Tareas/Data/TagsMaquina/code.py` -> `piezasMaquinaTurno_Automatica(celula, referencia)`.

## Impacto tecnico esperado

### 1) Carga e inicializacion de estandar
- `Tareas/Secuencia/General/code.py`
- `cargarEstandar(...)`
- `iniciarEstandar(...)`

Objetivo:
- construir dataset final con criterio de tiempo MC unico para la celula,
- mantener intactas otras celulas en el tag global,
- recalcular tareas y grafico con la nueva regla.

### 2) Calculo teorico de tiempos
- `Tareas/Data/Teorico/code.py`
- `obtenerTiemposMaquina(celula, referencia)`
- `generarDatasetTiempos(datasetMinutos, datasetTareas)`

Objetivo:
- dejar de emparejar tarea con tiempo por maquina local,
- usar tiempo unico de MC para tareas dependientes de piezas,
- mantener exclusion de filas no validas (medicion/varios/grafico segun criterio final).

### 3) Reprogramacion al completar tarea
- `Tareas/Secuencia/General/code.py`
- `completarTarea(...)`
- `Tareas/Data/General/code.py`
- `obtenerRitmoProd(...)`
- `programarTiemposTareas(...)`

Objetivo:
- recalcado con tiempo MC,
- avance por contador de celula (no por contador local de la maquina),
- mantener trazabilidad de completado en BD.

### 4) Contadores
- `Tareas/Data/TagsMaquina/code.py`
- `completarTarea(celula, num, nombreTarea)` hoy opera por `Maq_{num}/ContadorTareas`.

Objetivo:
- redefinir/encaminar el avance para que dependa del contador de celula automatica segun regla negocio,
- conservar comportamiento esperado de retorno (0, valor, -1, -2) o redefinirlo explicitamente.

## Criterios de aceptacion
1. Todas las tareas dependientes de piezas usan el mismo tiempo MC en una celula.
2. Tareas con mismo frecuencial aparecen alineadas temporalmente entre maquinas.
3. El avance depende del contador de celula automatica.
4. Cambio herramienta conserva su logica de vida util, pero con tiempo MC.
5. No hace falta linea artificial de tiempo para CELULA/pieza terminada.
6. `iniciarEstandar` sigue preservando filas de otras celulas en el tag dataset.
7. No se rompe insercion en tablas:
- `*_Secuencia`
- `*_Tareas`
- `*_Tareas_Resumen`
8. Se mantienen logs de error actuales.

## Pruebas funcionales minimas
1. Cargar `R104587 1.xlsx`.
2. Identificar MC en el estandar.
3. Verificar que columna `min` queda homogenea por celula para tareas afectadas.
4. Validar dos tareas con mismo frecuencial en maquinas distintas: misma hora objetivo.
5. Completar tarea y verificar recalcado:
- usa contador de celula,
- usa tiempo MC.
6. Probar cambio de herramienta con vida util.
7. Revisar tarea de grafico para que no dependa de fila artificial.

## Decisiones de negocio ya cerradas
1. Mantener campo `min` por tarea, aunque repetido, por flexibilidad futura.
2. El criterio operativo es de celula, no de maquina individual.

## Dudas a cerrar antes de cerrar codigo
1. Regla exacta para obtener MC desde el excel cuando falte o venga inconsistente.
2. Lista exacta de tareas incluidas/excluidas del modelo "depende de piezas".
3. Si algun flujo manual debe seguir usando contador por maquina (caso excepcional).

## Resultado esperado para operacion
El planificador debe mostrar tareas sincronizadas por ronda operaria:
- mismo frecuencial -> mismo bloque temporal,
- menor dispersion entre maquinas,
- comportamiento estable incluso si falla un contador local de maquina.
