# GPILOT2 - Estructura de Tablas

Base de datos confirmada: `GPILOT2`

## G_Pilot_Secuencia
- `id` (int, identity)
- `ac` (int)
- `celula` (nvarchar)
- `descripcion` (nvarchar)
- `elemento` (nvarchar)
- `maquina` (nvarchar)
- `min_std` (float)
- `min_std_ciclo` (float)
- `min_std_ciclo_pf` (float)
- `num` (int)
- `ocurrencia` (float)
- `pf` (float)
- `prioridad` (int)
- `referencia` (nvarchar)
- `tipo` (nvarchar)

## G_Pilot_Tareas
- `id` (int, identity)
- `celula` (nvarchar)
- `elemento` (nvarchar)
- `maquina` (nvarchar)
- `min` (float)
- `min_std` (float)
- `ocurrencia` (float)
- `ocurrenciaStd` (float)
- `prioridad` (int)
- `referencia` (nvarchar)
- `tarea` (nvarchar)
- `turno` (int)

## G_Pilot_Tareas_Resumen
- `id` (int, identity)
- `activo` (bit)
- `celula` (nvarchar)
- `elementos` (nvarchar)
- `maquina` (nvarchar)
- `ocurrencia` (float)
- `referencia` (nvarchar)
- `tarea` (nvarchar)

## Nota de uso
Si vas a limpiar una referencia/celula especifica, recuerda hacerlo en este orden para evitar inconsistencias lógicas:
1. `G_Pilot_Tareas_Resumen`
2. `G_Pilot_Tareas`
3. `G_Pilot_Secuencia`
