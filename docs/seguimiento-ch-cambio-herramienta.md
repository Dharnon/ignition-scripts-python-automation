# Seguimiento de cambio de herramienta

## Contexto

Se investigó por qué las tareas de cambio de herramienta no turno no se guardan como completadas en base de datos.

## Hallazgo principal

El guardado en base de datos no falla en la función de inserción, sino antes: la rama de `TALLADORA` y `AFEITADORA` solo completa la tarea si `GearFlow.cambioHerramientas(...)` devuelve `OK`.

Si esa llamada devuelve cualquier otro valor, la tarea se queda congelada en el dataset y no llega a ejecutar `Tareas.Secuencia.General.completarTarea(...)`, que es la que dispara el insert en BD.

## Diferencia con el flujo legado

En el flujo antiguo se probaban dos consultas para el cambio de gráfico/laboratorio:

- primero `CONTROL`
- si no había resultado, luego `HERRAMIENTA`

En el código actual para CH de no torno solo se hace una comprobación con `HERRAMIENTA`.

## Puntos clave del código

- [Tareas/Data/DesviacionTareas/code.py](../Tareas/Data/DesviacionTareas/code.py)
- [Tareas/Data/General/code.py](../Tareas/Data/General/code.py)
- [Tareas/Data/GearFlow/code.py](../Tareas/Data/GearFlow/code.py)
- [antiguo/script-python/Tareas/Data/DesviacionTareas/code.py](../antiguo/script-python/Tareas/Data/DesviacionTareas/code.py)

## Riesgo adicional en BD

Aunque la tarea llegue a completarse, `completarTareaBD(...)` busca un registro activo exacto en `G_Pilot_Tareas_Resumen` por:

- `tarea`
- `celula`
- `referencia`
- `maquina`

Si alguno de esos campos no coincide exactamente, no se inserta el completado.

## Próximo cambio recomendado

Restaurar la lógica de fallback para CH no torno:

1. probar `CONTROL`
2. si no devuelve `OK`, probar `HERRAMIENTA`
3. solo completar si alguna de las dos devuelve `OK`

Opcionalmente, añadir logging cuando `completarTareaBD(...)` no encuentre fila activa en el resumen.
