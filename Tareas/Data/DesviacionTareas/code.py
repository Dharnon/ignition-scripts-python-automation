def desviacionesTareas():
	# Tareas.Data.DesviacionTareas.desviacionesTareas()
	"""
	Repasa los tiempos de produccion por cada tarea de cada maquina y celula.
	Si hay alguna desviacion actualiza el dataset de tareas llamando a la funcion correspondiente
	Si hay tareas completadas tambien las actualiza.
	"""
	#---PARAMETROS--------------------------------------------------
	celulas = constantes.celulas
	tp = constantes.tag_provider
	manual = 0 # Significa que se ha hecho automaticamente y no de manera manual
	#---------------------------------------------------------------
	logger = system.util.getLogger('Prueba JD')
	
	for celula in celulas:
		print "======================== CELULA " + str(celula) + " ========================"
		# Numero de maquinas por celula
		path = tp + "Celula" + celula
		total = len(system.tag.browse(path, {"name": "Maq_*"})) # Mira el numero de tags dentro de una carpeta, que empiecen por "Maq_"
		referencia = Sinoptico.Data.General.obtenerReferencia(celula)		# Obtener referencia
		logger.info("Celula: " + str(celula))
		for num in range(1, total + 1):
			try:
				conexion = Sinoptico.Data.General.obtenerConexion(celula, num)
				print "------ Numero: " + str(num) + " ------"
				print "------ Conexion: " + str(conexion) + " ------"
				if conexion == 'Good':
					tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)	# Mira el tipo de maquina para saber si es el plc general de automatica
					print "---------------------- " + str(tipoMaq) + " ----------------------------"
					logger.info("Maquina: " + str(tipoMaq))
					plc_cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num) 		# Mira si es tipo plc o cnc
					tareas = Tareas.Data.DesviacionTareas.tareasPorMaquina(celula, referencia, tipoMaq)	# Obtiene todas las tareas por maquina
					for valorTarea in tareas:
						tarea = valorTarea["tarea"] # Obtiene tarea por maquina
						logger.info("Tarea: " + str(tarea))
						print "Tarea: " + str(tarea)
						#---DESCARGA-------------------------------------------------------------------------------
						if tarea.startswith("Descarga"): # Si tarea comienza por Descarga (osea todas las descargas)
							proxTarea = Tareas.Data.General.obtenerProximaFecha(celula, tipoMaq, tarea) # Obtiene cuando es la proxima fecha de una tarea
							estadoTarea = Tareas.Data.DesviacionTareas.accionesDescarga(celula, proxTarea) # 0: Mantener igual, 1: Completado, 2: Poner a 20min, 3: Descargar YA!
							if estadoTarea != 0:
								rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq) # Obtenemos el ritmo de produccion
								ocurrencia = Tareas.Data.General.obtenerOcurrencia(celula, referencia, tipoMaq, tarea) # Obtenemos ocurrencia
								if estadoTarea == 1: # Completar tarea
									Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
								elif estadoTarea == 2: # Poner a 20 min
									Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 20) # Actualiza las tareas con un desfase de 20 min
								elif estadoTarea == 3: # Descargar YA!
									Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, -1) # Establece la primera tarea ya! Y actualiza el resto de tareas
						
						#---VERIFICACION--------------------------------------------------------------------------
						if tarea.startswith("Verificación"): # Si tarea comienza por Verificación (osea todas las verificaciones)
							estado = Tareas.Data.DesviacionTareas.accionesVerificacion(tarea, num, referencia, celula, tipoMaq)
							if estado:
								# Estado true. se completa la tarea
								Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
						
						#---CAMBIO DE HERRAMIENTA-------------------------------------------------------------------
						if tarea.startswith("CH"): # Si tarea comienza por CH (osea todas los cambios de herramientas)
							rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq) # Obtenemos el ritmo de produccion
							ocurrencia = Tareas.Data.General.obtenerOcurrencia(celula, referencia, tipoMaq, tarea) # Obtenemos ocurrencia
							
							if tipoMaq == "TORNO":
								vidaTotal = Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno(celula, num)
							elif tipoMaq == "TALLADORA":
								vidaTotal = Tareas.Data.DesviacionTareas.accionesCH_CNC_Talladora(celula, num)
							elif tipoMaq == "AFEITADORA":
								vidaTotal = Tareas.Data.DesviacionTareas.accionesCH_PLC(celula, num)
							
							
							# Hacemos la comprobacion para completar tarea; Torno diferente al resto
							if tipoMaq == "TORNO" and vidaTotal != "Bad":
								vidaHta = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
								# Vemos cual es el contador mas desfavorable
								piezas = 0
								for i in range(len(vidaHta)):
									piezasActual = vidaHta[i][1]
									if piezasActual > piezas:
										piezas = piezasActual
								# Leemos el flag de CH
								path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/FlagCH"
								path = [path]
								valor = system.tag.readBlocking(path)
								flag = valor[0].value
								
								if flag == True and piezas >= 5:
									# Completamos tarea
									Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
									system.tag.writeBlocking(path, False) # Bajamos el flag
								elif flag == False and piezas < 5:
									system.tag.writeBlocking(path, True) # Subimos el flag
									print "No hacer nada: CH TORNO"
								elif flag == False and piezas >= 5:
									# Actualizamos tarea
									tiempoTotal = int(vidaTotal) * rpt
									Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, tiempoTotal) # Actualiza las tareas con un desfase que indica tiempo de Tarea
							elif (tipoMaq == "TALLADORA" or tipoMaq == "AFEITADORA") and vidaTotal != "Bad":
								try:
									if tipoMaq == "AFEITADORA":
										datosHta = Sinoptico.Data.General.obtenerAutoHerramienta(celula, num)
										piezasActuales = datosHta[1] 
									else:
										datosHta = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
										piezasActuales = datosHta[0][1]
								except:
									piezasActuales = 9999 

								proxTarea = Tareas.Data.General.obtenerProximaFecha(celula, tipoMaq, tarea)
								ahora = system.date.now()
								
								# 1. LA CONDICIÓN DE BLOQUEO (Validación)
								esperando_laboratorio = (vidaTotal <= 0) or system.date.isBefore(proxTarea, ahora) or (piezasActuales <= 5)

								if esperando_laboratorio:
									try:
										# Llamada original a GearFlow (SIN horas_busqueda)
										valorGearFlow = Tareas.Data.GearFlow.cambioHerramientas(
											ahora, tipoSolicitud="HERRAMIENTA", referencia=referencia, 
											celula=celula, herramienta=tipoMaq
										)
									except:
										valorGearFlow = None

									if valorGearFlow == 'OK':
										logger.info("GearFlow OK detectado. Completando tarea de CH " + tipoMaq)
										Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
									else:
										# 🛑 LA CLAVE: CONGELAMOS LA TAREA
										logger.info("CH en espera de Laboratorio. Congelando tarea.")
										Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 0)
								else:
									# 2. PRODUCCIÓN NORMAL
									tiempoTotal = int(vidaTotal) * rpt
									Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, tiempoTotal)
						#---CAMBIO BANDEJA DE CARGA------------------------------------------------------------------
						if tarea.startswith("Cambio de carga") and tipoMaq == "BIN PICKING": # La tarea es 'Cambio Bandeja Carga'
							estadoTarea = Tareas.Data.DesviacionTareas.accionesCambioBandejaCarga(celula, num)
							if estadoTarea == 1: # Significa que queda la mitad de las piezas
								rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq) # Obtenemos el ritmo de produccion
								ocurrencia = Tareas.Data.General.obtenerOcurrencia(celula, referencia, tipoMaq, tarea) # Obtenemos ocurrencia
								desfase = (int(ocurrencia/2))*rpt
								Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, desfase) # Y pone que falta la mitad del tiempo
							elif estadoTarea == 2: # Significa que hay que completar la tarea
								Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
						
						#---CAMBIO BANDEJA DE DESCARGA---------------------------------------------------------------
						if tarea.startswith("Cambio de carga") and tipoMaq == "CELULA": # La tarea es 'Cambio Bandeja Descarga'
							estadoTarea = Tareas.Data.DesviacionTareas.accionesCambioBandejaDescarga(celula, num, referencia)
							if estadoTarea:
								# Hay que completar la tarea
								Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
						
						#---GRAFICO---------------------------------------------------------------
						if tarea.startswith("Grafico"): # Si tarea comienza por 'Grafico'
							proxFecha = Tareas.Data.General.obtenerProximaFecha(celula, tipoMaq, tarea)
							valor = Tareas.Data.GearFlow.grafico(proxFecha, tipoSolicitud="CONTROL", referencia=referencia, celula=celula, herramienta=tipoMaq) # Mira en Gear Flow a ver si hay un OK
							if valor == 'OK':
								# El valor ha dado OK asi que podemos dar la tarea como completada
								Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
			except Exception as e:
				logger.error("----------ERROR dentro de Tareas.Data.DesviacionTareas.desviacionesTareas()-------------")
				continue
						
	return True
	
def tareasPorMaquina(celula, referencia, maquina):
	# Tareas.Data.DesviacionTareas.tareasPorMaquina(celula, referencia, maquina)
	"""
	Devuelve todas las tareas que le corresponden hacer a una maquina segun referencia, celula y maquina
	"""
	#---PARAMETROS--------------------------------------------------
	database = constantes.Database_Tareas
	tablaTareas = constantes.LINEA + "_Tareas_Resumen"
	#---------------------------------------------------------------
	# Obtenemos tareas
	query = """
		SELECT
    		tarea
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
	
def accionesDescarga(celula, proxTarea):
	# Tareas.Data.DesviacionTareas.accionesDescarga(celula, proxTarea)
	"""
	Script que realiza las acciones de la tarea de descarga
	saturacion = [preSat, Sat]
	return 0: Mantener igual
	return 1: Completado
	return 2: Poner a 20 min
	return 3: Descargar Ya!
	"""
	#---PARAMETROS--------------------------------------------------
	now = system.date.now()
	#---------------------------------------------------------------

	# Usamos la maquina LAVADORA porque hay que leer la saturacion de la lavadora para la descarga
	maquina = "LAVADORA"
	num = Sinoptico.Data.General.obtenerNumeroMaquina(celula, maquina)
	# Leemos los tags de saturacion
	saturacion = Sinoptico.Data.General.obtenerSaturacion(celula, num)
	preSat = saturacion[0]
	Sat = saturacion[1]
	
	# Comparamos las fechas 
	minutos = system.date.minutesBetween(now, proxTarea)
	
	# Realizamos accion
	if preSat == 1 and Sat == 1:
		return 3 # Descargar YA!
	elif preSat == 1 and Sat == 0 and minutos > 20:
		return 2 # Ajustar a 20 min
	elif preSat == 0 and Sat == 0 and minutos <= 15:
		return 1 # Tarea Completada
	
	return 0 # Mantener igual
	
def accionesVerificacion(tarea, num, referencia, celula, maquina):
    # Tareas.Data.DesviacionTareas.accionesVerificacion_Pruebas(tarea, num, referencia, celula, maquina)
    """
    Verifica si hay nuevas mediciones en QDAS y actualiza el dataset de verificaciones
    Versión modificada: sin filtrar por característica, obtiene la fecha más reciente
    """
    try:
        # --- PARÁMETROS ---
        tp = constantes.tag_provider
        database = constantes.Database_QDAS
        
        # Construir ruta del tag
        tag_path = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/Verificaciones"
        
        tarea_original = unicode(tarea)
        
        # Comprobar si tiene 'ó' y dividir
        if u'ó' in tarea_original:
            partes = tarea_original.split(u'ó')
            tiene_caracter_especial = True
        elif u'Ó' in tarea_original:
            partes = tarea_original.split(u'Ó')
            tiene_caracter_especial = True
        else:
            partes = None
            tiene_caracter_especial = False
        
        # Para guardar/comparar usamos solo la parte después de 'ó'
        if tiene_caracter_especial and len(partes) > 1:
            tarea_guardado = partes[1].strip()
            print "Tarea original: {}".format(tarea_original)
            print "Parte a guardar: {}".format(tarea_guardado)
        else:
            tarea_guardado = tarea_original
            print "Tarea (sin caracter especial): {}".format(tarea_guardado)
        
        # --- QUERY PARA BUSCAR MEDICIONES EN QDAS (SIN FILTRO DE CARACTERÍSTICA) ---
        query_qdas = """
        SELECT
            t.Teteil,
            t.TETEILNR AS Referencia,
            t.TEBEZEICH AS Descripcion,
            t.TEWERKSTATT AS Celula,
            t.TEPRUEFART AS TipoMedicion,
            m.MEMERKBEZ AS Caracteristica,
            m.MEMASCHBEZ AS Maquina,
            w.WVWERT AS Valor,
            w.WVPRUEFER AS Operario,
            w.WVDATZEIT AS FechaHoraMedicion
        FROM TEIL AS t
        INNER JOIN MERKMAL AS m ON t.Teteil = m.Meteil
        INNER JOIN WERTEVAR AS w ON t.Teteil = w.Wvteil
        WHERE t.TETEILNR LIKE ? 
            AND t.TEWERKSTATT LIKE ? 
            AND m.MEMASCHBEZ = ?
            AND w.WVDATZEIT IS NOT NULL
        ORDER BY w.WVDATZEIT DESC
        """
        
        print "="*80
        print "Buscando mediciones para tarea: {}".format(tarea_guardado)
        print "="*80
        
        # Ejecutar query sin filtro de característica
        try:
            resultado = system.db.runPrepQuery(
                query_qdas, 
                [str(referencia) + '%', str(celula) + '%', str(maquina)], 
                database
            )
            
            if resultado is None or resultado.getRowCount() == 0:
                print "\n" + "="*80
                print "NO se encontraron mediciones en QDAS"
                print "="*80
                return False
            
            # Obtener la fecha más reciente (ya ordenado DESC)
            fecha_mas_reciente = None
            
            for i in range(resultado.getRowCount()):
                fecha = resultado.getValueAt(i, "FechaHoraMedicion")
                
                if fecha is not None:
                    if fecha_mas_reciente is None or fecha > fecha_mas_reciente:
                        fecha_mas_reciente = fecha
            
            if fecha_mas_reciente is None:
                print "\n" + "="*80
                print "NO se encontraron fechas válidas en las mediciones"
                print "="*80
                return False
            
            print "\n" + "="*80
            print "Fecha más reciente encontrada en QDAS: {}".format(fecha_mas_reciente)
            print "Total de registros encontrados: {}".format(resultado.getRowCount())
            print "="*80
            
        except Exception as e:
            print "ERROR en búsqueda QDAS: {}".format(str(e))
            return False
        
        # --- LEER EL DATASET DEL TAG ---
        try:
            tag_result = system.tag.readBlocking([tag_path])
            
            if tag_result is None or len(tag_result) == 0:
                print "ERROR: No se pudo leer el tag: {}".format(tag_path)
                return False
                
            dataset_actual = tag_result[0].value
            
            if dataset_actual is None:
                print "ERROR: El dataset es None"
                return False
                
        except Exception as e:
            print "ERROR al leer el tag: {}".format(str(e))
            return False
        
        # Validar columnas del dataset
        columnas = list(dataset_actual.getColumnNames())
        if "tarea" not in columnas or "fecha" not in columnas:
            print "ERROR: El dataset no tiene las columnas esperadas (tarea, fecha)"
            print "Columnas actuales: {}".format(columnas)
            return False
        
        # --- BUSCAR SI LA TAREA YA EXISTE EN EL DATASET ---
        tarea_existe = False
        fecha_guardada = None
        fila_tarea = -1
        
        for i in range(dataset_actual.getRowCount()):
            tarea_ds = unicode(dataset_actual.getValueAt(i, "tarea"))
            
            print "Comparando dataset[{}]: '{}'".format(i, tarea_ds)
            print "  Con: '{}'".format(tarea_guardado)
            
            # Comparar con endswith o igualdad exacta
            if tiene_caracter_especial:
                if tarea_ds.endswith(tarea_guardado) or tarea_ds == tarea_guardado:
                    tarea_existe = True
                    fecha_guardada = dataset_actual.getValueAt(i, "fecha")
                    fila_tarea = i
                    print "  -> MATCH!"
                    break
            else:
                if tarea_ds == tarea_guardado:
                    tarea_existe = True
                    fecha_guardada = dataset_actual.getValueAt(i, "fecha")
                    fila_tarea = i
                    print "  -> MATCH!"
                    break
        
        # --- PROCESAR SEGÚN SI EXISTE O NO ---
        if tarea_existe:
            print "\nTarea encontrada en dataset (fila {})".format(fila_tarea)
            print "Fecha guardada:      {}".format(fecha_guardada)
            print "Fecha QDAS (reciente): {}".format(fecha_mas_reciente)
            
            # Comparar fechas: si la de QDAS es más reciente (futura), actualizar
            if fecha_mas_reciente > fecha_guardada:
                print "\n*** FECHA QDAS ES MÁS RECIENTE - Actualizando dataset ***"
                
                dataset_actualizado = system.dataset.setValue(
                    dataset_actual, 
                    fila_tarea, 
                    "fecha", 
                    fecha_mas_reciente
                )
                
                system.tag.writeBlocking([tag_path], [dataset_actualizado])
                
                return True
            else:
                print "\n*** FECHA GUARDADA ES IGUAL O MÁS RECIENTE - Sin cambios ***"
                return False
        else:
            print "\nTarea NO encontrada en dataset - Creando nueva fila"
            
            nueva_fila = [[tarea_guardado, fecha_mas_reciente]]
            dataset_actualizado = system.dataset.addRows(dataset_actual, nueva_fila)
            
            system.tag.writeBlocking([tag_path], [dataset_actualizado])
            
            print "Tarea creada exitosamente: {}".format(tarea_guardado)
            return False
            
    except Exception as e:
        print "ERROR GENERAL en accionesVerificacion_Pruebas: {}".format(str(e))
        import traceback
        print traceback.format_exc()
        return False
	
def accionesCH_PLC(celula, num):
	# Tareas.Data.DesviacionTareas.accionesCH_PLC(celula, num)
	"""
	Script que realiza las acciones de la tarea de cambio de herramientas tipo PLC
	Resta la (vidaTeorica - vida Util) * rpt para obtener el tiempo estimado para la siguiente tarea
	vidaHerr = [vidaTeorica, vidaUtil]
	"""
	#---PARAMETROS--------------------------------------------------
	#---------------------------------------------------------------
	try:
		vidaHerr = Sinoptico.Data.General.obtenerAutoHerramienta(celula, num)
		vidaTeorica = vidaHerr[0]
		vidaUtil = vidaHerr[1]
		
		vidaTotal = vidaTeorica - vidaUtil
	
		if vidaTotal == 0:
			return "Bad"
		else:
			return vidaTotal
	
	except Exception as e:
		print("Tareas.Data.DesviacionTareas.accionesCH_PLC():", str(e))
		return "Bad"
	
def accionesCH_CNC_Torno_v0(celula, num):
	# Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno_v0(celula, num)
	"""
	Script que realiza las acciones de la tarea de cambio de herramientas tipo CNC de la maquina Torno
	vidaHerr = [vidaTeorica, vidaUtil]
	"""
	#---PARAMETROS----------------------------------------------
	#prefijo = constantes.prefijo - Se usa mas adelante en el codigo
	vidaTotal = 0
	vidaReal = 0
	vidaMax = 0
	#-----------------------------------------------------------
	try:
		nombres = Sinoptico.Data.General.obtenerCNCHtaNombre(celula, num)
		prefijo = nombres[0] # Cogemos el prefijo de la primera pieza
		vidaHta = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
		
		cantidad_original = len(nombres)
		cantidad = len([nombre for nombre in nombres if nombre.startswith(prefijo)])
		
		for i in range(0, cantidad):
			vidaMax += vidaHta[i][0] # Sumamos las vidaMax de los prefijos que coincidan
		
		for i in range(0, cantidad_original):
			#print vidaHta[i][0] # Vida Max
			#print vidaHta[i][1] # Vida Util
			vidaReal_i = vidaHta[i][1]
			if vidaReal_i > vidaReal: # Vemos cual es el mas desfavorable (osea el mas alto)
				vidaReal = vidaReal_i
		vidaRealCantidad = vidaReal * cantidad # Obtenemos la cantidad de Herramientas
		
		vidaTotal = vidaMax - vidaRealCantidad # Obtenemos todas las vidas utiles en total de la herramienta
		
		if vidaTotal == 0:
			return "Bad"
		else:
			return vidaTotal
		
	except Exception as e:
		print("Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno():", str(e))
		return "Bad"
	
def accionesCH_CNC_Torno(celula, num):
	# Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno(celula, num)
	"""
	Script que realiza las acciones de la tarea de cambio de herramientas tipo CNC de la maquina Torno
	vidaHerr = [vidaTeorica, vidaUtil]
	Mira los nombres unicos y hace la suma de todas las vidas max y utiles para hacer la diferencia
	La mas desfavorable (el menor valor) es el resultado final
	"""
	
	#---PARAMETROS----------------------------------------------
	#prefijo = constantes.prefijo - Se usa mas adelante en el codigo
	vidaTotal = 0
	Total = 9999
	vidaReal = 0
	vidaMax = 0
	
	tp = constantes.tag_provider
	
	# Construir las rutas base
	base_path1 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaVidaMax/HtaVidaMax"
	base_path2 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/HtaVidaActual/HtaVidaActual"
	#-----------------------------------------------------------
	
	base_path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaNombre/HtaNombre"
	try:
		paths_nombres = []
		for i in range(1, 121):
		    paths_nombres.append(base_path + str(i))
		
		data = system.tag.readBlocking(paths_nombres)
		
		nombres = []
		
		for i in range(120):
		    nombre_valor = data[i].value
		    if str(nombre_valor).strip() != "":
		        nombres.append(nombre_valor)
		
		
		
		nombresUnicos = list(set(nombres))
		#print nombresUnicos
		posiciones = {}
		for valor in nombresUnicos:
			posiciones[valor] = [i for i, v in enumerate(nombres) if v == valor]
		#print posiciones
		
		for nombres in nombresUnicos:
			if nombres != None and nombres != "ARMED":
				#print nombres
				posicion = posiciones[nombres]
				for p in posicion:
					#print p
					path_vidaMax = base_path1 + str(p+1)
					path_vidaUtil = base_path2 + str(p+1)
					
					valorVidaMax = system.tag.readBlocking(path_vidaMax)
					valorVidaUtil = system.tag.readBlocking(path_vidaUtil)
					
					vidaMax += valorVidaMax[0].value
					vidaReal += valorVidaUtil[0].value
					
				#print vidaReal
				#print vidaMax
				vidaTotal = vidaMax - vidaReal
				#print vidaTotal
				
				if vidaTotal < Total:
					Total = vidaTotal
				#print Total
		return Total
	except Exception as e:
		print("Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno():", str(e))
		return "Bad"
	
def accionesCH_CNC_Talladora(celula, num):
	# Tareas.Data.DesviacionTareas.accionesCH_CNC_Talladora(celula, num)
	"""
	Script que realiza las acciones de la tarea de cambio de herramientas tipo CNC
	Resta la (vidaTeorica - vida Util) * rpt para obtener el tiempo estimado para la siguiente tarea
	vidaHerr = [vidaTeorica, vidaUtil]
	"""
	#---PARAMETROS--------------------------------------------------
	#---------------------------------------------------------------
	try:
		vidaHerr = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
		vidaTeorica = vidaHerr[0][0]
		vidaUtil = vidaHerr[0][1]
		
		vidaTotal = vidaTeorica - vidaUtil
		
		if vidaTotal == 0:
			return "Bad"
		else:
			return vidaTotal
		
	except Exception as e:
		print("Tareas.Data.DesviacionTareas.accionesCH_CNC_Torno():", str(e))
		return "Bad"
	
def accionesCambioBandejaCarga(celula, num):
	# Tareas.Data.DesviacionTareas.accionesCambioBandejaCarga(celula, num)
	"""
	Script que realiza las acciones de la tarea cambio bandeja de carga del bin picking
	saturacion = [preSat, Sat]
	return 0: Mantener igual
	return 1: Quedan la mitad de las piezas
	return 2: Completado
	"""
	#---PARAMETROS--------------------------------------------------
	tp = constantes.tag_provider
	#---------------------------------------------------------------
	try:
		# Leemos los tags de saturacion
		saturacion = Sinoptico.Data.General.obtenerSaturacion(celula, num)
		preSat = saturacion[0]
		
		# Leemos el flag de Pre
		path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Pre"
		path = [path]
		
		valor = system.tag.readBlocking(path)
		
		preUDT = valor[0].value
	
		# Realizamos accion
		if preSat == 1 and preUDT == 0:
			system.tag.writeBlocking(path, [preSat])
			return 1 # Hay que ponerlo a la mitad
		elif preSat == 0 and preUDT == 1:
			system.tag.writeBlocking(path, [preSat])
			return 2 # Completado
		else:
			return 0 # Mantener igual
	except Exception as e:
		print("Error en Tareas.Data.DesviacionTareas.accionesCambioBandejaCarga(celula, num): " + str(e))
        return 0
		
def accionesCambioBandejaDescarga(celula, num, referencia):
    # Tareas.Data.DesviacionTareas.accionesCambioBandejaDescarga(celula, num, referencia)
    """
    Se comprueba en base de datos si el rack es diferente al anterior se debe completar la tarea
    """
    #---PARAMETROS--------
    tp = constantes.tag_provider
    database = constantes.Database_Tareas_2
    tabla = "CGF_RACKS_DATA_MARTS"
    
    try:
        #---Obtenemos último rack en base de datos----------------
        query = """
            SELECT TOP 1
                RS_ETIQUETA_RACK_LOCAL
            FROM 
                {0}
            WHERE
                RS_CODIGO_REFERENCIA = ?
                AND RS_ETIQUETA_RACK_LOCAL LIKE 'GFV-%'
            ORDER BY RS_FECHA DESC
        """.format(tabla)
        
        params = [str(referencia)]
        data = system.db.runPrepQuery(query, params, database)

        if not data or len(data) == 0:
            print("No se encontraron racks para referencia:", referencia)
            return False
        
        nuevoRack = data[0][0]
        print nuevoRack
        
        #---Leemos el último rack guardado en tags----------------
        path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Rack"
        valor = system.tag.readBlocking([path])
        ultRack = valor[0].value
        
        #---Comprobamos diferencias y actualizamos si procede-----
        if ultRack is not None and ultRack != nuevoRack:
            system.tag.writeBlocking([path], [nuevoRack])
            return True
        elif ultRack is None:
            system.tag.writeBlocking([path], [nuevoRack])
            return False
        elif ultRack == nuevoRack:
            return False
    
    except Exception as e:
        print("Error en Tareas.Data.DesviacionTareas.accionesCambioBandejaDescarga(celula, num, referencia): " + str(e))
        return False
	