/*
Validacion post-fix fallback MC (DB only)

Que comprueba:
1) Si cada tarea recurrente (no Tiempo de m / no Carga / no Traslados)
   tiene minutos efectivos para programarse.
2) Minuto efectivo = tiempo exacto por maquina, o fallback MC si maquina es
   CELULA/BIN PICKING y no hay tiempo exacto.
3) Detecta tareas que seguirian sin programarse.

Uso rapido:
- Cambia @Referencia y @Celula para filtrar un caso (ej. R120638 y 142A).
- Deja NULL para revisar todo.
*/

DECLARE @Referencia VARCHAR(100) = 'R120638';
DECLARE @Celula     VARCHAR(20)  = '142A';

WITH base_tareas AS (
    SELECT
        t.referencia,
        t.celula,
        t.maquina,
        t.tarea,
        COALESCE(t.ocurrencia, t.ocurrenciaStd) AS ocurrencia_final,
        t.elemento
    FROM dbo.G_Pilot_Tareas t
    WHERE t.tarea NOT LIKE 'Tiempo de m%'
      AND t.tarea NOT LIKE 'Carga%'
      AND t.tarea NOT LIKE 'Traslados%'
      AND (@Referencia IS NULL OR t.referencia = @Referencia)
      AND (@Celula IS NULL OR t.celula = @Celula)
),
resumen_tareas AS (
    SELECT
        b.referencia,
        b.celula,
        b.maquina,
        b.tarea,
        b.ocurrencia_final,
        STRING_AGG(CONVERT(VARCHAR(MAX), b.elemento), ' | ') AS elementos
    FROM base_tareas b
    GROUP BY
        b.referencia,
        b.celula,
        b.maquina,
        b.tarea,
        b.ocurrencia_final
),
tiempos_maquina AS (
    SELECT
        t.referencia,
        t.celula,
        t.maquina,
        COALESCE(t.min, t.min_std) AS minutos_maquina
    FROM dbo.G_Pilot_Tareas t
    WHERE t.tarea LIKE 'Tiempo de m%'
      AND t.maquina <> 'VARIOS'
      AND t.maquina <> 'GRAFICO'
      AND t.elemento NOT LIKE 'MEDICI%'
      AND (@Referencia IS NULL OR t.referencia = @Referencia)
      AND (@Celula IS NULL OR t.celula = @Celula)
),
mc_por_par AS (
    SELECT
        s.referencia,
        s.celula,
        MIN(s.min_std) AS minuto_mc,
        COUNT(*) AS filas_mc
    FROM dbo.G_Pilot_Secuencia s
    WHERE s.tipo = 'MC'
      AND (@Referencia IS NULL OR s.referencia = @Referencia)
      AND (@Celula IS NULL OR s.celula = @Celula)
    GROUP BY
        s.referencia,
        s.celula
),
validacion AS (
    SELECT
        r.referencia,
        r.celula,
        r.maquina,
        r.tarea,
        r.ocurrencia_final,
        r.elementos,
        tm.minutos_maquina,
        mc.minuto_mc,
        mc.filas_mc,
        CASE
            WHEN tm.minutos_maquina IS NOT NULL THEN tm.minutos_maquina
            WHEN UPPER(LTRIM(RTRIM(r.maquina))) IN ('CELULA', 'BIN PICKING') THEN mc.minuto_mc
            ELSE NULL
        END AS minutos_efectivos,
        CASE
            WHEN tm.minutos_maquina IS NOT NULL THEN 'EXACTO_MAQUINA'
            WHEN UPPER(LTRIM(RTRIM(r.maquina))) IN ('CELULA', 'BIN PICKING') AND mc.minuto_mc IS NOT NULL THEN 'FALLBACK_MC'
            WHEN UPPER(LTRIM(RTRIM(r.maquina))) IN ('CELULA', 'BIN PICKING') AND mc.minuto_mc IS NULL THEN 'SIN_MC'
            ELSE 'SIN_TIEMPO_MAQUINA'
        END AS fuente_minutos
    FROM resumen_tareas r
    LEFT JOIN tiempos_maquina tm
        ON tm.referencia = r.referencia
       AND tm.celula = r.celula
       AND UPPER(LTRIM(RTRIM(tm.maquina))) = UPPER(LTRIM(RTRIM(r.maquina)))
    LEFT JOIN mc_por_par mc
        ON mc.referencia = r.referencia
       AND mc.celula = r.celula
)

-- 1) Resumen por referencia/celula: principal KPI de salud
SELECT
    v.referencia,
    v.celula,
    COUNT(*) AS tareas_totales,
    SUM(CASE WHEN v.ocurrencia_final > 0 THEN 1 ELSE 0 END) AS tareas_con_ocurrencia,
    SUM(CASE WHEN v.ocurrencia_final > 0 AND v.minutos_efectivos IS NOT NULL AND v.minutos_efectivos > 0 THEN 1 ELSE 0 END) AS tareas_programables,
    SUM(CASE WHEN v.ocurrencia_final > 0 AND (v.minutos_efectivos IS NULL OR v.minutos_efectivos <= 0) THEN 1 ELSE 0 END) AS tareas_no_programables
FROM validacion v
GROUP BY
    v.referencia,
    v.celula
ORDER BY
    v.referencia,
    v.celula;

-- 2) Detalle de las que NO pintarian (si sale vacio, bien)
SELECT
    v.referencia,
    v.celula,
    v.maquina,
    v.tarea,
    v.ocurrencia_final,
    v.fuente_minutos,
    v.minutos_maquina,
    v.minuto_mc,
    v.filas_mc
FROM validacion v
WHERE v.ocurrencia_final > 0
  AND (v.minutos_efectivos IS NULL OR v.minutos_efectivos <= 0)
ORDER BY
    v.referencia,
    v.celula,
    v.maquina,
    v.tarea;

-- 3) Distribucion de fuente de minutos (sirve para verificar que el fallback se esta usando)
SELECT
    v.referencia,
    v.celula,
    v.fuente_minutos,
    COUNT(*) AS tareas
FROM validacion v
WHERE v.ocurrencia_final > 0
GROUP BY
    v.referencia,
    v.celula,
    v.fuente_minutos
ORDER BY
    v.referencia,
    v.celula,
    v.fuente_minutos;

-- 4) Control de integridad MC (deberia haber 1 fila MC por referencia/celula)
SELECT
    s.referencia,
    s.celula,
    COUNT(*) AS filas_mc,
    MIN(s.min_std) AS min_mc,
    MAX(s.min_std) AS max_mc
FROM dbo.G_Pilot_Secuencia s
WHERE s.tipo = 'MC'
  AND (@Referencia IS NULL OR s.referencia = @Referencia)
  AND (@Celula IS NULL OR s.celula = @Celula)
GROUP BY
    s.referencia,
    s.celula
HAVING COUNT(*) <> 1;
