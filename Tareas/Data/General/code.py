def obtenerRitmoProd(celula, referencia, maquina):
	# Tareas.Data.General.obtenerRitmoProd(celula, referencia, maquina)
	"""
	Obtener el ritmo de produccion teórico según maquina y referencia.
	Se hace una query  la tabla intermedia del excel y se multiplica ocurrencia * min
	Se filtra por 'Tiempo de máquina' para obtener el tiempo que queremos
	"""
	#---PARAMETROS--------
	database = constantes.Database_Tareas
	tablaTareas = constantes.LINEA + "_Tareas"
	# Obtenemos ritmo de produccion
	try:
		query = """
			SELECT
	    		ISNULL(ocurrencia, ocurrenciaStd) * 1.0 * ISNULL(min, min_std) AS valor_ocurrencia_por_min
	    	FROM 
	    		{0}
	    	WHERE
	    	tarea LIKE 'Tiempo de m%'
	    	AND celula = ?
	    	AND referencia = ?
	    	AND maquina = ?
		""".format(tablaTareas)
		
		params = [str(celula), str(referencia), str(maquina)]
		
		data = system.db.runPrepQuery(query, params, database)
		return data[0][0]
	except Exception as e:
		system.util.getLogger("Tareas.Data.General.obtenerRitmoProd(celula, referencia, maquina)").error("Error: " + str(e))
		return 1.0

def obtenerOcurrencia(celula, referencia, maquina, tarea):
	# Tareas.Data.General.obtenerOcurrencia(celula, referencia, maquina, tarea)
	"""
	Obtener la ocurrencia según CELULA, maquina, referencia y tarea.
	Se hace una query  la tabla resumen final del excel
	"""
	#---PARAMETROS--------
	database = constantes.Database_Tareas
	tablaTareas = constantes.LINEA + "_Tareas_Resumen"
	# Obtenemos ritmo de produccion
	query = """
	SELECT tarea, ocurrencia
	FROM {0}
	WHERE celula = ?
	AND referencia = ?
	AND maquina = ?
	AND activo = 1
	""".format(tablaTareas)
	
	params = [str(celula), str(referencia), str(maquina)]
	
	data = system.db.runPrepQuery(query, params, database)
	
	# --- Filtrar en Python por tarea que empiece igual ---
	for row in data:
		tareaBD = row["tarea"]
		if tareaBD.startswith(tarea):
			return row["ocurrencia"]
	
	# Si no se encontró ninguna coincidencia
	raise ValueError("No se encontró ninguna tarea que comience con: '{}'".format(tarea))
	
def crearNuevasTareas(tarea, celula, maquina, elemento, rpt, ocurrencia, referencia):
    # Tareas.Data.General.crearNuevasTareas(tarea, celula, maquina, elemento, rpt, ocurrencia, referencia)
    """
    Script genérico para añadir nuevas tareas al dataset de tareas.
    Primero inserta en base de datos,
    luego actualiza el dataset del tag si la referencia es la actual.
    """

    # --- PARÁMETROS --------------------------------------------------
    tablaTareas = constantes.LINEA + "_Tareas"
    database = constantes.Database_Tareas
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
    # ----------------------------------------------------------------

    # --- INSERTAR EN BASE DE DATOS -----------------------------------
    query = """
    INSERT INTO {tabla} (
        referencia,
        tarea,
        maquina,
        ocurrenciaStd,
        ocurrencia,
        turno,
        elemento,
        prioridad,
        celula,
        min_std,
        min
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """.format(tabla=tablaTareas)

    params = [
        referencia,
        tarea,
        maquina,
        ocurrencia,
        None,
        None,
        elemento,
        1,
        celula,
        0,
        None
    ]

    system.db.runPrepUpdate(query, params, database)
    Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)
    # ----------------------------------------------------------------

    # --- INSERTAR EN EL TAG DATASET ---------------------------------
    referencia_actual = Sinoptico.Data.General.obtenerReferencia(celula)

    if referencia == referencia_actual:
        ds = system.tag.readBlocking([tagPath])[0].value

        # Asegurarse de que sea un dataset válido
        if ds is None or not hasattr(ds, "getRowCount"):
            headers = ["tarea", "cuando", "celula", "maquina", "elemento", "completado"]
            ds = system.dataset.toDataSet(headers, [])

        headers = list(ds.getColumnNames())
        col_tarea = headers.index("tarea")
        col_cuando = headers.index("cuando")
        col_celula = headers.index("celula")
        col_maquina = headers.index("maquina")
        col_elemento = headers.index("elemento")
        col_completado = headers.index("completado")

        filas = []
        filas_encontradas = 0

        # Recorrer dataset actual
        for row in range(ds.getRowCount()):
            tarea_existente = ds.getValueAt(row, col_tarea)
            celula_existente = ds.getValueAt(row, col_celula)
            maquina_existente = ds.getValueAt(row, col_maquina)
            elemento_actual = ds.getValueAt(row, col_elemento)

            # Si coincide, actualizar elemento
            if tarea_existente == tarea and celula_existente == celula and maquina_existente == maquina:
                if elemento_actual:
                    elemento_actual = elemento_actual + " | " + elemento
                else:
                    elemento_actual = elemento
                fila = [ds.getValueAt(row, c) for c in range(ds.getColumnCount())]
                fila[col_elemento] = elemento_actual
                filas.append(fila)
                filas_encontradas += 1
            else:
                filas.append([ds.getValueAt(row, c) for c in range(ds.getColumnCount())])
                
                
        # Si no hay coincidencias, crear nuevas tareas
        if filas_encontradas == 0:
            intervalo = rpt * float(ocurrencia)  # minutos
            ahora = system.date.now()
            fin = system.date.addHours(ahora, 8)
		    
            siguiente = system.date.addMinutes(ahora, int(intervalo))
		    
            # SIEMPRE añadir la primera tarea (sin importar si está fuera de las 8 horas)
            nuevaFila = [tarea, siguiente, celula, maquina, elemento, 0]
            filas.append(nuevaFila)
		    
            # Calcular la siguiente después de la primera
            siguiente = system.date.addMinutes(siguiente, int(intervalo))
		    
            # Añadir el resto de tareas solo si están dentro del límite de 8 horas
            while siguiente <= fin:
                nuevaFila = [tarea, siguiente, celula, maquina, elemento, 0]
                filas.append(nuevaFila)
                siguiente = system.date.addMinutes(siguiente, int(intervalo))

        # Crear y escribir el nuevo dataset
        nuevoDataset = system.dataset.toDataSet(headers, filas)
        system.tag.writeBlocking([tagPath], [nuevoDataset])

    return True
 
def crearNuevasTareas_v0(tarea, celula, maquina, elemento, rpt, ocurrencia, referencia):
    # Tareas.Data.General.crearNuevasTareas(tarea, celula, maquina, elemento, rpt, ocurrencia, referencia)
    """
    Script genérico para añadir nuevas tareas al dataset de tareas.
    Primero inserta en base de datos,
    luego actualiza el dataset del tag si la referencia es la actual.
    """

    # --- PARÁMETROS --------------------------------------------------
    tablaTareas = constantes.LINEA + "_Tareas"
    database = constantes.Database_Tareas
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
    # ----------------------------------------------------------------

    # --- INSERTAR EN BASE DE DATOS -----------------------------------
    query = """
    INSERT INTO {tabla} (
        referencia,
        tarea,
        maquina,
        ocurrenciaStd,
        ocurrencia,
        turno,
        elemento,
        prioridad,
        celula,
        min_std,
        min
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """.format(tabla=tablaTareas)

    params = [
        referencia,
        tarea,
        maquina,
        ocurrencia,
        None,
        None,
        elemento,
        1,
        celula,
        0,
        None
    ]

    system.db.runPrepUpdate(query, params, database)
    Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)
    # ----------------------------------------------------------------

    # --- INSERTAR EN EL TAG DATASET ---------------------------------
    referencia_actual = Sinoptico.Data.General.obtenerReferencia(celula)

    if referencia == referencia_actual:
        ds = system.tag.readBlocking([tagPath])[0].value

        # Asegurarse de que sea un dataset válido
        if ds is None or not hasattr(ds, "getRowCount"):
            headers = ["tarea", "cuando", "celula", "maquina", "elemento", "completado"]
            ds = system.dataset.toDataSet(headers, [])

        headers = list(ds.getColumnNames())
        col_tarea = headers.index("tarea")
        col_cuando = headers.index("cuando")
        col_celula = headers.index("celula")
        col_maquina = headers.index("maquina")
        col_elemento = headers.index("elemento")
        col_completado = headers.index("completado")

        filas = []
        filas_encontradas = 0

        # Recorrer dataset actual
        for row in range(ds.getRowCount()):
            tarea_existente = ds.getValueAt(row, col_tarea)
            celula_existente = ds.getValueAt(row, col_celula)
            maquina_existente = ds.getValueAt(row, col_maquina)
            elemento_actual = ds.getValueAt(row, col_elemento)

            # Si coincide, actualizar elemento
            if tarea_existente == tarea and celula_existente == celula and maquina_existente == maquina:
                if elemento_actual:
                    elemento_actual = elemento_actual + " | " + elemento
                else:
                    elemento_actual = elemento
                fila = [ds.getValueAt(row, c) for c in range(ds.getColumnCount())]
                fila[col_elemento] = elemento_actual
                filas.append(fila)
                filas_encontradas += 1
            else:
                filas.append([ds.getValueAt(row, c) for c in range(ds.getColumnCount())])

        # Si no hay coincidencias, crear nuevas tareas
        if filas_encontradas == 0:
            intervalo = rpt * float(ocurrencia)  # minutos
            ahora = system.date.now()
            fin = system.date.addHours(ahora, 8)

            siguiente = system.date.addMinutes(ahora, int(intervalo))
            while siguiente <= fin:
                nuevaFila = [tarea, siguiente, celula, maquina, elemento, 0]
                filas.append(nuevaFila)
                siguiente = system.date.addMinutes(siguiente, int(intervalo))

        # Crear y escribir el nuevo dataset
        nuevoDataset = system.dataset.toDataSet(headers, filas)
        system.tag.writeBlocking([tagPath], [nuevoDataset])

    return True
	 

def modificarTiemposMaquinas(CelulaObjetivo, MaquinaObjetivo, incremento):
	# Tareas.Data.General.modificarTiemposMaquinas(CelulaObjetivo, MaquinaObjetivo, incremento)
	"""
	Script generico para modificar el tiempo de desfase de una maquina 
	Por ejemplo:
	CelulaObjetivo = "142A"
	MaquinaObjetivo = "TORNO"
	incremento = 10
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	logger = system.util.getLogger('Desviacion Maquina')
	logger.info("Modificar Tiempo Maquina: " + str(MaquinaObjetivo) + " en la celula " + str(CelulaObjetivo) + " un incremento de: " + str(incremento))
	
	filaEncontrada = False
	
	#---Transformamos a minutos y segundos-------------------------
	minutos = int(incremento)
	segundos = int(round((incremento - minutos) * 60))
	logger.info("Incremento de " + str(minutos) + " minutos y " + str(segundos) + " segundos")
	
	#---Leer el dataset y crear array para poder modificar---------
	lista = system.tag.readBlocking([path])
	dataset = lista[0].value
	
	columnNames = list(dataset.getColumnNames())
	rowCount = dataset.getRowCount()
	
	rows = []
	for rowIndex in range(rowCount):
		rowData = []
		for col in columnNames:
			rowData.append(dataset.getValueAt(rowIndex, col))
		rows.append(rowData)
	
	#---MODIFICAR FILA SEGÚN CONDICIÓN----------------------------
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	colTarea = columnNames.index("tarea")
	
	#---Modificar la tabla-----------------------------------------
	for i in range(rowCount):
		if rows[i][colCelula] == CelulaObjetivo and rows[i][colMaquina] == MaquinaObjetivo:
			#---Añadir incremento
			if rows[i][colCompletado] == 0: # Si no se ha completado la tarea hace el incremento
				valorActual = rows[i][colCuando]
				valorActual = system.date.addMinutes(valorActual, minutos)
				valorActual = system.date.addSeconds(valorActual, segundos)
				rows[i][colCuando] = valorActual
				print rows[i]
			filaEncontrada = True
	
	if not filaEncontrada:
		print("No se encontró ninguna fila con los objetivos establecidos.")
	
	#---Crear y escribir el nuevo dataset---------------------------
	newDataset = system.dataset.toDataSet(columnNames, rows)
	system.tag.writeBlocking([path], [newDataset])
	return True

def completarTarea_v0(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo):
	# Tareas.Data.General.completarTarea_v0(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo)
	"""
	Script genérico para marcar como completada la tarea más próxima
	que coincida con los parámetros dados y no esté completada aún.
	Además, actualiza el campo 'cuando' con la hora actual.
	Por ejemplo:
	CelulaObjetivo = "142A"
	MaquinaObjetivo = "TORNO"
	TareaObjetivo = "CH"
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	filaEncontrada = False
	now = system.date.now()
	
	#---Leer el dataset y crear array para poder modificar---------
	lista = system.tag.readBlocking([path])
	dataset = lista[0].value
	
	columnNames = list(dataset.getColumnNames())
	rowCount = dataset.getRowCount()
	
	rows = []
	for rowIndex in range(rowCount):
		rowData = []
		for col in columnNames:
			rowData.append(dataset.getValueAt(rowIndex, col))
		rows.append(rowData)
	
	#---MODIFICAR FILA SEGÚN CONDICIÓN----------------------------
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	colTarea = columnNames.index("tarea")
	
	#---Buscar la fila más próxima que coincida---------------------
	filaObjetivoIndex = -1
	fechaMasProxima = None

	for i in range(rowCount):
		celula = dataset.getValueAt(i, colCelula)
		maquina = dataset.getValueAt(i, colMaquina)
		tarea = dataset.getValueAt(i, colTarea)
		completado = dataset.getValueAt(i, colCompletado)
		fecha = dataset.getValueAt(i, colCuando)

		if (
			celula == CelulaObjetivo and
			maquina == MaquinaObjetivo and
			completado == 0 and
			tarea.startswith(TareaObjetivo) # Aqui indica que tiene que empezar con ese nombre. Por ejemplo "CH" = "CH 1/400"
		):
			if fechaMasProxima is None or fecha < fechaMasProxima:
				fechaMasProxima = fecha
				filaObjetivoIndex = i

	#---Si se encontró, modificar la fila correspondiente-----------
	if filaObjetivoIndex != -1:
		rows = []
		for i in range(rowCount):
			row = []
			for col in columnNames:
				valor = dataset.getValueAt(i, col)
				# Marcar como completado solo la fila objetivo
				if i == filaObjetivoIndex:
					if col == "completado":
						valor = 1 # Marcamos tarea como completado
					elif col == "cuando":
						valor = now # Asignamos fecha y hora de completado
				row.append(valor)
			rows.append(row)
		
		newDataset = system.dataset.toDataSet(columnNames, rows)
		system.tag.writeBlocking([path], [newDataset])
		return True
	else:
		print("No se encontró ninguna tarea pendiente con esos criterios.")
		return False
		
def completarTarea(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo):
    # Tareas.Data.General.completarTarea(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo)
    """
    Script genérico para marcar como completada la tarea más próxima
    que coincida con los parámetros dados y no esté completada aún.
    Además:
    - Actualiza el campo 'cuando' con la hora actual.
    - Duplica la fila completada y genera una nueva tarea con fecha dentro de 8 horas.
	CelulaObjetivo = "142A"
	MaquinaObjetivo = "TORNO"
	TareaObjetivo = "CH"
    """

    #---PARAMETROS Y CONSTANTES------------------------------------
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    path = tp + "Dataset/Tareas_Celula" + celulaLinea

    now = system.date.now()

    #---Leer el dataset y crear array para poder modificar---------
    lista = system.tag.readBlocking([path])
    dataset = lista[0].value

    columnNames = list(dataset.getColumnNames())
    rowCount = dataset.getRowCount()

    rows = []
    for rowIndex in range(rowCount):
        rowData = []
        for col in columnNames:
            rowData.append(dataset.getValueAt(rowIndex, col))
        rows.append(rowData)

    #---Indices de columnas----------------------------------------
    colCelula = columnNames.index("celula")
    colMaquina = columnNames.index("maquina")
    colCuando = columnNames.index("cuando")
    colCompletado = columnNames.index("completado")
    colTarea = columnNames.index("tarea")

    #---Buscar la fila más próxima que coincida--------------------
    filaObjetivoIndex = -1
    fechaMasProxima = None

    for i in range(rowCount):
        celula = dataset.getValueAt(i, colCelula)
        maquina = dataset.getValueAt(i, colMaquina)
        tarea = dataset.getValueAt(i, colTarea)
        completado = dataset.getValueAt(i, colCompletado)
        fecha = dataset.getValueAt(i, colCuando)

        if (
            celula == CelulaObjetivo and
            maquina == MaquinaObjetivo and
            completado == 0 and
            tarea.startswith(TareaObjetivo) # Aqui indica que tiene que empezar con ese nombre. Por ejemplo "CH" = "CH 1/400"
        ):
            if fechaMasProxima is None or fecha < fechaMasProxima:
                fechaMasProxima = fecha
                filaObjetivoIndex = i

    #---Si se encontró, modificar la fila correspondiente----------
    if filaObjetivoIndex != -1:
        #---Marcar fila como completada----------------------------
        for col in range(len(columnNames)):
            if columnNames[col] == "completado":
                rows[filaObjetivoIndex][col] = 1   # Marcamos tarea como completada
            elif columnNames[col] == "cuando":
                rows[filaObjetivoIndex][col] = now # Fecha y hora actual de completado

        #---Crear nueva fila duplicada-----------------------------
        nuevaFila = list(rows[filaObjetivoIndex]) # Copiamos fila completada
        nuevaFila[colCompletado] = 0              # La nueva tarea está pendiente
        nuevaFila[colCuando] = system.date.addHours(now, 8) # Se reprograma dentro de 8 horas
        rows.append(nuevaFila)

        #---Depuración: mostrar nueva fila generada----------------
        print "Nueva tarea generada a +8h:", nuevaFila

        #---Crear y escribir el nuevo dataset----------------------
        newDataset = system.dataset.toDataSet(columnNames, rows)
        system.tag.writeBlocking([path], [newDataset])
        print "Tarea completada y nueva tarea programada dentro de 8 horas."
        return True
    else:
        print("No se encontró ninguna tarea pendiente con esos criterios.")
        return False
 


def completarTareaConFecha(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo, Fecha):
	# Tareas.Data.General.completarTareaConFecha(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo, Fecha)
	"""
	Es una copia de completarTarea pero con la posibilidad de indicar a que hora se ha completado la tarea
	Script genérico para marcar como completada la tarea más próxima
	que coincida con los parámetros dados y no esté completada aún.
	Por ejemplo:
	CelulaObjetivo = "142A"
	MaquinaObjetivo = "TORNO"
	TareaObjetivo = "CH"
	Fecha = formato datetime
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	filaEncontrada = False
	
	#---Leer el dataset y crear array para poder modificar---------
	lista = system.tag.readBlocking([path])
	dataset = lista[0].value
	
	columnNames = list(dataset.getColumnNames())
	rowCount = dataset.getRowCount()
	
	rows = []
	for rowIndex in range(rowCount):
		rowData = []
		for col in columnNames:
			rowData.append(dataset.getValueAt(rowIndex, col))
		rows.append(rowData)
	
	#---MODIFICAR FILA SEGÚN CONDICIÓN----------------------------
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	colTarea = columnNames.index("tarea")
	
	#---Buscar la fila más próxima que coincida---------------------
	filaObjetivoIndex = -1
	fechaMasProxima = None

	for i in range(rowCount):
		celula = dataset.getValueAt(i, colCelula)
		maquina = dataset.getValueAt(i, colMaquina)
		tarea = dataset.getValueAt(i, colTarea)
		completado = dataset.getValueAt(i, colCompletado)
		fecha = dataset.getValueAt(i, colCuando)

		if (
			celula == CelulaObjetivo and
			maquina == MaquinaObjetivo and
			completado == 0 and
			tarea.startswith(TareaObjetivo) # Aqui indica que tiene que empezar con ese nombre. Por ejemplo "CH" = "CH 1/400"
		):
			if fechaMasProxima is None or fecha < fechaMasProxima:
				fechaMasProxima = fecha
				filaObjetivoIndex = i

	#---Si se encontró, modificar la fila correspondiente-----------
	if filaObjetivoIndex != -1:
		rows = []
		for i in range(rowCount):
			row = []
			for col in columnNames:
				valor = dataset.getValueAt(i, col)
				# Marcar como completado solo la fila objetivo
				if i == filaObjetivoIndex:
					if col == "completado":
						valor = 1 # Marcamos tarea como completado
					elif col == "cuando":
						valor = Fecha # Asignamos fecha y hora de completado
				row.append(valor)
			rows.append(row)
		
		newDataset = system.dataset.toDataSet(columnNames, rows)
		system.tag.writeBlocking([path], [newDataset])
		return True
	else:
		print("No se encontró ninguna tarea pendiente con esos criterios.")
		return False

def completarTareaBD_v0(celula, referencia, maquina, tarea, elemento, manual):
	# Tareas.Data.General.completarTareaBD_v0(celula, referencia, maquina, tarea, elemento, manual)
	"""
	Inserta en Base de Datos los datos de la ultima tarea completada
	manual = 0 significa que ha sido automatico; manual = 1 significa que ha sido manual
	InicioFin = 1 siginifica que se ha completado
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
	    manual,             # manual
	    idUsuario,          # idUsuario
	    1					# InicioFin
	]
	
	system.db.runPrepUpdate(query, params, database)
	
	return True
	
def completarTareaBD(celula, referencia, maquina, tarea, elemento, manual):
	# Tareas.Data.General.completarTareaBD(celula, referencia, maquina, tarea, elemento, manual)
	"""
	Inserta en Base de Datos los datos de la ultima tarea completada
	Primero miramos el id de Tareas Resumen para relacionar tablas
	manual = 0 significa que ha sido automatico; manual = 1 significa que ha sido manual
	InicioFin = 1 siginifica que se ha completado
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	database = constantes.Database_Tareas
	tablaCompletado = constantes.LINEA + "_Completados"
	tablaTareasResumen = constantes.LINEA + "_Tareas_Resumen"
	
	path = tp + "Variables/Inicio/idUsuario"
	path = [path]
	
	data = system.tag.readBlocking(path)
	
	idUsuario = data[0].value
	#---LLAMADA A LA QUERY PARA OBTENER ID------------------------------
	query = """
		SELECT
			id
		FROM 
			{0}
		WHERE tarea = ?
		AND celula = ?
		AND referencia = ?
		AND maquina = ?
		AND activo = 1
	""".format(tablaTareasResumen)
	
	params = [str(tarea) ,str(celula), str(referencia), str(maquina)]
	
	data = system.db.runPrepQuery(query, params, database)
	print data[0][0]
	idTareasResumen = data[0][0]
	
	#---LLAMADA A LA QUERY Y SUS PARAMETROS------------------------
	query = """
	INSERT INTO {0} (fecha, manual, idUsuario, InicioFin, idTareasR)
	VALUES (?, ?, ?, ?, ?)
	""".format(tablaCompletado)
	
	# Valores a insertar
	params = [
	    system.date.now(),	# fecha
	    manual,             # manual
	    idUsuario,          # idUsuario
	    1,					# InicioFin
	    idTareasResumen		# id Tabla Tareas Resumen
	]
	
	system.db.runPrepUpdate(query, params, database)
	
	return True
	
def iniciarTareaBD_v0(celula, referencia, maquina, tarea, elemento):
	# Tareas.Data.General.iniciarTareaBD_v0(celula, referencia, maquina, tarea, elemento)
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

def iniciarTareaBD(celula, referencia, maquina, tarea, elemento):
	# Tareas.Data.General.iniciarTareaBD(celula, referencia, maquina, tarea, elemento)
	"""
	Inserta en Base de Datos los datos de la ultima tarea completada
	Primero miramos el id de Tareas Resumen para relacionar tablas
	manual = 0 significa que ha sido automatico; manual = 1 significa que ha sido manual
	InicioFin = 1 siginifica que se ha completado
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	database = constantes.Database_Tareas
	tablaCompletado = constantes.LINEA + "_Completados"
	tablaTareasResumen = constantes.LINEA + "_Tareas_Resumen"
	
	path = tp + "Variables/Inicio/idUsuario"
	path = [path]
	
	data = system.tag.readBlocking(path)
	
	idUsuario = data[0].value
	#---LLAMADA A LA QUERY PARA OBTENER ID------------------------------
	query = """
		SELECT
			id
		FROM 
			{0}
		WHERE tarea = ?
		AND celula = ?
		AND referencia = ?
		AND maquina = ?
		AND activo = 1
	""".format(tablaTareasResumen)
	
	params = [str(tarea) ,str(celula), str(referencia), str(maquina)]
	
	data = system.db.runPrepQuery(query, params, database)
	print data[0][0]
	idTareasResumen = data[0][0]
	
	#---LLAMADA A LA QUERY Y SUS PARAMETROS------------------------
	query = """
	INSERT INTO {0} (fecha, manual, idUsuario, InicioFin, idTareasR)
	VALUES (?, ?, ?, ?, ?)
	""".format(tablaCompletado)
	
	# Valores a insertar
	params = [
	    system.date.now(),	# fecha
	    0,             # manual
	    idUsuario,          # idUsuario
	    1,					# InicioFin
	    idTareasResumen		# id Tabla Tareas Resumen
	]
	
	system.db.runPrepUpdate(query, params, database)
	
	return True

def borrarTareasCompletadasPorHoras():
	# Tareas.Data.General.borrarTareasCompletadasPorHoras()
	"""
	Elimina las filas del dataset de tareas cuya columna 'completado' sea 1
	y cuya fecha en 'cuando' sea anterior a unas horas respecto al momento actual (viene de un tag)
	"""
	#---PARAMETROS Y CONSTANTES------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	
	#---Leer el dataset--------------------------------------------
	lista = system.tag.readBlocking([path])
	dataset = lista[0].value
	
	columnNames = list(dataset.getColumnNames())
	rowCount = dataset.getRowCount()
	
	colCompletado = columnNames.index("completado")
	colCuando = columnNames.index("cuando")
	
	#---Hora actual y lista filtrada-------------------------------
	ahora = system.date.now()
	pathVariable = tp + "Variables/Tareas/horasBorrarTareas"
	valor = system.tag.readBlocking([pathVariable])
	horasBorrar = valor[0].value
	dosHorasAtras = system.date.addHours(ahora, -horasBorrar)
	
	filasFiltradas = []
	for i in range(rowCount):
		completado = dataset.getValueAt(i, colCompletado)
		cuando = dataset.getValueAt(i, colCuando)
		
		if not (completado == 1 and cuando < dosHorasAtras):
			# Solo conservamos las que no están completadas o son recientes
			fila = []
			for col in columnNames:
				fila.append(dataset.getValueAt(i, col))
			filasFiltradas.append(fila)
		else:
			print i
	
	#---Actualizar el dataset si hay cambios------------------------
	newDataset = system.dataset.toDataSet(columnNames, filasFiltradas)
	system.tag.writeBlocking([path], [newDataset])
	return True
	
def borrarTareasCompletadas():
	# Tareas.Data.General.borrarTareasCompletadas()
	
	"""
	Elimina del dataset todas las tareas completadas (completado == 1) 
	que coincidan en 'tarea', 'celula' y 'maquina', 
	excepto la tarea completada más reciente de cada combinación.
	"""
	
	#--- Parámetros
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	#--- Leer dataset
	ds = system.tag.readBlocking([path])[0].value
	columnNames = list(ds.getColumnNames())
	rowCount = ds.getRowCount()
	
	#--- Índices de columnas
	colTarea = columnNames.index("tarea")
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	
	#--- Agrupar tareas completadas por combinación clave
	completadas_por_clave = {}
	for i in range(rowCount):
		if ds.getValueAt(i, colCompletado) == 1:
			clave = (
				str(ds.getValueAt(i, colTarea)),
				str(ds.getValueAt(i, colCelula)),
				str(ds.getValueAt(i, colMaquina))
			)
			fecha = ds.getValueAt(i, colCuando)
			if clave not in completadas_por_clave or fecha > completadas_por_clave[clave][1]:
				completadas_por_clave[clave] = (i, fecha)  # guardamos el índice y fecha más reciente
	
	#--- Construir nuevo dataset excluyendo las tareas completadas (salvo la última por grupo)
	filasFiltradas = []
	for i in range(rowCount):
		tarea = str(ds.getValueAt(i, colTarea))
		celula = str(ds.getValueAt(i, colCelula))
		maquina = str(ds.getValueAt(i, colMaquina))
		completado = ds.getValueAt(i, colCompletado)
	
		clave = (tarea, celula, maquina)
	
		if completado == 1:
			if clave in completadas_por_clave and completadas_por_clave[clave][0] == i:
				# Es la última completada → se conserva
				pass
			else:
				continue  # Omitir tarea completada que no es la más reciente
		
		# Agregar fila al nuevo dataset
		fila = [ds.getValueAt(i, col) for col in columnNames]
		filasFiltradas.append(fila)
	
	#--- Escribir nuevo dataset
	newDataset = system.dataset.toDataSet(columnNames, filasFiltradas)
	system.tag.writeBlocking([path], [newDataset])
	print "Tareas completadas (excepto la última por grupo) eliminadas correctamente."
	
	return True


def programarTiemposTareas(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo, ocurrencia, rpt, desfase):
	# Tareas.Data.General.programarTiemposTareas(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo, ocurrencia, rpt, desfase)
	"""
	Actualiza el campo 'cuando' para tareas filtradas por celula, maquina y comienzo de tarea.
	- Tareas con completado != 0 son ignoradas.
	- Si desfase == -1: la primera tarea es ahora, el resto según ocurrencia * rpt.
	- Si desfase == 0: primera tarea desde ocurrencia * rpt.
	- Si desfase > 0: primera tarea desde desfase, luego suma ocurrencia * rpt.
	"""
	# Ruta del dataset
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	logger = system.util.getLogger('Pruebas JD')
	logger.info("Tarea reprogramada: {} de la celula: {} en la maquina: {}".format(TareaObjetivo, CelulaObjetivo, MaquinaObjetivo))
	logger.info("El desfase de la tarea reprogramada es: {}".format(desfase))
	
	# Fecha actual
	now = system.date.now()
	
	# Leer dataset
	ds = system.tag.readBlocking([path])[0].value
	columnNames = list(ds.getColumnNames())
	rowCount = ds.getRowCount()
	
	# Indices de columnas
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colTarea = columnNames.index("tarea")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	
	# Convertir a lista modificable
	rows = [ [ds.getValueAt(i, col) for col in columnNames] for i in range(rowCount) ]
	
	# Filtrar filas válidas
	tareas_filtradas = []
	for i, row in enumerate(rows):
		if (
			row[colCelula] == CelulaObjetivo and
			row[colMaquina] == MaquinaObjetivo and
			str(row[colTarea]).startswith(TareaObjetivo) and
			row[colCompletado] == 0
		):
			tareas_filtradas.append((i, row))
	
	if not tareas_filtradas:
		print "No se encontraron tareas que cumplan los criterios."
		return False
	
	# Aplicar fechas
	for index, (i, row) in enumerate(tareas_filtradas):
		if desfase == -1:
			minutos = index * ocurrencia * rpt
		elif desfase == 0:
			minutos = (index + 1) * ocurrencia * rpt
		else:
			if index == 0:
				minutos = desfase
			else:
				minutos = desfase + (index * ocurrencia * rpt)
	
		nuevaFecha = system.date.addMinutes(now, int(minutos))
		rows[i][colCuando] = nuevaFecha
		print "Fila modificada:", i, "- Nuevo 'cuando':", nuevaFecha
	
	# Escribir nuevo dataset
	newDataset = system.dataset.toDataSet(columnNames, rows)
	system.tag.writeBlocking([path], [newDataset])
	print "Tareas actualizadas correctamente."
	
	return True

def obtenerProximaFecha(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo):
	# Tareas.Data.General.obtenerProximaFecha(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo)
	"""
	Devuelve la fecha 'cuando' más próxima de una tarea que:
	- Coincida con la celula y máquina indicadas.
	- Empiece por el texto dado en TareaObjetivo.
	- No esté completada (completado == 0).
	"""
	
	#--- Ruta del dataset
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	#--- Leer dataset
	ds = system.tag.readBlocking([path])[0].value
	columnNames = list(ds.getColumnNames())
	rowCount = ds.getRowCount()
	
	#--- Indices de columnas
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colTarea = columnNames.index("tarea")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	
	#--- Buscar tarea más próxima
	fechaMasProxima = None
	
	for i in range(rowCount):
		celula = ds.getValueAt(i, colCelula)
		maquina = ds.getValueAt(i, colMaquina)
		tarea = ds.getValueAt(i, colTarea)
		completado = ds.getValueAt(i, colCompletado)
		cuando = ds.getValueAt(i, colCuando)
		
		
		if (celula == CelulaObjetivo and maquina == MaquinaObjetivo and tarea.startswith(TareaObjetivo) and completado == 0):
			if fechaMasProxima is None or cuando < fechaMasProxima:
				fechaMasProxima = cuando
	
	#--- Devolver resultado
	if fechaMasProxima is not None:
		print "Próxima tarea:", fechaMasProxima
		return fechaMasProxima
	else:
		print "No se encontró ninguna tarea pendiente con esos criterios."
		return None
	
def obtenerUltimaTareaCompletada(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo):
	# Tareas.Data.General.obtenerUltimaTareaCompletada(CelulaObjetivo, MaquinaObjetivo, TareaObjetivo)
	"""
	Devuelve la fecha 'cuando' más reciente de una tarea que:
	- Coincida con la celula y máquina indicadas.
	- Empiece por el texto dado en TareaObjetivo.
	- Esté completada (completado == 1).
	"""
	
	#--- Ruta del dataset
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	#--- Leer dataset
	ds = system.tag.readBlocking([path])[0].value
	columnNames = list(ds.getColumnNames())
	rowCount = ds.getRowCount()
	
	#--- Indices de columnas
	colCelula = columnNames.index("celula")
	colMaquina = columnNames.index("maquina")
	colTarea = columnNames.index("tarea")
	colCuando = columnNames.index("cuando")
	colCompletado = columnNames.index("completado")
	
	#--- Buscar tarea completada más reciente
	ultimaFecha = None
	
	for i in range(rowCount):
		celula = ds.getValueAt(i, colCelula)
		maquina = ds.getValueAt(i, colMaquina)
		tarea = str(ds.getValueAt(i, colTarea))
		completado = ds.getValueAt(i, colCompletado)
		cuando = ds.getValueAt(i, colCuando)
		
		if (
			celula == CelulaObjetivo and
			maquina == MaquinaObjetivo and
			tarea.startswith(TareaObjetivo) and
			completado == 1
		):
			if ultimaFecha is None or cuando > ultimaFecha:
				ultimaFecha = cuando
	
	#--- Devolver resultado
	if ultimaFecha is not None:
		print "Última tarea completada:", ultimaFecha
		return ultimaFecha
	else:
		# Fecha por defecto: 01/01/1970 00:00:00
		fechaDefault = system.date.fromMillis(0)
		print "No se encontró ninguna tarea completada con esos criterios."
		return fechaDefault
 