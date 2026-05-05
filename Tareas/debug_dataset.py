# ============================================================
# DEBUG SCRIPT PARA IGNITION SCRIPT CONSOLE
# Ejecutar este script para diagnosticar problemas con el dataset
# ============================================================

# Database name - ajustado para GPILOT2
database = "GPILOT2"

# Configuracion
celula = '142A'
tp = '[G-PILOT_TAGS]'  # Cambiar si tu tag provider es diferente

print "=" * 60
print "DEBUG: Analizando Dataset para celula {}".format(celula)
print "=" * 60

# 1. Leer el dataset actual del tag
print "\n[1] DATASET ACTUAL EN EL TAG"
print "-" * 40
try:
    path = tp + "Dataset/Tareas_Celula142"
    existingDataset = system.tag.readBlocking([path])[0].value
    print "Columnas: {}".format(list(existingDataset.getColumnNames()))
    print "Total filas: {}".format(existingDataset.getRowCount())
    
    # Filtrar solo filas de esta celula
    filasCelula = []
    for row in range(existingDataset.getRowCount()):
        celulaRow = existingDataset.getValueAt(row, "celula")
        if celulaRow is not None:
            celulaRow = str(celulaRow).strip()
        if celulaRow == celula:
            filasCelula.append({
                'row': row,
                'tarea': existingDataset.getValueAt(row, "tarea"),
                'maquina': existingDataset.getValueAt(row, "maquina"),
                'elemento': existingDataset.getValueAt(row, "elemento")
            })
    
    print "\nFilas para {} en dataset actual: {}".format(celula, len(filasCelula))
    for f in filasCelula:
        print "  Row {}: tarea={}, maquina={}".format(
            f['row'], f['tarea'], f['maquina'])
except Exception as e:
    print "ERROR leyendo tag: {}".format(str(e))

# 2. Consultar G_Pilot_Tareas_Resumen
print "\n[2] DATOS EN G_Pilot_Tareas_Resumen"
print "-" * 40
try:
    queryResumen = """
        SELECT id, tarea, maquina, elementos, celula, referencia, activo
        FROM G_Pilot_Tareas_Resumen
        WHERE celula = ?
        ORDER BY maquina, tarea
    """
    dataResumen = system.db.runPrepQuery(queryResumen, [celula], database)
    print "Filas en Tareas_Resumen para {}: {}".format(celula, dataResumen.rowCount)
    for row in range(dataResumen.rowCount):
        print "  ID {}: tarea={}, maquina={}, elementos={}".format(
            dataResumen.getValueAt(row, "id"),
            dataResumen.getValueAt(row, "tarea"),
            dataResumen.getValueAt(row, "maquina"),
            str(dataResumen.getValueAt(row, "elementos"))[:50] + "..." if dataResumen.getValueAt(row, "elementos") and len(str(dataResumen.getValueAt(row, "elementos"))) > 50 else dataResumen.getValueAt(row, "elementos")
        )
except Exception as e:
    print "ERROR consultando Tareas_Resumen: {}".format(str(e))

# 3. Consultar G_Pilot_Tareas
print "\n[3] DATOS EN G_Pilot_Tareas"
print "-" * 40
try:
    queryTareas = """
        SELECT id, tarea, maquina, elemento, celula, referencia, ocurrenciaStd
        FROM G_Pilot_Tareas
        WHERE celula = ?
        ORDER BY maquina, tarea
    """
    dataTareas = system.db.runPrepQuery(queryTareas, [celula], database)
    print "Filas en Tareas para {}: {}".format(celula, dataTareas.rowCount)
    for row in range(dataTareas.rowCount):
        print "  ID {}: tarea={}, maquina={}, elemento={}".format(
            dataTareas.getValueAt(row, "id"),
            dataTareas.getValueAt(row, "tarea"),
            dataTareas.getValueAt(row, "maquina"),
            str(dataTareas.getValueAt(row, "elemento"))[:50] + "..." if dataTareas.getValueAt(row, "elemento") and len(str(dataTareas.getValueAt(row, "elemento"))) > 50 else dataTareas.getValueAt(row, "elemento")
        )
except Exception as e:
    print "ERROR consultando Tareas: {}".format(str(e))

# 4. Verificar si obtenerTareas esta devolviendo bien
print "\n[4] RESULTADO DE obtenerTareas(celula, referencia)"
print "-" * 40
try:
    # Importar el modulo
    referencia = 'R120638'  # O usar la funcion obtenerReferencia
    
    # Llamar a obtenerTareas (usando el modulo Tareas.Data.Teorico)
    # Si no funciona, usar la query directa
    queryObtenerTareas = """
    WITH GroupedData AS (
        SELECT 
            referencia,
            tarea,
            maquina,
            COALESCE(ocurrencia, ocurrenciaStd) AS ocurrencia_final,
            turno,
            celula,
            STUFF((
                SELECT ' | ' + elemento
                FROM G_Pilot_Tareas AS t2
                WHERE t2.referencia = t1.referencia 
                  AND t2.tarea = t1.tarea
                  AND (t2.maquina = t1.maquina OR (t2.maquina IS NULL AND t1.maquina IS NULL))
                  AND (COALESCE(t2.ocurrencia, t2.ocurrenciaStd) = COALESCE(t1.ocurrencia, t1.ocurrenciaStd) 
                       OR (COALESCE(t2.ocurrencia, t2.ocurrenciaStd) IS NULL AND COALESCE(t1.ocurrencia, t1.ocurrenciaStd) IS NULL))
                  AND (t2.turno = t1.turno OR (t2.turno IS NULL AND t1.turno IS NULL))
                FOR XML PATH('')
            ), 1, 3, '') AS elementos_concatenados,
            CASE 
                WHEN CHARINDEX('/', tarea) > 0 THEN
                    CASE 
                        WHEN PATINDEX('% [0-9]%/[0-9]%', tarea) > 0 THEN
                            LEFT(tarea, PATINDEX('% [0-9]%/[0-9]%', tarea))
                        ELSE
                            LEFT(tarea, CHARINDEX('/', tarea) - 1)
                    END
                ELSE tarea 
            END AS tarea_base
        FROM G_Pilot_Tareas AS t1
        WHERE 
            tarea NOT LIKE 'Tiempo de m%' AND
            tarea NOT LIKE 'Carga%' AND
            tarea NOT LIKE 'Traslados%' AND
            t1.celula = ?
        GROUP BY referencia, tarea, maquina, ocurrencia, ocurrenciaStd, turno, celula
    )
    SELECT DISTINCT
        referencia,
        CASE 
            WHEN turno = 1 THEN tarea_base + '1/1'
            WHEN CHARINDEX('/', tarea) > 0 THEN 
                tarea_base + '1/' + CAST(ocurrencia_final AS VARCHAR)
            ELSE tarea
        END AS tarea,
        maquina,
        ocurrencia_final AS ocurrencia,
        elementos_concatenados AS elementos,
        celula
    FROM GroupedData
    ORDER BY tarea;
    """
    dataObtenerTareas = system.db.runPrepQuery(queryObtenerTareas, [celula], database)
    print "Filas devueltas por obtenerTareas: {}".format(dataObtenerTareas.rowCount)
    
    # Agrupar por maquina
    maquinas = {}
    for row in range(dataObtenerTareas.rowCount):
        maquina = dataObtenerTareas.getValueAt(row, "maquina")
        if maquina not in maquinas:
            maquinas[maquina] = []
        maquinas[maquina].append({
            'tarea': dataObtenerTareas.getValueAt(row, "tarea"),
            'ocurrencia': dataObtenerTareas.getValueAt(row, "ocurrencia"),
            'elementos': str(dataObtenerTareas.getValueAt(row, "elementos"))[:30] + "..." if dataObtenerTareas.getValueAt(row, "elementos") and len(str(dataObtenerTareas.getValueAt(row, "elementos"))) > 30 else dataObtenerTareas.getValueAt(row, "elementos")
        })
    
    for maquina, tareas in maquinas.items():
        print "\n  Maquina: {}".format(maquina)
        for t in tareas:
            print "    - {} (ocurrencia={})".format(t['tarea'], t['ocurrencia'])
            
except Exception as e:
    print "ERROR en obtenerTareas: {}".format(str(e))
    import traceback
    traceback.print_exc()

# 5. Ver tiempos de maquina
print "\n[5] TIEMPOS DE MAQUINA (datasetMinutos)"
print "-" * 40
try:
    queryMinutos = """
        SELECT 
            maquina,
            CASE 
                WHEN min IS NULL THEN min_std
                ELSE min 
            END AS minutos,
            celula,
            elemento
        FROM G_Pilot_Tareas
        WHERE tarea LIKE 'Tiempo de m%'
          AND maquina != 'VARIOS'
          AND maquina != 'GRAFICO'
          AND elemento NOT LIKE 'MEDICI%'
          AND celula = ?
    """
    dataMinutos = system.db.runPrepQuery(queryMinutos, [celula], database)
    print "Tiempos de maquina para {}: {}".format(celula, dataMinutos.rowCount)
    for row in range(dataMinutos.rowCount):
        print "  Maquina: {}, Minutos: {}, Elemento: {}".format(
            dataMinutos.getValueAt(row, "maquina"),
            dataMinutos.getValueAt(row, "minutos"),
            dataMinutos.getValueAt(row, "elemento")
        )
except Exception as e:
    print "ERROR consultando minutos: {}".format(str(e))

print "\n" + "=" * 60
print "DEBUG COMPLETO"
print "=" * 60
