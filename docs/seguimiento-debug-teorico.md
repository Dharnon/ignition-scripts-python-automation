# Seguimiento debug: Dataset Tareas_Celula142

## Objetivo actual
Entender por qué el dataset visual no incluye tareas de `CELULA` y `BIN PICKING` aunque sí existen en la base de datos.

## Estado confirmado
- La importación del estándar sí llena la BD.
- `MC` ya queda resuelto desde la fila `tipo = 'MC'`.
- `VARIOS` se excluye.
- El problema ya no parece estar en la BD ni en la pantalla de administración.
- El fallo está en la generación del dataset runtime.

## Hallazgo clave
En la tabla `_Tareas` la columna base de frecuencia es `ocurrenciaStd`.
La columna `ocurrencia` puede venir vacía o usarse como override runtime.

## Síntoma visto en consola
- `datasetMinutos` sí devuelve filas.
- `datasetTareas` sí devuelve filas.
- Pero aparece mucho `SKIP ocurrencia 0`.

Eso indica que alguna parte del generador estaba leyendo solo `ocurrencia` y no `ocurrenciaStd`.

## Cambio aplicado
Se ha empezado a corregir el fallback para que el runtime use:
1. `ocurrencia`
2. si está vacía, `ocurrenciaStd`
3. si ambas fallan, `0`

Archivos tocados:
- `Tareas/Data/Teorico/code.py`
- `Tareas/iniciarEstandar.py`

## Hipótesis de trabajo
Las tareas se estaban saltando porque el generador interpretaba la frecuencia como cero cuando realmente estaba en `ocurrenciaStd`.

## Pendiente de validar
- Reejecutar la consola y comprobar que ya no salen `SKIP ocurrencia 0` para tareas válidas.
- Verificar que `CELULA` y `BIN PICKING` llegan a `[G-PILOT_TAGS]Dataset/Tareas_Celula142`.
- Confirmar si la selección final de minutos debe seguir usando `min` o si algún flujo todavía depende de `min_std`.

## Regla práctica para seguir investigando
Si una tarea existe en BD pero no aparece en el dataset visual:
- revisar primero `ocurrenciaStd`
- revisar luego el cruce con `datasetMinutos`
- revisar al final si hay algún filtro por máquina/célula

## Resumen corto
La BD parece correcta. El problema estaba en la capa de planificación, y el campo importante de frecuencia en `_Tareas` es `ocurrenciaStd`.

## Último hallazgo
- La consulta sobre `G_PILOT_Tareas_Resumen` sin filtrar `activo = 1` devuelve muchas filas históricas/inactivas.
- En `142A / R120638 / TORNO` se ven varias filas `CH` y `Verificación` repetidas con `activo = false`.
- La fila realmente vigente es la que sale con `activo = true` y `ocurrencia` ya resuelta.
- Esto confirma que parte de la “duplicación” viene del histórico activo/inactivo, no de que falten datos.

## Hipótesis actual sobre `CELULA` y `BIN PICKING`
- La BD sí tiene esas filas activas.
- El runtime dataset se construye en `Tareas/Data/Teorico/code.py` cruzando `datasetTareas` con `datasetMinutos` por `celula + maquina`.
- Si no aparecen, probablemente el cruce exacto falla o alguna capa posterior pisa la salida.

## Cómo comprobarlo rápido
1. Comparar los valores exactos de `maquina` en `datasetTareas` y `datasetMinutos`.
2. Loggear en el bucle de `generarDatasetTiempos()` cuando no hay match de `celula + maquina`.
3. Verificar si el dataset final que se escribe en `[G-PILOT_TAGS]Dataset/Tareas_Celula142` contiene esas filas después del cruce.

## Query útil para aislar el problema
```sql
SELECT referencia, celula, maquina, tarea, ocurrencia, elementos, activo
FROM G_PILOT_Tareas_Resumen
WHERE referencia = 'R120638'
	AND celula = '142A'
	AND activo = 1
ORDER BY maquina, tarea
```

## Resumen corto del estado
- BD: correcta.
- `_Tareas_Resumen`: correcta y activa.
- Sospecha: match exacto o pisado en `generarDatasetTiempos()` / `syncTareas()`.