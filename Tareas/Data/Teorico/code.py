def obtenerTiemposMaquina_v0():
	# Tareas.Data.Teorico.obtenerTiemposMaquina_v0()
	"""
	Devuelve los tiempos por máquina (tareas que empiezan por 'Tiempo de m'),
	con los minutos correctos según las columnas 'min' y 'min_std'.
	"""
	database = constantes.Database_Tareas
	tablaTareas = constantes.LINEA + "_Tareas"
	
	query = """
	SELECT 
	    maquina,
	    CASE 
	        WHEN min IS NULL THEN min_std
	        ELSE min 
	    END AS minutos,
	    celula,
	    elemento
	FROM [dbo].[{tabla}]
	WHERE tarea LIKE 'Tiempo de m%'
	AND maquina != 'VARIOS'
	AND maquina != 'GRAFICO'
	AND elemento not LIKE 'MEDICI%'
	""".format(tabla=tablaTareas)

	dataset = system.db.runQuery(query, database)
	print("Tiempos maquina encontrados:", dataset.rowCount)
	
	#for row in range(dataset.getRowCount()):
	#    print(dataset.getValueAt(row, "maquina"), dataset.getValueAt(row, "minutos"), dataset.getValueAt(row, "celula"))
	
	return dataset
	
def obtenerTiemposMaquina(celula, referencia):
    # Tareas.Data.Teorico.obtenerTiemposMaquina(celula, referencia)
    """
    Devuelve los tiempos por máquina (tareas que empiezan por 'Tiempo de m'),
    con los minutos correctos según las columnas 'min' y 'min_std'.
    Se puede filtrar por referencia y celula.
    """
    database = constantes.Database_Tareas
    tablaTareas = constantes.LINEA + "_Tareas"

    filtro = ""
    params = []

    if referencia:
        filtro += " AND referencia = ?"
        params.append(str(referencia))
    if celula:
        filtro += " AND celula = ?"
        params.append(str(celula))

    query = """
    SELECT 
        maquina,
        CASE 
            WHEN min IS NULL THEN min_std
            ELSE min 
        END AS minutos,
        celula,
        elemento
    FROM [dbo].[{tabla}]
    WHERE tarea LIKE 'Tiempo de m%'
      AND maquina != 'VARIOS'
      AND maquina != 'GRAFICO'
      AND elemento NOT LIKE 'MEDICI%'
      {filtro}
    """.format(tabla=tablaTareas, filtro=filtro)

    if params:
        dataset = system.db.runPrepQuery(query, params, database)
    else:
        dataset = system.db.runQuery(query, database)

    print("Tiempos maquina encontrados:", dataset.rowCount)
    # for row in range(dataset.getRowCount()):
    #     print(dataset.getValueAt(row, "maquina"), dataset.getValueAt(row, "minutos"), dataset.getValueAt(row, "celula"))

    return dataset
 
	
def obtenerTiemposMaquina_crearTareas(celula, referencia):
    # Tareas.Data.Teorico.obtenerTiemposMaquina_crearTareas(celula, referencia)
    """
    Devuelve los tiempos por máquina (tareas que empiezan por 'Tiempo de m'),
    con los minutos correctos según las columnas 'min' y 'min_std'.
    Se puede filtrar por referencia y celula.
    Esto sirve para Crear Tareas
    """
    database = constantes.Database_Tareas
    tablaTareas = constantes.LINEA + "_Tareas"

    filtro = ""
    params = []

    if referencia:
        filtro += " AND referencia = ?"
        params.append(str(referencia))
    if celula:
        filtro += " AND celula = ?"
        params.append(str(celula))

    query = """
    SELECT 
        maquina
    FROM [dbo].[{tabla}]
    WHERE tarea LIKE 'Tiempo de m%'
      AND maquina != 'VARIOS'
      AND maquina != 'GRAFICO'
      AND elemento NOT LIKE 'MEDICI%'
      {filtro}
    """.format(tabla=tablaTareas, filtro=filtro)

    if params:
        dataset = system.db.runPrepQuery(query, params, database)
    else:
        dataset = system.db.runQuery(query, database)

    print("Tiempos maquina encontrados:", dataset.rowCount)
    # for row in range(dataset.getRowCount()):
    #     print(dataset.getValueAt(row, "maquina"), dataset.getValueAt(row, "minutos"), dataset.getValueAt(row, "celula"))
    # Convierte el dataset a una lista de diccionarios
    
    # Si tienes un dataset llamado 'data'
    result = []
    for row in range(dataset.rowCount):
	    rowDict = {}
	    for col in range(dataset.columnCount):
	        colName = dataset.getColumnName(col)
	        rowDict[colName] = dataset.getValueAt(row, col)
	    result.append(rowDict)

    #return dataset
    return result
    
    
	
def obtenerTareas_v0():
    tp = constantes.tag_provider
    database = constantes.Database_Tareas
    
    tablaTareas = constantes.LINEA + "_Tareas"
    
    query = """
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
                FROM {tabla} AS t2
                WHERE t2.referencia = t1.referencia 
                  AND t2.tarea = t1.tarea
                  AND (t2.maquina = t1.maquina OR (t2.maquina IS NULL AND t1.maquina IS NULL))
                  AND (COALESCE(t2.ocurrencia, t2.ocurrenciaStd) = COALESCE(t1.ocurrencia, t1.ocurrenciaStd) 
                       OR (COALESCE(t2.ocurrencia, t2.ocurrenciaStd) IS NULL AND COALESCE(t1.ocurrencia, t1.ocurrenciaStd) IS NULL))
                  AND (t2.turno = t1.turno OR (t2.turno IS NULL AND t1.turno IS NULL))
                FOR XML PATH('')
            ), 1, 3, '') AS elementos_concatenados,
            
            -- Extraer solo el texto descriptivo usando una lógica más simple
            CASE 
                WHEN CHARINDEX('/', tarea) > 0 THEN
                    -- Buscar el último espacio antes del patrón número/número
                    CASE 
                        WHEN PATINDEX('% [0-9]%/[0-9]%', tarea) > 0 THEN
                            LEFT(tarea, PATINDEX('% [0-9]%/[0-9]%', tarea))
                        ELSE
                            LEFT(tarea, CHARINDEX('/', tarea) - 1)
                    END
                ELSE tarea 
            END AS tarea_base
        FROM {tabla} AS t1
        WHERE 
            tarea NOT LIKE 'Tiempo de m%' AND
            tarea NOT LIKE 'Carga%' AND
            tarea NOT LIKE 'Traslados%'
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
    ORDER BY referencia, tarea;
    """.format(tabla=tablaTareas)
    
    dataset = system.db.runQuery(query, database)
    print("Filas obtenidas:", dataset.rowCount)
    
    for row in range(dataset.getRowCount()):
        print(dataset.getValueAt(row, "referencia"), dataset.getValueAt(row, "tarea"), dataset.getValueAt(row, "elementos"), dataset.getValueAt(row, "maquina"), dataset.getValueAt(row, "ocurrencia"))
    
    return dataset
	
def obtenerTareas(celula, referencia):
    # Tareas.Data.Teorico.obtenerTareas(celula, referencia)
    """
    Obtener la información general para la vista de tareas
    """
    database = constantes.Database_Tareas
    tablaTareas = constantes.LINEA + "_Tareas"

    filtro = ""
    params = []

    if referencia:
        filtro += " AND t1.referencia = ?"
        params.append(str(referencia))
    if celula:
        filtro += " AND t1.celula = ?"
        params.append(str(celula))

    query = """
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
                FROM {tabla} AS t2
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
        FROM {tabla} AS t1
        WHERE 
            tarea NOT LIKE 'Tiempo de m%' AND
            tarea NOT LIKE 'Carga%' AND
            tarea NOT LIKE 'Traslados%'
            {filtro}
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
    ORDER BY referencia, tarea;
    """.format(tabla=tablaTareas, filtro=filtro)

    dataset = system.db.runPrepQuery(query, params, database) if params else system.db.runQuery(query, database)

    print("Filas obtenidas:", dataset.rowCount)
    for row in range(dataset.getRowCount()):
        print(dataset.getValueAt(row, "referencia"), dataset.getValueAt(row, "tarea"),
              dataset.getValueAt(row, "elementos"), dataset.getValueAt(row, "maquina"),
              dataset.getValueAt(row, "ocurrencia"))

    return dataset
	
	
def generarDatasetTiempos_v0(datasetMinutos, datasetTareas):
	# Tareas.Data.Teorico.generarDatasetTiempos(datasetMinutos, datasetTareas)
	"""
	Devuelve un Dataset de Ignition con:
	['tarea', 'cuando', 'celula', 'maquina', 'elemento', 'completado']
	Al comparar 'celula' y 'maquina' de dos datasets, y multiplicar minutos × ocurrencia.
	"""
	from system.dataset import toDataSet
	import system.date

	# Columnas finales
	columnas = ["tarea", "cuando", "celula", "maquina", "elemento", "completado"]
	resultados = []

	# Convertimos datasetMinutos a lista de dicts
	minutos_lista = []
	for i in range(datasetMinutos.rowCount):
		minutos_lista.append({
			'maquina': datasetMinutos.getValueAt(i, 'maquina'),
			'celula': datasetMinutos.getValueAt(i, 'celula'),
			'minutos': datasetMinutos.getValueAt(i, 'minutos'),
			'elemento': datasetMinutos.getValueAt(i, 'elemento')
		})

	# Hora actual como punto de inicio
	base_time = system.date.now()

	# Recorremos datasetTareas
	for i in range(datasetTareas.rowCount):
		tarea = datasetTareas.getValueAt(i, 'tarea')
		maquina = datasetTareas.getValueAt(i, 'maquina')
		celula = datasetTareas.getValueAt(i, 'celula')
		ocurrencia = datasetTareas.getValueAt(i, 'ocurrencia') or 0
		elemento = datasetTareas.getValueAt(i, 'elementos')
		completado = 0

		# Validar que ocurrencia sea positiva
		if ocurrencia <= 0:
			continue

		# Buscar la primera coincidencia válida en datasetMinutos
		for row in minutos_lista:
			if row['celula'] == celula and row['maquina'] == maquina:
				# Repetir tarea cada 'ocurrencia' minutos durante 12 horas
				minutos = row['minutos'] or 0
				newocurrencia = minutos * ocurrencia
				total_minutos = 8 * 60
				num_repeticiones = total_minutos // newocurrencia
				print "Tarea: {}, Ocurrencia: {}, Célula: {}, Máquina: {}".format(
						tarea, newocurrencia, celula, maquina
					)

				for j in range(int(num_repeticiones)):
					cuando = system.date.addMinutes(base_time, (j+1) * int(newocurrencia))
					resultados.append([tarea, cuando, celula, maquina, elemento, completado])
				break  # Solo usar primera coincidencia

	# Crear y devolver dataset
	return toDataSet(columnas, resultados)
	
def generarDatasetTiempos(datasetMinutos, datasetTareas):
	# Tareas.Data.Teorico.generarDatasetTiempos(datasetMinutos, datasetTareas)
	"""
	Devuelve un Dataset de Ignition con:
	['tarea', 'cuando', 'celula', 'maquina', 'elemento', 'completado']
	Al comparar 'celula' y 'maquina' de dos datasets, y multiplicar minutos × ocurrencia.
	"""
	from system.dataset import toDataSet
	import system.date

	# Columnas finales
	columnas = ["tarea", "cuando", "celula", "maquina", "elemento", "completado"]
	resultados = []

	# Convertimos datasetMinutos a lista de dicts
	minutos_lista = []
	for i in range(datasetMinutos.rowCount):
		minutos_lista.append({
			'maquina': datasetMinutos.getValueAt(i, 'maquina'),
			'celula': datasetMinutos.getValueAt(i, 'celula'),
			'minutos': datasetMinutos.getValueAt(i, 'minutos'),
			'elemento': datasetMinutos.getValueAt(i, 'elemento')
		})

	# Hora actual como punto de inicio
	base_time = system.date.now()

	# Recorremos datasetTareas
	for i in range(datasetTareas.rowCount):
		tarea = datasetTareas.getValueAt(i, 'tarea')
		maquina = datasetTareas.getValueAt(i, 'maquina')
		celula = datasetTareas.getValueAt(i, 'celula')
		ocurrencia = datasetTareas.getValueAt(i, 'ocurrencia') or 0
		elemento = datasetTareas.getValueAt(i, 'elementos')
		completado = 0

		# Validar que ocurrencia sea positiva
		if ocurrencia <= 0:
			continue
		# Buscar la primera coincidencia válida en datasetMinutos
		for row in minutos_lista:
		    if row['celula'] == celula and row['maquina'] == maquina:
		        # Calcular intervalo
		        minutos = row['minutos'] or 0
		        newocurrencia = minutos * ocurrencia
		        total_minutos = 8 * 60
		        num_repeticiones = total_minutos // newocurrencia
		        
		        print "Tarea: {}, Ocurrencia: {}, Célula: {}, Máquina: {}".format(
		            tarea, newocurrencia, celula, maquina
		        )
		        
		        # SIEMPRE añadir la primera ocurrencia (sin importar si está fuera de 8 horas)
		        primera_cuando = system.date.addMinutes(base_time, int(newocurrencia))
		        resultados.append([tarea, primera_cuando, celula, maquina, elemento, completado])
		        
		        # Añadir el resto solo si están dentro del límite de 8 horas
		        for j in range(1, int(num_repeticiones)):  # Empezar desde 1 (la primera ya está añadida)
		            cuando = system.date.addMinutes(base_time, (j+1) * int(newocurrencia))
		            resultados.append([tarea, cuando, celula, maquina, elemento, completado])

	# Crear y devolver dataset
	return toDataSet(columnas, resultados)
	
def reprogramarTareasDesdeHora(datasetMinutos, datasetTareas, horaBase=None):
	# Tareas.Data.Teorico.reprogramarTareasDesdeHora(datasetMinutos, datasetTareas, None)
    """
    REPROGRAMAR TAREAS CADA CAMBIO DE TURNO
    Reprograma tareas manteniendo el ritmo original desde la horaBase.
    Si hay una no completada antes de horaBase, la secuencia se reinicia desde horaBase.
    Indica la ultima tarea completada.
    Concatena las tareas a la siguiente tarea por hacer manteniendo minutos y ocurrencia
    """
    from system.dataset import toDataSet
    import system.date

    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    path = tp + "Dataset/Tareas_Celula" + celulaLinea

    # Leer dataset actual
    tareas_actuales = system.tag.readBlocking([path])[0].value
    colNames = list(tareas_actuales.getColumnNames())
    rowCount = tareas_actuales.getRowCount()

    colTarea = colNames.index("tarea")
    colCelula = colNames.index("celula")
    colMaquina = colNames.index("maquina")
    colCuando = colNames.index("cuando")
    colCompletado = colNames.index("completado")
    colElemento = colNames.index("elemento")

    if horaBase is None:
        horaBase = system.date.now()

    # Última completada más cercana (antes o igual a horaBase)
    ultimas_completadas = {}
    for i in range(rowCount):
        if tareas_actuales.getValueAt(i, colCompletado) == 1:
            clave = (
                str(tareas_actuales.getValueAt(i, colTarea)),
                str(tareas_actuales.getValueAt(i, colCelula)),
                str(tareas_actuales.getValueAt(i, colMaquina))
            )
            fecha = tareas_actuales.getValueAt(i, colCuando)
            if fecha <= horaBase:
                if clave not in ultimas_completadas or abs(system.date.millisBetween(horaBase, fecha)) < abs(system.date.millisBetween(horaBase, ultimas_completadas[clave][1])):
                    ultimas_completadas[clave] = (i, fecha)

    # Tarea no completada más cercana (antes o después de horaBase)
    no_completadas_cercanas = {}
    for i in range(rowCount):
        if tareas_actuales.getValueAt(i, colCompletado) == 0:
            clave = (
                str(tareas_actuales.getValueAt(i, colTarea)),
                str(tareas_actuales.getValueAt(i, colCelula)),
                str(tareas_actuales.getValueAt(i, colMaquina))
            )
            fecha = tareas_actuales.getValueAt(i, colCuando)
            diferencia = abs(system.date.millisBetween(horaBase, fecha))
            if clave not in no_completadas_cercanas or diferencia < no_completadas_cercanas[clave][2]:
                no_completadas_cercanas[clave] = (i, fecha, diferencia)

    # Última no completada ANTES de horaBase
    no_completadas_antes = {}
    for i in range(rowCount):
        if tareas_actuales.getValueAt(i, colCompletado) == 0:
            clave = (
                str(tareas_actuales.getValueAt(i, colTarea)),
                str(tareas_actuales.getValueAt(i, colCelula)),
                str(tareas_actuales.getValueAt(i, colMaquina))
            )
            fecha = tareas_actuales.getValueAt(i, colCuando)
            if fecha < horaBase:
                if clave not in no_completadas_antes or fecha > no_completadas_antes[clave][1]:
                    no_completadas_antes[clave] = (i, fecha)

    # Duración y elemento por celula/maquina
    min_dict = {}
    for i in range(datasetMinutos.rowCount):
        key = (
            str(datasetMinutos.getValueAt(i, 'celula')),
            str(datasetMinutos.getValueAt(i, 'maquina'))
        )
        min_dict[key] = {
            'minutos': datasetMinutos.getValueAt(i, 'minutos'),
            'elemento': datasetMinutos.getValueAt(i, 'elemento')
        }

    nuevas_filas = []

    # Generar nuevas tareas
    for i in range(datasetTareas.rowCount):
        tarea = datasetTareas.getValueAt(i, 'tarea')
        celula = datasetTareas.getValueAt(i, 'celula')
        maquina = datasetTareas.getValueAt(i, 'maquina')
        ocurrencia = datasetTareas.getValueAt(i, 'ocurrencia') or 0
        elemento = datasetTareas.getValueAt(i, 'elementos')
        completado = 0

        if ocurrencia <= 0:
            continue

        key = (celula, maquina)
        if key not in min_dict:
            continue

        duracion = min_dict[key]['minutos'] or 0
        new_ocurrencia = duracion * ocurrencia
        clave_tarea = (str(tarea), str(celula), str(maquina))

        # --- Selección de punto de inicio
        if clave_tarea in no_completadas_antes:
            start_time = horaBase  # Reinicia desde horaBase
        elif clave_tarea in no_completadas_cercanas:
            start_time = no_completadas_cercanas[clave_tarea][1]
        elif clave_tarea in ultimas_completadas:
            start_time = ultimas_completadas[clave_tarea][1]
        else:
            start_time = horaBase

        max_end_time = system.date.addHours(horaBase, 12)
        cuenta = 0

        while True:
            cuando = system.date.addMinutes(start_time, cuenta * int(new_ocurrencia))
            if cuando > max_end_time:
                break
            if cuando >= horaBase:
                nuevas_filas.append([tarea, cuando, celula, maquina, elemento, completado])
            cuenta += 1

    # Añadir última completada
    for idx, _ in ultimas_completadas.values():
        row = [tareas_actuales.getValueAt(idx, col) for col in colNames]
        nuevas_filas.append(row)

    # Guardar dataset final
    finalDataset = toDataSet(colNames, nuevas_filas)
    system.tag.writeBlocking([path], [finalDataset])
    print "Dataset actualizado con nuevas tareas teóricas desde", horaBase

    return True

def marcarTareasComoCompletadasAntesDe(horaLimite):
    # Tareas.Data.Teorico.marcarTareasComoCompletadasAntesDe(horaLimite)
    """
    PARA PRUEBAS DE TAREAS
    Marca como completadas todas las tareas cuyo 'cuando' es anterior a 'horaLimite'.
    """

    #---PARAMETROS------------------------------------------
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    path = tp + "Dataset/Tareas_Celula" + celulaLinea

    # Leer el dataset actual
    tareas_actuales = system.tag.readBlocking([path])[0].value
    colNames = list(tareas_actuales.getColumnNames())
    rowCount = tareas_actuales.getRowCount()

    colCuando = colNames.index("cuando")
    colCompletado = colNames.index("completado")

    nuevas_filas = []

    for i in range(rowCount):
        fila = [tareas_actuales.getValueAt(i, col) for col in range(len(colNames))]
        cuando = fila[colCuando]

        # Marcar completado si es anterior a la hora límite
        if cuando < horaLimite:
            fila[colCompletado] = 1

        nuevas_filas.append(fila)

    # Escribir el dataset actualizado
    nuevoDataset = system.dataset.toDataSet(colNames, nuevas_filas)
    system.tag.writeBlocking([path], [nuevoDataset])
    print "Tareas actualizadas hasta:", horaLimite

    return True

def accionesCambioBandejaDescarga(referencia):
	# Tareas.Data.Teorico.accionesCambioBandejaDescarga(referencia)
	"""
	Cambia la ocurrencia del cambio de bandeja cuando se inicializa un estandar
	"""
	#---PARAMETROS--------
	databaseTareas = constantes.Database_Tareas
	database = constantes.Database_Tareas_2
	tablaTareas = constantes.LINEA + "_Secuencia"
	tabla = "CGF_RACKS_DATA_MARTS"
	
	maquina = "CELULA"
	elemento = "Cambio de carga bandejas PP"
	#---------------------
	try:
	    #---Obtenemos valor RS_CANTIDAD--------------------------
	    query = """
	        SELECT TOP 1
	            RS_CANTIDAD
	        FROM {0}
	        WHERE RS_CODIGO_REFERENCIA = ?
	        AND RS_ETIQUETA_RACK_LOCAL LIKE 'GFV-%'
	        ORDER BY RS_FECHA DESC
	    """.format(tabla)
	
	    params = [str(referencia)]
	    data = system.db.runPrepQuery(query, params, database)
	
	    if not data or len(data) == 0:
	        print "No se encontraron datos en", tabla, "para referencia", referencia
	        return False
	
	    valor = float(data[0][0])
	    if valor == 0:
	        print "RS_CANTIDAD = 0, no se puede dividir"
	        return False
	
	    newOcurrencia = 1 / valor
	    print "Valor:", valor
	    print "Nuevo valor de ocurrencia:", newOcurrencia
	
	    #---Obtenemos ocurrencia actual--------------------------
	    query = """
	        SELECT ocurrencia
	        FROM {0}
	        WHERE maquina = ?
	        AND elemento = ?
	    """.format(tablaTareas)
	
	    params = [str(maquina), str(elemento)]
	    data = system.db.runPrepQuery(query, params, databaseTareas)
	
	    if not data or len(data) == 0:
	        print "No se encontraron registros en", tablaTareas, "para maquina/elemento"
	        return False
	
	    ocurrenciaActual = data[0][0]
	    print "Ocurrencia actual:", ocurrenciaActual
	
	    #---UPDATE de ocurrencia--------------------------
	    queryUpdate = """
	        UPDATE {0}
	        SET ocurrencia = ?
	        WHERE maquina = ?
	        AND elemento = ?
	    """.format(tablaTareas)
	
	    paramsUpdate = [newOcurrencia, str(maquina), str(elemento)]
	    filasAfectadas = system.db.runPrepUpdate(queryUpdate, paramsUpdate, databaseTareas)
	
	    if filasAfectadas == 0:
	        print "No se actualizó ningún registro en", tablaTareas
	        return False
	
	    print "Ocurrencia actualizada correctamente a", newOcurrencia
	    return True
	
	except Exception as e:
	    print "Error en script de actualización de ocurrencia:", str(e)
	    return False
 