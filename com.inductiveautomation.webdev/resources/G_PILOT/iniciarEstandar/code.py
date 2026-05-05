import system.dataset as ds
import system.date

def iniciarEstandar(celula):
    # G_PILOT.iniciarEstandar.iniciarEstandar(celula)
    """
    Reinicia el estándar en el dataset del tag:
    - Borra lo que haya de la célula indicada.
    - Inserta las nuevas filas generadas para esa célula.
    - Mantiene intactos los datos de las demás células.
    """
    import system.dataset as ds

    try:
	    #---PARAMETROS-------------------------
	    tp = constantes.tag_provider
	    #celulaLinea = constantes.celulaLinea
	    celulaLinea = celula[:3] # Da "142" de "142A"
	    referencia = obtenerReferencia(celula)
	
	    #---Obtenemos los tiempos que tarda cada maquina
	    datasetMinutos = obtenerTiemposMaquina(celula, referencia)
	    #---Obtenemos las tareas de la tabla Tareas de base de datos
	    datasetTareas = obtenerTareas(celula, referencia)
	    #---Segun los tiempos y las tareas, calculamos la data a enviar
	    datasetNuevo = generarDatasetTiempos(datasetMinutos, datasetTareas)
	
	    #---Leemos el dataset existente-----------------------------------------------------------------
	    path = tp + "Dataset/Tareas_Celula" + celulaLinea
	    existingDataset = system.tag.readBlocking([path])[0].value
	    columns = list(existingDataset.getColumnNames())
	
	    #---Filtrar las filas que NO sean de esta célula
	    filasMantener = []
	    for row in range(existingDataset.getRowCount()):
	        if existingDataset.getValueAt(row, "celula") != celula:
	            filasMantener.append([existingDataset.getValueAt(row, col) for col in columns])
	
	    #---Añadir filas nuevas de la célula actual
	    for row in range(datasetNuevo.getRowCount()):
	        filasMantener.append([datasetNuevo.getValueAt(row, col) for col in datasetNuevo.getColumnNames()])
	
	    #---Crear dataset final
	    finalDataset = ds.toDataSet(columns, filasMantener)
	
	    #---Escribir al tag
	    system.tag.writeBlocking([path], [finalDataset])
	
	    #----------------------------------------------------------------------------------------------
	    # Actualizar tags derivados
	    tareasPorMaquinaGeneral(celula)
	    inicializarTodosLosDatasetsPiezas(celula)
	    
	    # Actualizar tarea grafico
	    actualizarTareaGrafico(celula)
	
	    return True
    
    except Exception as e:
        system.util.getLogger("ScriptError").error(
            "G_PILOT.iniciarEstandar(): {}".format(str(e))
        )
        return False
    

def obtenerTiemposMaquina(celula, referencia):
    # G_PILOT.obtenerTiemposMaquina(celula, referencia)
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
    
def obtenerTareas(celula, referencia):
    # G_PILOT.obtenerTareas(celula, referencia)
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
    
def generarDatasetTiempos(datasetMinutos, datasetTareas):
	# G_PILOT.generarDatasetTiempos(datasetMinutos, datasetTareas)
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
	
def actualizarTareaGrafico(celula):
    # G_PILOT.actualizarTareaGrafico(celula)
    """
    Adef actualizarTareaGrafico(celula):ctualiza la hora 'cuando' de la tarea 'Grafico' (o que empiece por 'Grafico')
    para la célula indicada, según:
    - Si hay una tarea CH de Talladora o Afeitadora SIN completar y dentro del turno actual: usar su hora.
    - Si no hay ninguna válida o está fuera del turno: usar 2 horas después del inicio de turno.
    """

    from system.dataset import toDataSet
    import system.date

    try:
        #---PARAMETROS---------------------------------------------
        tp = constantes.tag_provider
        celulaLinea = constantes.celulaLinea
        tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
        #----------------------------------------------------------

        # === Funciones auxiliares ===
        def obtenerInicioYFinTurno():
            ahora = system.date.now()
            hora = system.date.getHour24(ahora)

            if 6 <= hora < 14:  # Turno mañana
                inicio = system.date.setTime(ahora, 6, 0, 0)
                fin = system.date.setTime(ahora, 14, 0, 0)
                turno = 1
            elif 14 <= hora < 22:  # Turno tarde
                inicio = system.date.setTime(ahora, 14, 0, 0)
                fin = system.date.setTime(ahora, 22, 0, 0)
                turno = 2
            else:  # Turno noche
                if hora < 6:
                    # Si son las 00:00–05:59 → turno empezó el día anterior
                    inicio = system.date.addDays(system.date.setTime(ahora, 22, 0, 0), -1)
                else:
                    inicio = system.date.setTime(ahora, 22, 0, 0)
                fin = system.date.addHours(inicio, 8)
                turno = 3
            return inicio, fin, turno

        def estaEnTurno(fecha, inicio, fin):
            # Verifica si una fecha cae dentro del rango del turno actual
            return (fecha >= inicio) and (fecha < fin)

        # 1. Leer dataset actual
        dataset = system.tag.readBlocking([tagPath])[0].value
        columnas = list(dataset.columnNames)
        nuevas_filas = []

        # 2. Calcular turno actual
        inicio_turno, fin_turno, nro_turno = obtenerInicioYFinTurno()

        # 3. Buscar candidatos válidos
        candidatos = []
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}
            if row["celula"] != celula or row["completado"] != 0:
                continue

            if row["tarea"].startswith("CH") and row["maquina"].upper() == "TALLADORA":
                if estaEnTurno(row["cuando"], inicio_turno, fin_turno):
                    candidatos.append((row, 1))
            elif row["tarea"].startswith("CH") and row["maquina"].upper() == "AFEITADORA":
                if estaEnTurno(row["cuando"], inicio_turno, fin_turno):
                    candidatos.append((row, 2))

        # 4. Determinar hora programada
        if candidatos:
            candidatos.sort(key=lambda x: x[1])
            fila_candidato = candidatos[0][0]
            hora_programada = fila_candidato["cuando"]
        else:
            # Sin candidatos válidos o fuera de turno
            hora_programada = system.date.addHours(inicio_turno, 2)

        # 5. Actualizar fila de la tarea "Grafico"
        grafico_encontrado = False
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}

            if row["celula"] == celula and str(row["tarea"]).startswith("Grafico") and row["completado"] == 0:
                row["cuando"] = hora_programada
                grafico_encontrado = True

            nuevas_filas.append([row[col] for col in columnas])

        # 6. Si no se encontró la tarea “Grafico”
        if not grafico_encontrado:
            print("⚠️ No se encontró tarea 'Grafico' para la célula:", celula)
            return {"warning": "Tarea 'Grafico' no encontrada en el dataset"}

        # 7. Escribir el dataset actualizado
        dataset_actualizado = toDataSet(columnas, nuevas_filas)
        system.tag.writeBlocking([tagPath], [dataset_actualizado])

        print("Tarea 'Grafico' actualizada para la célula:", celula)
        print("Hora programada:", hora_programada)
        print("Turno actual:", nro_turno)
        return True

    except Exception as e:
        print("❌ Error en actualizarHoraGrafico():", str(e))
        return {"error": "Error interno al actualizar tag"}
    
def tareasPorMaquinaGeneral(celula):
	# G_PILOT.tareasPorMaquinaGeneral(celula)
	"""
	Llamada general para asignar las tareas en los tags de Datos_Celula
	"""
	#---PARAMETROS--------------------------------------------------
	celulas = constantes.celulas
	tp = constantes.tag_provider
	#---------------------------------------------------------------
	
	#for celula in celulas:
		# Numero de maquinas por celula
	path = tp + "Celula" + celula
	total = len(system.tag.browse(path, {"name": "Maq_*"})) # Mira el numero de tags dentro de una carpeta, que empiecen por "Maq_"
	referencia = obtenerReferencia(celula)		# Obtener referencia
	for num in range(1, total + 1):
		print "===== CELULA " + str(celula) + " ======"
		print "----- Maquina " + str(num) + " ------"
		tipoMaq = obtenerTipoMaquina(celula, num)	# Mira el tipo de maquina para saber si es el plc general de automatica
		tareas = syncTareas(celula, referencia, tipoMaq, num)	# Establece todas las tareas en los tags Datos_Celula
		print tareas
	
	return True

def tareasPorMaquina(celula, referencia, maquina):
	# G_PILOT.tareasPorMaquina(celula, referencia, maquina)
	"""
	Devuelve todas las tareas (+ la ocurrencia y los elementos) que le corresponden hacer a una maquina segun referencia, celula y maquina
	"""
	#---PARAMETROS--------------------------------------------------
	database = constantes.Database_Tareas
	tablaTareas = constantes.LINEA + "_Tareas_Resumen"
	#---------------------------------------------------------------
	# Obtenemos tareas
	query = """
		SELECT
    		tarea, ocurrencia, elementos
    	FROM 
    		{0}
    	WHERE celula = ?
    	AND referencia = ?
    	AND maquina = ?
    	AND activo = 1
	""".format(tablaTareas)
	
	params = [str(celula), str(referencia), str(maquina)]
	
	data = system.db.runPrepQuery(query, params, database)
	return data

def inicializarTodosLosDatasetsPiezas(celula):
    # G_PILOT.inicializarTodosLosDatasetsPiezas(celula)
    """
    Inicializa los datasets de piezas para todas las máquinas de todas las celdas.
    Sigue la misma lógica que desviacionesMaquina() pero para inicializar datasets.
    """
    #---PARAMETROS--------------------------------------------------
    celulas = constantes.celulas
    tp = constantes.tag_provider
    logger = system.util.getLogger('Inicializar Datasets')
    #---------------------------------------------------------------
    
    logger.info("Iniciando inicialización de datasets de piezas")
    
    #for celula in celulas:
    print "============================ INICIALIZANDO CELULA " + str(celula) + " ==========================================="
    
    # Numero de maquinas por celula
    path = tp + "Celula" + celula
    total = len(system.tag.browse(path, {"name": "Maq_*"}))
    logger.info("Celula: " + str(celula) + " - Total máquinas: " + str(total))
    
    for num in range(1, total + 1):
    	# Inicializamos el contador de piezas de los cnc----------------------
    	plc_cnc = obtenerPLC_CNC(celula, num)
    	if plc_cnc == 1: # CNC
    		actualizarPiezasPorTurno(celula, num)
    	#---------------------------------------------------------------------
        # Inicializar dataset para esta máquina
        resultado = inicializarDatasetPiezas(celula, num)
        if resultado is not None:
            print "Máquina " + str(num) + " inicializada correctamente"
        else:
            print "Error inicializando máquina " + str(num)
    
    logger.info("Inicialización de todos los datasets completada")
    return True
    
def inicializarDatasetPiezas(celula, num):
	# G_PILOT.inicializarDatasetPiezas(celula, num)
    """
    Inicializa o sobreescribe el dataset de piezas para una máquina específica.
    Crea un dataset con fecha actual y piezas según el tipo de máquina.
    
    Args:
        celula: Número de celula
        num: Número de máquina
    
    Returns:
        Dataset actualizado o None si hay error
    """
    #---PARAMETROS--------------------------------------------------
    tp = constantes.tag_provider
    logger = system.util.getLogger('Dataset Piezas')
    #---------------------------------------------------------------
    
    try:
        # Verificar conexión
        conexion = obtenerConexion(celula, num)
        if conexion != 'Good':
            logger.warn("Conexión no válida para Celula " + str(celula) + " Maq " + str(num))
            return None
        
        # Obtener información de la máquina
        tipoMaq = obtenerTipoMaquina(celula, num)
        plc_cnc = obtenerPLC_CNC(celula, num)
        referencia = obtenerReferencia(celula)
        
        # Path del tag histórico
        pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
        
        # Definir estructura del dataset
        columnNames = ["fecha", "piezas"]
        
        # Obtener fecha actual
        fechaActual = system.date.now()
        
        # Obtener piezas según el tipo de máquina
        piezas = 0  # Valor por defecto
        
        if plc_cnc == 1:  # Máquinas tipo CNC
            pathTagContador = tp + "Celula" + str(celula) + "/Maq_" + str(num) + "/Datos_Dinamicos/ContadorPiezas/Pos1"
            piezasValue = system.tag.readBlocking([pathTagContador])[0].value
            if piezasValue is not None:
                piezas = piezasValue
            logger.info("Piezas CNC obtenidas: " + str(piezas))
            
        elif plc_cnc == 0:  # Máquinas tipo PLC
            if tipoMaq == "CELULA":
                piezas = piezasMaquinaTurno_Automatica(celula, referencia)
                logger.info("Piezas CELULA obtenidas: " + str(piezas))
                
            elif tipoMaq == "BROCHADORA" or tipoMaq == "AFEITADORA":
                pathPiezasActuales = tp + "Celula" + str(celula) + "/Maq_" + str(num) + "/Datos_Dinamicos/HtaVidaActual"
                piezasValue = system.tag.readBlocking([pathPiezasActuales])[0].value
                if piezasValue is not None:
                    piezas = piezasValue
                logger.info("Piezas " + tipoMaq + " obtenidas: " + str(piezas))
                
            else:
                # Para otros tipos PLC, asignar 0
                piezas = 0
                logger.info("Tipo PLC " + tipoMaq + " - Piezas asignadas: 0")
        
        # Crear dataset con una sola fila (sobreescribe si ya existía)
        data = [[fechaActual, piezas]]
        nuevoDataset = system.dataset.toDataSet(columnNames, data)
        
        # Escribir al tag (esto sobreescribe el dataset completo)
        system.tag.writeBlocking([pathTagHistorico], [nuevoDataset])
        
        logger.info("Dataset actualizado - Celula: " + str(celula) + ", Maq: " + str(num) + ", Tipo: " + tipoMaq + ", PLC_CNC: " + str(plc_cnc) + ", Piezas: " + str(piezas))
        print("Dataset inicializado - C: " + str(celula) + " / M: " + str(num) + " / (" + tipoMaq + "): " + str(piezas) + " piezas")
        
        return nuevoDataset
        
    except Exception as e:
        logger.error("Error inicializando dataset C" + str(celula) + "M" + str(num) + ": " + str(e))
        print("Error al inicializar dataset: " + str(e))
        return None
    
def actualizarPiezasPorTurno(celula, num):
	# G_PILOT.actualizarPiezasPorTurno(celula, num)
	"""
	Llamada general para actualizar el tag que se tiene para obtener piezas por turnos
	Ahora piezas se inicializa a 0 y cambiamos con el changeScript para los cnc
	"""
	#---PARAMETROS--------------------------------------------------
	tp = constantes.tag_provider
	#---------------------------------------------------------------
	try:
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/ContadorPiezas/Pos1"
		path = [path]
		
		cnc = obtenerPLC_CNC(celula, num)
		
		if cnc:
			piezas = 0
		else:
			valor = system.tag.readBlocking(path)
			piezas = valor[0].value
		
		
		tagPath = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Piezas_Turno"
		system.tag.writeBlocking([tagPath], [piezas])
	
		return True
	
	except Exception as e:
		system.util.getLogger("ScriptError").error("Tareas.Data.TagsMaquina.actualizarPiezasPorTurno(celula, num): {}".format(str(e)))
		return False
		
def piezasMaquinaTurno_Automatica(celula, referencia):
    # G_PILOT.piezasMaquinaTurno_Automatica(celula, referencia)
    """
	Esto esta hecho para el Gateway Timer Script y obtener el contador de las piezas de la celula automatica
	Tambien usado en: para tener el numero de piezas de una celula automatica para las desviaciones de la maquina
		Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt)
    """
    #---PARAMETROS Y CONSTANTES----------------------------------
    tp = constantes.tag_provider
    database = constantes.Database_Tareas_2
    tabla = "COEEproduction"
    ahora = system.date.now()

    #---Obtener hora actual--------------------------------------
    hora = system.date.getHour24(ahora)

    #---Calcular inicio de turno---------------------------------
    if 6 <= hora < 14:
        # Primer turno: 06:00 a 14:00
        inicioTurno = system.date.setTime(ahora, 6, 0, 0)
    elif 14 <= hora < 22:
        # Segundo turno: 14:00 a 22:00
        inicioTurno = system.date.setTime(ahora, 14, 0, 0)
    else:
        # Tercer turno: 22:00 a 06:00 (cruza medianoche)
        if hora >= 22:
            # estamos el mismo día desde las 22:00
            inicioTurno = system.date.setTime(ahora, 22, 0, 0)
        else:
            # estamos después de medianoche, el turno empezó ayer a las 22:00
            ayer = system.date.addDays(ahora, -1)
            inicioTurno = system.date.setTime(ayer, 22, 0, 0)
    
    #---Obtener AssetID------------------------------------------
    path = tp + "Variables/Datos_Celula/Celula" + str(celula) + "/AssetID"
    rutaTag = [path]
    AssetId = system.tag.readBlocking(rutaTag)[0].value

    #---Query para contar registros------------------------------
    query = """
        SELECT COUNT(*) 
        FROM {0}
        WHERE job = ?
        AND AssetID = ?
        AND TimeComplete >= ? 
        AND TimeComplete <= ?
    """.format(tabla)

    params = [str(referencia), str(AssetId), inicioTurno, ahora]

    try:
        data = system.db.runPrepQuery(query, params, database)
        cantidad = data[0][0]
        print "Cantidad de piezas en el turno actual:", cantidad
        return cantidad
    except Exception as e:
        print "Error en contarProduccionTurno():", str(e)
        return -1
        
def syncTareas(celula, referencia, maquina, num):
    # G_PILOT.syncTareas(celula, referencia, maquina, num)
    """
    Sincroniza el dataset de tareas en un tag con lo que devuelve la BD.
    - Solo hacemos la funcion si la referencia es la referencia con la que estamos trabajando.
    - Inserta nuevas tareas si no existen (contador = 0).
    - Elimina las tareas que ya no estén en BD.
    - Mantiene el contador y la fecha si la tarea ya existía.
    - Si la BD devuelve vacío, limpia el dataset.
    - Si el tag no existe, no hace nada.
    - Cuando se detecta una tarea totalmente nueva, se inserta en BD su inicio
    """
    logger = system.util.getLogger("SyncTareas")
    
    try:
        #---PARAMETROS--------------------------------------------------
        tp = constantes.tag_provider
        basePath = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num)
        tagPath = basePath + "/ContadorTareas"
        #----------------------------------------------------------------
        
        referencia_actual = obtenerReferencia(celula)
        # Insertamos si la referencia es la misma con la que estan trabajando
        if referencia == referencia_actual:
        
	        # 1. Obtener tareas desde BD
	        dataBD = tareasPorMaquina(celula, referencia, maquina)
	        
	        # Si la BD devuelve vacío → limpiar dataset
	        if not dataBD or len(dataBD) == 0:
	            headers = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
	            emptyDS = ds.toDataSet(headers, [])
	            try:
	                system.tag.writeBlocking([tagPath], [emptyDS])
	            except:
	                logger.warn("Celula %s Maq_%s: No se pudo escribir dataset vacío (tag inexistente?)." % (celula, num))
	                return False
	            return True
	        
	        # 2. Leer dataset actual del tag
	        try:
	            tareasTag = system.tag.readBlocking([tagPath])[0].value
	        except:
	            logger.warn("Celula %s Maq_%s: Tag %s no encontrado." % (celula, num, tagPath))
	            return False
	        
	        tareasTagDict = {}
	        if tareasTag is not None:
	            for i in range(tareasTag.getRowCount()):
	                tareasTagDict[tareasTag.getValueAt(i, "tarea")] = i
	        
	        # 3. Armar dataset nuevo en base a BD
	        newRows = []
	        for row in dataBD:
	            tarea = row["tarea"]
	            ocurrencia = row["ocurrencia"]
	            elementos = row["elementos"]
	            print "Se observa en " + str(maquina) + ", la tarea: " + str(tarea)
	            
	            if tarea in tareasTagDict:
	                idx = tareasTagDict[tarea]
	                fecha = tareasTag.getValueAt(idx, "fecha")
	                contador = tareasTag.getValueAt(idx, "contador")
	            else:
	                fecha = system.date.now()  # fecha de creación
	                contador = 0
	                try:
	                	# Aqui insertamos en la tabla de completados al inicio
	                	iniciarTareaBD(celula, referencia, maquina, tarea, elementos)
	                	print "Se inserta base de datos en " + str(maquina) + ", la tarea: " + str(tarea)
	                except Exception as e:
	                	logger.warn("Celula %s Maq_%s: No se pudo insertar nueva tarea en BD (%s)" % (celula, num, str(e)))
	            
	            newRows.append([fecha, tarea, ocurrencia, contador, elementos])
	        
	        headers = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
	        newDS = ds.toDataSet(headers, newRows)
	        
	        # 4. Escribir dataset sincronizado
	        system.tag.writeBlocking([tagPath], [newDS])
	        logger.info("Celula %s Maq_%s: Dataset sincronizado con BD." % (celula, num))
        
        return True
    
    except Exception as e:
        logger.error("Celula %s Maq_%s: Error en syncTareas - %s" % (celula, num, str(e)))
        return False
    
def iniciarTareaBD(celula, referencia, maquina, tarea, elemento):
	# G_PILOT.iniciarTareaBD(celula, referencia, maquina, tarea, elemento)
	"""
	Inserta en Base de Datos los datos el inicio de una tarea
	InicioFin = 0 significa que es el inicio
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	database = constantes.Database_Tareas
	tablaCompletado = constantes.LINEA + "_Completado"
	
	path = tp + "Variables/Inicio/idUsuario"
	path = [path]
	
	data = system.tag.readBlocking(path)
	
	idUsuario = data[0].value
	
	#---LLAMADA A LA QUERY Y SUS PARAMETROS------------------------
	query = """
	INSERT INTO {0} (celula, referencia, maquina, tarea, elemento, fecha, manual, idUsuario, InicioFin)
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	""".format(tablaCompletado)
	
	# Valores a insertar
	params = [
	    celula,       		# celula
	    referencia,     	# referencia
	    maquina,      		# maquina
	    tarea,        		# tarea
	    elemento, 			# elemento
	    system.date.now(),	# fecha
	    0,             		# manual
	    idUsuario,          # idUsuario
	    0					# InicioFin
	]
	
	system.db.runPrepUpdate(query, params, database)
	
	return True
	
def obtenerReferencia(celula):
	# G_PILOT.obtenerReferencia(celula)
	"""
	Obtener la referencia de la célula segun un tag.
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_1/Datos_Cuasiconstantes/Referencia"
		path = [path]
		
		datos = system.tag.readBlocking(path)
		referencia = datos[0].value
		referencia = referencia.strip()
		return referencia
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerReferencia: {}".format(str(e)))
		return 'NULL'
		
def obtenerConexion(celula, num):
	# G_PILOT.obtenerConexion(celula, num)
	"""
	Obtener el estado de la conexion de la maquina segun un tag.
	Las opciones son 'Good' or 'Bad'
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/Maq_Conexion"
		path = [path]
		
		data = system.tag.readBlocking(path)
		
		if data[0].value:
			return 'Good'
		else:
			return 'Bad'
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerConexion: {}".format(str(e)))
		return 'Bad'
	
def obtenerTipoMaquina(celula, num):
	# G_PILOT.obtenerTipoMaquina(celula, num)
	"""
	Obtener el tipo de Maquina consultando directamente al tag
	Comprueba si es Celula Automatica o Bin Picking
	"""
	try:
		tp = constantes.tag_provider
		
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Constantes/Tipo"
		path = [path]
		
		data = system.tag.readBlocking(path)
		tipo = data[0].value
		
		if tipo is None:
			# No leemos datos asi que leemos del auxiliar
			path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) +"/Tipo"
			path = [path]
			
			data = system.tag.readBlocking(path)
			tipo = data[0].value
			
			tipoMaq = tipo.upper()
			return tipoMaq
		else:
			tipoMaq = tipo.upper()
			if tipoMaq == "CELULA_AUTOMATICA":
				tipoMaq = "CELULA"
			
			path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Constantes/Situacion"
			path = [path]
			
			# Comprobamos si es Bin Picking por la situacion
			sit = system.tag.readBlocking(path)
			situacion = sit[0].value
			pick = situacion[-5:-1]
			
			if tipoMaq == "CELULA" and pick == "Pick":
				tipoMaq = "BIN PICKING"
			
			return tipoMaq
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerTipoMaquina: {}".format(str(e)))
		return 'NULL'
		
def obtenerPLC_CNC(celula, num):
	# G_PILOT.obtenerPLC_CNC(celula, num)
	"""
	Obtener si es CNC o PLC
	0: PLC
	1: CNC
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/ContadorPiezas"
		
		if system.tag.exists(path):
			return 1
		else:
			return 0
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerPLCoCNC: {}".format(str(e)))
		return 'NULL'
	