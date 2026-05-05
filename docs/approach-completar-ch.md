# Approach para completar CH no torno

## Objetivo

Hacer que las tareas de cambio de herramienta de TALLADORA y AFEITADORA no solo recalculen su programación, sino que también lleguen al mismo punto de completado en base de datos que el resto de tareas cuando la condición de negocio se cumpla.

## Situación actual

El flujo actual de `Tareas.Data.DesviacionTareas.desviacionesTareas()` para CH no torno hace esto:

1. Calcula `vidaTotal` con la lógica correspondiente.
2. Llama a `Tareas.Data.GearFlow.cambioHerramientas(...)`.
3. Si el resultado es `OK`, llama a `Tareas.Secuencia.General.completarTarea(...)`.
4. Si no es `OK`, congela la tarea con `programarTiemposTareas(..., 0)`.

Eso significa que, en la práctica, muchas veces la tarea se queda en recalcular sin pasar por el cierre real en dataset y base de datos.

## Idea de solución

Separar dos decisiones que ahora están mezcladas:

- Decisión de planificación: recalcular, congelar o dejar la tarea como está.
- Decisión de cierre: marcar la tarea como completada y persistir el cierre en BD.

La segunda decisión debería ejecutarse con la misma estructura que el resto de tareas cuando la condición de negocio indique que la tarea ya se resolvió.

## Enfoque propuesto

### 1. Definir una condición única de completado

Para CH no torno, la tarea debería completarse cuando ocurra alguna de estas condiciones de negocio:

- `GearFlow.cambioHerramientas(...) == 'OK'`.
- O bien, una validación equivalente que represente que la tarea ya quedó resuelta y no necesita seguir pendiente.

La clave es que el cierre no dependa solo de recalcular tiempos.

### 2. Reusar siempre el mismo cierre común

Cuando la condición se cumpla, seguir llamando a:

- `Tareas.Secuencia.General.completarTarea(...)`

Porque esa función ya hace el flujo completo:

- actualiza el dataset en tags,
- reestructura tiempos,
- escribe el registro en base de datos.

### 3. Añadir fallback de validación en GearFlow

Restaurar la lógica tipo:

- probar `CONTROL`,
- si no hay `OK`, probar `HERRAMIENTA`.

Esto reduce falsos negativos y evita que una tarea válida se quede congelada por una sola consulta insuficiente.

### 4. Separar logging de planificación y cierre

Conviene loguear dos cosas distintas:

- `CH en espera` cuando solo se recalcula o congela.
- `CH completada` cuando se llama al cierre común.

Así se distingue rápido si el problema está en la detección o en el insert.

### 5. Validar que el resumen exista antes de insertar

`completarTareaBD(...)` depende de que exista una fila activa en `G_Pilot_Tareas_Resumen` con coincidencia exacta de:

- `tarea`
- `celula`
- `referencia`
- `maquina`

Si no existe, el flujo debería registrar el motivo explícitamente para no confundirlo con un fallo de recalculo.

## Cambios concretos que haría

- En `Tareas.Data.DesviacionTareas.desviacionesTareas()`:
  - mantener el cálculo de `vidaTotal`,
  - reintroducir la prueba `CONTROL -> HERRAMIENTA` para CH no torno,
  - completar la tarea cuando cualquiera de las dos devuelva `OK`.

- En `Tareas.Data.General.completarTareaBD(...)`:
  - añadir validación de resultado vacío antes de acceder a `data[0][0]`,
  - loguear claramente si no se encontró coincidencia en `Tareas_Resumen`.

- Opcionalmente, en `GearFlow`:
  - normalizar `herramienta` y `tipoSolicitud` antes del filtro,
  - dejar trazas claras del criterio usado y del resultado.

## Riesgos a revisar

- Si el nombre de la tarea no coincide exactamente con el resumen activo, el insert seguirá sin producirse.
- Si el flujo de CH no torno depende de una condición externa adicional, hay que respetarla antes de llamar a `completarTarea(...)`.
- Si se completa la tarea demasiado pronto, puede romper la cadencia de recálculo para tareas repetitivas.

## Resultado esperado

Cuando la tarea de CH no torno esté resuelta, el flujo debería terminar igual que el resto de tareas:

1. cerrar en dataset,
2. reprogramar lo que corresponda,
3. persistir el completado en BD.
