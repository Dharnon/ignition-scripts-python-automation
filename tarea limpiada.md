# Tarea limpiada (version final)

## Objetivo
Cambiar el modelo de planificacion de G Pilot para que todas las tareas dependientes de piezas se calculen con:
1. Un unico contador: contador de la celula automatica.
2. Un unico tiempo: tiempo de la maquina critica (MC) del estandar.

## Regla funcional final
1. Si la celula avanza 1 pieza, avanzan todas las tareas dependientes de piezas.
2. El tiempo de recalcado no depende de cada maquina, depende de MC.
3. Tareas con igual frecuencial deben quedar alineadas en el tiempo.
4. Cambio de herramienta es excepcion en contador (vida util), pero no en tiempo: sigue usando tiempo MC.
5. No debe ser necesaria una fila artificial tipo "CELULA / tiempo de maquina / pieza terminada".

## Alcance de implementacion
1. Carga de estandar y refresco de dataset:
   - `Tareas/Secuencia/General/code.py`
   - funciones: `cargarEstandar`, `iniciarEstandar`, `completarTarea`.
2. Calculo teorico de tareas:
   - `Tareas/Data/Teorico/code.py`
   - funciones: `obtenerTiemposMaquina`, `generarDatasetTiempos`.
3. Reprogramacion y ritmo:
   - `Tareas/Data/General/code.py`
   - funciones: `obtenerRitmoProd`, `programarTiemposTareas`.
4. Contador de referencia de celula automatica:
   - `Tareas/Data/TagsMaquina/code.py`
   - funcion base existente: `piezasMaquinaTurno_Automatica`.

## Criterios de aceptacion
1. Para una celula-referencia, `min` queda unificado para tareas dependientes de piezas (valor de MC).
2. Tareas de mismo frecuencial en distintas maquinas aparecen a la misma hora objetivo.
3. El avance ya no depende del contador local por maquina en automatica.
4. Cambios de herramienta se siguen programando con su logica de vida util.
5. `iniciarEstandar` mantiene datos de otras celulas sin romper el dataset global.
6. Inserciones y actualizaciones en BD siguen funcionando (`_Secuencia`, `_Tareas`, `_Tareas_Resumen`, `_Completados`).

## Plan de pruebas (R104587 1.xlsx)
1. Cargar estandar desde Excel.
2. Confirmar cual es MC en el estandar.
3. Verificar tareas 1/100 en varias maquinas: misma franja temporal.
4. Verificar tareas 1/200 en varias maquinas: misma franja temporal.
5. Completar una tarea y validar recalcado con contador de celula + tiempo MC.
6. Probar un cambio de herramienta y validar comportamiento de vida util.
7. Confirmar que ya no depende de fila artificial de tiempo de CELULA.

## Riesgos y puntos a cerrar
1. Definir fallback cuando MC no venga bien informado en el excel.
2. Cerrar listado exacto de tareas que son "dependientes de piezas".
3. Revisar si algun flujo manual debe conservar temporalmente el contador local.

## Resultado operativo esperado
1. Menos dispersion de tareas en planificador.
2. Mas coherencia con el trabajo real del operario (rondas por frecuencial).
3. Menor dependencia de contadores individuales de maquina.
