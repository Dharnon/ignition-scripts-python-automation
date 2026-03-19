import system.dataset as ds
import system.date

def tareasPorMaquinaGeneral(celula):
	# Tareas.Data.TagsMaquina.tareasPorMaquinaGeneral(celula)
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
	referencia = Sinoptico.Data.General.obtenerReferencia(celula)		# Obtener referencia
	for num in range(1, total + 1):
		print "===== CELULA " + str(celula) + " ======"
		print "----- Maquina " + str(num) + " ------"
		tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)	# Mira el tipo de maquina para saber si es el plc general de automatica
		tareas = Tareas.Data.TagsMaquina.syncTareas(celula, referencia, tipoMaq, num)	# Establece todas las tareas en los tags Datos_Celula
		print tareas
	
	return True
			
def tareasPorMaquina(celula, referencia, maquina):
	# Tareas.Data.TagsMaquina.tareasPorMaquina(celula, referencia, maquina)
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
	

def syncTareas(celula, referencia, maquina, num):
    # Tareas.Data.TagsMaquina.syncTareas(celula, referencia, maquina, num)
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
        
        referencia_actual = Sinoptico.Data.General.obtenerReferencia(celula)
        # Insertamos si la referencia es la misma con la que estan trabajando
        if referencia == referencia_actual:
        
	        # 1. Obtener tareas desde BD
	        dataBD = Tareas.Data.TagsMaquina.tareasPorMaquina(celula, referencia, maquina)
	        
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
	                	Tareas.Data.General.iniciarTareaBD(celula, referencia, maquina, tarea, elementos)
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

def piezasMaquinaTurno(idMaquina):
    # Tareas.Data.TagsMaquina.piezasMaquinaTurno(idMaquina)
    """
    Esto viene por el Gateway Timer Script
    Devuelve el número de piezas registradas para una máquina en el turno actual.
    Maneja errores para que siempre devuelva un número entero seguro.
    Hecho para maquinas tipo PLC
    """
    #---PARAMETROS---------------------------
    database = constantes.Database_Tareas_2
    #-----------------------------------------

    try:
        # --- Obtener IdMaquina desde BD ---
        query = "SELECT IdMaquina FROM CMaquinas WHERE Maquina = ?"
        data = system.db.runPrepQuery(query, [idMaquina], database)
        if not data or len(data) == 0:
            return 0
        bdIdMaq = data[0][0]

        # --- Determinar turno automáticamente ---
        ahora = system.date.now()
        hora = system.date.getHour(ahora)
        if 6 <= hora < 14:
            turno = 1
        elif 14 <= hora < 22:
            turno = 2
        else:
            turno = 3

        # --- Calcular fechas de turno ---
        fecha_hoy = system.date.midnight(ahora)
        if turno == 1:
            inicio = system.date.addHours(fecha_hoy, 6)
            fin    = system.date.addHours(fecha_hoy, 14)
        elif turno == 2:
            inicio = system.date.addHours(fecha_hoy, 14)
            fin    = system.date.addHours(fecha_hoy, 22)
        elif turno == 3:
            inicio = system.date.addHours(fecha_hoy, 22)
            fin    = system.date.addHours(system.date.addDays(fecha_hoy, 1), 6)
        else:
            return 0

        # --- Consultar registros de piezas ---
        query = """
            SELECT Fecha, Valor
            FROM CDatosMaquina
            WHERE IdTipoDatoMaquina = 3
              AND IdMaquina = ?
              AND Fecha >= ?
              AND Fecha < ?
            ORDER BY Fecha DESC
        """
        datos = system.db.runPrepQuery(query, [bdIdMaq, inicio, fin], database)
        if not datos:
            return 0

        # --- Contar piezas (pareja 1 -> 0) ---
        piezas = 0
        for i in range(len(datos)-1):
            try:
                if datos[i]['Valor'] == '1' and datos[i+1]['Valor'] == '0':
                    piezas += 1
            except Exception:
                # Ignorar errores en registros individuales
                continue

        return piezas

    except Exception:
        # Cualquier error inesperado devuelve 0
        return 0

def piezasMaquinaTurno_Automatica(celula, referencia):
    # Tareas.Data.TagsMaquina.piezasMaquinaTurno_Automatica(celula, referencia)
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


def usaContadorCelula(nombreTarea):
	# Tareas.Data.TagsMaquina.usaContadorCelula(nombreTarea)
	"""
	Devuelve True si la tarea debe avanzar con el contador de celula automatica.
	Regla de negocio actual:
	- Todas las tareas recurrentes usan contador de celula,
	- excepto los cambios de herramienta (CH), que siguen usando su logica de vida util.
	"""
	if nombreTarea is None:
		return False
	# CH sigue siendo excepcion de contador
	return not str(nombreTarea).startswith("CH")


def completarTarea(celula, referencia, num, nombreTarea):
	# Tareas.Data.TagsMaquina.completarTarea(celula, referencia, num, nombreTarea)
	"""
	Completa una tarea en el dataset `ContadorTareas` y devuelve el estado del contador.

	Nuevo modelo:
	- Para tareas piece-dependent (no CH):
	  - `contador` se interpreta como baseline del contador de celula.
	  - Se compara contra `piezasMaquinaTurno_Automatica(celula, referencia)`.
	- Para tareas CH:
	  - Se mantiene el comportamiento anterior (contador local por maquina).

	Retorno:
	- 0: completada "antes de tiempo" (delta < ocurrencia) → se reprograma desde ahora.
	- contador (1..ocurrencia-1): piezas ya consumidas hacia el siguiente ciclo.
	- -1: delta >= ocurrencia → se ha sobrepasado el ciclo, descargar/reprogramar YA.
	- -2: error.
	"""
	tp = constantes.tag_provider

	try:
		# Ruta al dataset de contadores por maquina
		rutaTag = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/ContadorTareas"

		dsOld = system.tag.readBlocking([rutaTag])[0].value
		if dsOld is None or dsOld.getRowCount() == 0:
			print("Error: No hay dataset en la ruta especificada")
			return -2

		expectedCols = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
		colNames = list(dsOld.getColumnNames())
		for col in expectedCols:
			if col not in colNames:
				print("Error: Dataset corrupto - falta columna: " + col)
				return -2

		usaCelula = usaContadorCelula(nombreTarea)

		# Si usa contador de celula, obtenemos el valor actual robusto
		if usaCelula:
			contadorCelula = Tareas.Data.TagsMaquina.piezasMaquinaTurno_Automatica(celula, referencia)
			if contadorCelula < 0:
				print("Error al obtener piezas de celula automatica")
				return -2
		else:
			contadorCelula = None

		tareaEncontrada = False
		newRows = []
		resultado = -1

		for i in range(dsOld.getRowCount()):
			try:
				fecha = dsOld.getValueAt(i, "fecha")
				tarea = dsOld.getValueAt(i, "tarea")
				ocurrencia = dsOld.getValueAt(i, "ocurrencia")
				contador = dsOld.getValueAt(i, "contador")
				elementos = dsOld.getValueAt(i, "elementos")

				if tarea == nombreTarea:
					tareaEncontrada = True

					if ocurrencia is None or ocurrencia <= 0:
						print("Error: Ocurrencia inválida para la tarea: " + nombreTarea)
						return -2

					if usaCelula:
						# Baseline almacenado en contador, valor actual de celula en contadorCelula
						if contador is None:
							contador = 0
						delta = int(contadorCelula) - int(contador)
						print "Delta piezas celula para tarea", nombreTarea, ":", delta

						if delta < 0:
							# contador de celula retrocedio (reinicio de turno, etc.) → reset baseline
							delta = 0

						if delta < ocurrencia:
							# No se ha llegado al ciclo completo
							resultado = delta if delta > 0 else 0
						else:
							# Hemos alcanzado o sobrepasado el ciclo
							resultado = -1

						# Actualizamos baseline al valor actual de celula para el siguiente ciclo
						contador = int(contadorCelula)
					else:
						# Comportamiento antiguo para CH: contador local por maquina
						contador = contador - ocurrencia
						contador = int(contador)
						print contador

						if contador < 0:
							contador = 0
							resultado = 0
						elif contador >= 0 and contador < ocurrencia:
							resultado = contador
						else:
							resultado = -1

				newRows.append([fecha, tarea, ocurrencia, contador, elementos])

			except Exception as e:
				print("Error procesando fila " + str(i) + ": " + str(e))
				continue

		if not tareaEncontrada:
			print("Error: No se encontró la tarea especificada: " + nombreTarea)
			return -2

		if len(newRows) == 0:
			print("Error: No hay datos válidos en el dataset")
			return -2

		headers = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
		dsNew = ds.toDataSet(headers, newRows)
		writeResult = system.tag.writeBlocking([rutaTag], [dsNew])

		if not writeResult[0].isGood():
			print("Error: No se pudo escribir el dataset actualizado")
			return -2

		print("Dataset actualizado correctamente")
		return resultado

	except Exception as e:
		print("Error general en completarTarea: " + str(e))
		return -2
    
def actualizarPiezasPorTurno(celula, num):
	# Tareas.Data.TagsMaquina.actualizarPiezasPorTurno(celula, num)
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
		
		cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num)
		
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
		
def inicializarDatasetPiezas(celula, num):
	# Tareas.Data.TagsMaquina.inicializarDatasetPiezas(celula, num)
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
        conexion = Sinoptico.Data.General.obtenerConexion(celula, num)
        if conexion != 'Good':
            logger.warn("Conexión no válida para Celula " + str(celula) + " Maq " + str(num))
            return None
        
        # Obtener información de la máquina
        tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
        plc_cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num)
        referencia = Sinoptico.Data.General.obtenerReferencia(celula)
        
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
                piezas = Tareas.Data.TagsMaquina.piezasMaquinaTurno_Automatica(celula, referencia)
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


def inicializarTodosLosDatasetsPiezas(celula):
    # Tareas.Data.TagsMaquina.inicializarTodosLosDatasetsPiezas(celula)
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
    	plc_cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num)
    	if plc_cnc == 1: # CNC
    		Tareas.Data.TagsMaquina.actualizarPiezasPorTurno(celula, num)
    	#---------------------------------------------------------------------
        # Inicializar dataset para esta máquina
        resultado = Tareas.Data.TagsMaquina.inicializarDatasetPiezas(celula, num)
        if resultado is not None:
            print "Máquina " + str(num) + " inicializada correctamente"
        else:
            print "Error inicializando máquina " + str(num)
    
    logger.info("Inicialización de todos los datasets completada")
    return True