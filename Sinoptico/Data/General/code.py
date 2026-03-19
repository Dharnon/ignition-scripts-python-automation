def obtenerReferencia(celula):
	# Sinoptico.Data.General.obtenerReferencia(celula)
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

def obtenerOEEStatus_v0(celula, referencia):
	# Sinoptico.Data.General.obtenerOEEStatus_v0(celula, referencia)
	"""-
	0 - Verde
	1 - Amarillo
	2 - Rojo
	"""
	try:
		database = constantes.Database_Sinoptico
		tp = constantes.tag_provider
		
		# Se obtiene por medio de base de datos el ultimo registro que significa cuando ha comenzado una pieza
		query = "SELECT TOP 1 Production.TimeComplete FROM COEEproduction as Production"
		query = query + " INNER JOIN COEEasset AS Asset ON Asset.AssetID = Production.AssetID AND Asset.AssetName = 'C" + str(celula) + "'" #INNER JOIN
		query = query + " WHERE Production.Job = '" + str(referencia) + "'"
		query = query + " ORDER BY Production.TimeComplete desc"
		
		data = system.db.runQuery(query, database)
		
		tiempo = data[0][0]
		print "Tiempo base de datos: " + str(tiempo)
		
		# Se obtiene la fecha actual
		now = system.date.now()
		print "Tiempo ahora: " + str(now)
		
		# Se obtiene la diferencia en segundos y se pasa a minutos
		segundos = system.date.secondsBetween(tiempo, now)
		tiempoTotal = segundos/60.0
		print "Tiempo de diferencia en minutos: " + str(tiempoTotal)
		
		# Se obtiene por medio de base de datos la production rate
		newCelula = "C" + str(celula[:-1])
		
		query = "SELECT ProductionRate FROM COEErate"
		query = query + " WHERE WorkGroup = '" + newCelula + "' "
		query = query + "AND Job = '" + str(referencia) + "'"
		
		data = system.db.runQuery(query, database)
		
		productionRate = data[0][0]
		
		print "Production Rate que indica la base de datos: " + str(productionRate)
		
		# El limite de la production rate es + 5 min
		
		pr = productionRate + 5
		print "Production Rate Final (con el factor de potencia de +5 min): " + str(pr)
		
		# Resultado
		if tiempoTotal < pr:
			print "Tiempo total < Produccion Rate: Vamos bien (Verde)"
			oeValor = 0
		else:
			print "Tiempo total >= Produccion Rate: Vamos mal (Amarillo)"
			oeValor = 1
		
		# Es rojo si la celula automatica disponibilidad = False. Hay que recorrer todas
		path = tp + "Celula" + celula
		total = len(system.tag.browse(path, {"name": "Maq_*"}))
		
		for num in range(1, total + 1):
			tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
			if tipoMaq == "CELULA":
				disponibilidad = Sinoptico.Data.General.obtenerDisponibilidad(celula, num)
				if disponibilidad == False:
					print "Celula automatica: disponibilidad = False (Rojo)"
					oeValor = 2
		
		return oeValor
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerOEEStatus: {}".format(str(e)))
		return 'NULL'

def obtenerOEEStatus(celula, referencia):
    # Sinoptico.Data.General.obtenerOEEStatus(celula, referencia)
    """
    0 - Verde
    1 - Amarillo
    2 - Rojo
    """
    try:
    	#---PARAMETROS----------------------------------------------
        database = constantes.Database_Sinoptico
        tp = constantes.tag_provider

        #---Check de celula automatica (Rojo)----------------------
        path = tp + "Celula" + celula
        total = len(system.tag.browse(path, {"name": "Maq_*"}))

        for num in range(1, total + 1):
            tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
            if tipoMaq == "CELULA":
                disponibilidad = Sinoptico.Data.General.obtenerDisponibilidad(celula, num)
                print "Disponibilidad: "
                print disponibilidad
                if disponibilidad == False:
                    print "Celula automatica: disponibilidad = False (Rojo)"
                    oeValor = 2
                    return oeValor
        
        #---Obtener AssetID desde el tag----------------------------
        path = tp + "Variables/Datos_Celula/Celula" + str(celula) + "/AssetID"
        rutaTag = [path]
        AssetId = system.tag.readBlocking(rutaTag)[0].value
        print "AssetID obtenido del tag:", AssetId

        #---Último registro Production.TimeComplete----------------
        query = """
            SELECT TOP 1 Production.TimeComplete
            FROM COEEproduction AS Production
            WHERE Production.AssetID = ?
            AND Production.Job = ?
            ORDER BY Production.TimeComplete DESC
        """
        params = [str(AssetId), str(referencia)]
        data = system.db.runPrepQuery(query, params, database)

        if not data or len(data) == 0:
            print "No se encontraron datos en COEEproduction"
            return 'NULL'

        tiempo = data[0][0]
        print "Tiempo base de datos:", tiempo

        #---Fecha actual-------------------------------------------
        now = system.date.now()
        print "Tiempo ahora:", now

        #---Diferencia en minutos----------------------------------
        segundos = system.date.secondsBetween(tiempo, now)
        tiempoTotal = segundos / 60.0
        print "Tiempo de diferencia en minutos:", tiempoTotal

        #---Obtener ProductionRate---------------------------------
        newCelula = "C" + str(celula[:-1])
        query = """
            SELECT ProductionRate
            FROM COEErate
            WHERE WorkGroup = ?
            AND Job = ?
        """
        params = [newCelula, str(referencia)]
        data = system.db.runPrepQuery(query, params, database)

        if not data or len(data) == 0:
            print "No se encontró ProductionRate"
            return 'NULL'

        productionRate = data[0][0]
        print "Production Rate:", productionRate

        #---Factor +5 minutos--------------------------------------
        pr = productionRate + 5
        print "Production Rate Final (+5 min):", pr

        #---Resultado preliminar-----------------------------------
        if tiempoTotal < pr:
            print "Tiempo total < Production Rate: Verde"
            oeValor = 0
        else:
            print "Tiempo total >= Production Rate: Amarillo"
            oeValor = 1

        return oeValor

    except Exception as e:
        system.util.getLogger("ScriptError").error("obtenerOEEStatus: {}".format(str(e)))
        return 'NULL'
 

def obtenerAuto(celula, num):
	# Sinoptico.Data.General.obtenerAuto(celula, num)
	"""
	Obtener si es automatico o no segun un tag.
	0: NO AUTO
	1: AUTO
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Grupo_Auto"
		path = [path]
		
		auto = system.tag.readBlocking(path)
		
		return auto[0].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerAuto: {}".format(str(e)))
		return 'NULL'
	
def obtenerPLC_CNC(celula, num):
	# Sinoptico.Data.General.obtenerPLC_CNC(celula, num)
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
	
def obtenerPosicion(celula, num):
	# Sinoptico.Data.General.obtenerPosicion(celula, num)
	"""
	Obtener la posicion de la maquina segun un tag
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Posicion"
		path = [path]
		
		pos = system.tag.readBlocking(path)
		
		return pos[0].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerPosicion: {}".format(str(e)))
		return 'NULL'
	
def obtenerPosicionAuto(celula, num):
	# Sinoptico.Data.General.obtenerPosicionAuto(celula, num)
	"""
	Obtener la posicion de la maquina dentro de la automatica segun un tag
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/Posicion_Auto"
		path = [path]
		
		pos = system.tag.readBlocking(path)
		
		return pos[0].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerPosicion: {}".format(str(e)))
		return 'NULL'

def obtenerTipoMaquina(celula, num):
	# Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
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

def obtenerIDMaquina(celula, num):
	# Sinoptico.Data.General.obtenerIDMaquina(celula, num)
	"""
	Obtener el id de la maquina de la célula segun un tag.
	Del id se coge los ultimos 4 numeros y se le añade una 'E' delante
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Constantes/ID_Maquina"
		path = [path]
		
		data = system.tag.readBlocking(path)
		valor = data[0].value
		
		valor = str(valor)
		idMaq = "E" + valor[8:]
		
		return idMaq
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerIDMaquina: {}".format(str(e)))
		return 'NULL'

def obtenerDisponibilidad(celula, num):
	# Sinoptico.Data.General.obtenerDisponibilidad(celula, num)
	"""
	Obtener disponibilidad de la maquina segun un tag.
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Maq_Disponible"
		path = [path]
		
		data = system.tag.readBlocking(path)
		
		return data[0].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerDisponibilidad: {}".format(str(e)))
		return 'NULL'
	
def obtenerCiclo(celula, num):
	# Sinoptico.Data.General.obtenerCiclo(celula, num)
	"""
	Obtener ciclo de una maquina segun un tag.
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Maq_Ciclo"
		path = [path]
		
		data = system.tag.readBlocking(path)
		
		return data[0].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerCiclo: {}".format(str(e)))
		return 'NULL'
	
def obtenerCNCContador(celula, num):
	# Sinoptico.Data.General.obtenerCNCContador(celula, num)
	"""
	Obtener contador de la maquina CNC restando el actual con el principio de turno.
	"""
	try:
		tp = constantes.tag_provider
		# Valor actual
		path1 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/ContadorPiezas/Pos1" # Contador Actual
		path2 = tp + "Datos_Celula/Celula" + celula + "/Maq_" +  str(num) + "/Piezas_Turno" # Contador principio de turno
		path = [path1, path2]
		
		data = system.tag.readBlocking(path)
		
		print data[0].value
		print data[1].value
		"""
		if data[0].value != None or data[1].value != None:
			contador = data[0].value - data[1].value # Contador Actual - Contador principio de turno
			if contador < 0:
				contador = contador + 2000 # El contador cuenta de 0 a 1999. Si la resta nos da negativa hay que sumarle 2000 para que nos de el valor correcto
		else:
			contador = 0
		"""
		# Ahora cogemos directamente el valor
		return data[1].value
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerCNCContador: {}".format(str(e)))
		return 0

def obtenerCNCHerramienta(celula, num):
	# Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
	"""
	Obtener Vida Teorica y Vida Util de una Maquina CNC
	Ahora recorre tags individuales hasta el 120
	"""
	try:
		tp = constantes.tag_provider
		
		# Construir las rutas base
		base_path1 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaVidaMax/HtaVidaMax"
		base_path2 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/HtaVidaActual/HtaVidaActual"
		
		# Crear listas para almacenar todas las rutas de tags
		paths_teorica = []
		paths_util = []
		
		# Generar todas las rutas de tags del 1 al 120
		for i in range(1, 121):  # Del 1 al 120
		    paths_teorica.append(base_path1 + str(i))
		    paths_util.append(base_path2 + str(i))
		
		# Combinar todas las rutas en una sola lista
		all_paths = paths_teorica + paths_util
		
		# Leer todos los tags de una vez
		data = system.tag.readBlocking(all_paths)
		
		vidaHerr = []
		
		# Procesar los resultados (primeros 120 son vida teorica, siguientes 120 son vida util)
		for i in range(120):
			try:
				vidaTeorica = data[i].value if data[i].quality.isGood() else None
				vidaUtil = data[i + 120].value if data[i + 120].quality.isGood() else None
				
				# Solo agregar si al menos uno de los valores no es None
				if vidaTeorica is not None or vidaUtil is not None:
					# Convertir None a 'NULL' string o mantener el valor
					vTeorica = vidaTeorica if vidaTeorica is not None else 'NULL'
					vUtil = vidaUtil if vidaUtil is not None else 'NULL'
					
					vHerr = [vTeorica, vUtil]  # Agregamos el número de herramienta
					vidaHerr.append(vHerr)
			except Exception as tag_error:
				# Si hay error en un tag específico, continuar con el siguiente
				system.util.getLogger("ScriptError").debug("Error en tag {}: {}".format(i + 1, str(tag_error)))
				continue
        
		return vidaHerr
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerCNCHerramienta: {}".format(str(e)))
		return [['NULL', 'NULL']]
		
def obtenerCNCHerramientaConNombre(celula, num):
    # Sinoptico.Data.General.obtenerCNCHerramientaConNombre(celula, num)
    """
    Obtener Vida Teorica, Vida Util y Nombre de una Maquina CNC
    Recorre tags individuales hasta el 120
    Retorna: [[vidaTeorica, vidaUtil, nombreHerramienta], ...]
    """
    try:
        tp = constantes.tag_provider
        
        # Construir las rutas base
        base_path1 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaVidaMax/HtaVidaMax"
        base_path2 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos/HtaVidaActual/HtaVidaActual"
        base_path3 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaNombre/HtaNombre"
        base_path4 = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaPosicion/HtaPosicion"
        
        # Crear listas para almacenar todas las rutas de tags
        paths_teorica = []
        paths_util = []
        paths_nombre = []
        paths_posicion = []
        
        # Generar todas las rutas de tags del 1 al 120
        for i in range(1, 121):  # Del 1 al 120
            paths_teorica.append(base_path1 + str(i))
            paths_util.append(base_path2 + str(i))
            paths_nombre.append(base_path3 + str(i))
            paths_posicion.append(base_path4 + str(i))
        
        # Combinar todas las rutas en una sola lista
        all_paths = paths_teorica + paths_util + paths_nombre + paths_posicion
        
        # Leer todos los tags de una vez
        data = system.tag.readBlocking(all_paths)
        
        vidaHerr = []
        
        # Procesar los resultados
        # Primeros 120: vida teorica
        # Siguientes 120: vida util
        # Últimos 120: nombre herramienta
        for i in range(120):
            try:
                vidaTeorica = data[i].value if data[i].quality.isGood() else None
                vidaUtil = data[i + 120].value if data[i + 120].quality.isGood() else None
                nombreHerramienta = data[i + 240].value if data[i + 240].quality.isGood() else None
                posicion = data[i + 360].value if data[i + 360].quality.isGood() else None
                
                # Solo agregar si al menos uno de los valores no es None
                if vidaTeorica is not None or vidaUtil is not None or nombreHerramienta is not None or posicion is not None:
                    # Convertir None a 'NULL' string o mantener el valor
                    vTeorica = vidaTeorica if vidaTeorica is not None else 'NULL'
                    vUtil = vidaUtil if vidaUtil is not None else 'NULL'
                    vNombre = nombreHerramienta if nombreHerramienta is not None else 'NULL'
                    pos = posicion if posicion is not None else 'NULL'
                    
                    nombre = vNombre + "-" + pos
                    
                    vHerr = [vTeorica, vUtil, nombre]
                    vidaHerr.append(vHerr)
            except Exception as tag_error:
                # Si hay error en un tag específico, continuar con el siguiente
                system.util.getLogger("ScriptError").debug("Error en tag {}: {}".format(i + 1, str(tag_error)))
                continue
        
        return vidaHerr
    except Exception as e:
        system.util.getLogger("ScriptError").error("obtenerCNCHerramienta: {}".format(str(e)))
        return [['NULL', 'NULL', 'NULL']]

def obtenerAlarmas(celula, num):
	# Sinoptico.Data.General.obtenerAlarmas(celula, num)
	"""
	Obtener Alarmas de una Maquina CNC
	"""
	try:
		tp = constantes.tag_provider
		
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Dinamicos"
		results = system.tag.browse(path, {"name":"Maq_Alarma_*"}) # Mira el numero de tags dentro de una carpeta, que empiecen por "Maq_Alarma_"
		total = len(results)
		print total
		
		alarmas = []
		for i in range(1, total + 1):
			path1 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Maq_Alarma_" + str(i) + "/Alarma" # Bool
			path2 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Maq_Alarma_" + str(i) + "/Valor_Detalle" # Codigo
			
			path = [path1, path2]
			
			data = system.tag.readBlocking(path)
			
			alarmaBool = data[0].value
			alarmaCodigo = data[1].value
			
			alarma = [alarmaBool, alarmaCodigo]
			
			alarmas.append(alarma)
		
		return alarmas
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerAlarmas: {}".format(str(e)))
		return [['NULL', 'NULL']]
	
def obtenerAutoContador(celula, referencia):
	# Sinoptico.Data.General.obtenerAutoContador(celula, referencia)
	"""
	Obtener contador de la maquina Auto restando el actual con el principio de turno. Consulta por BD
	"""
	try:
		tp = constantes.tag_provider
		database = constantes.Database_Sinoptico
		
		now = system.date.now()
		hour = system.date.getHour24(now)
		
		# Ajustar la hora de acuerdo al turno
		if 6 <= hour < 14:
		    # Turno 1: desde las 6 AM
		    newNow = system.date.setTime(now, 6, 0, 0)
		elif 14 <= hour < 22:
		    # Turno 2: desde las 2 PM
		    newNow = system.date.setTime(now, 14, 0, 0)
		elif 22 <= hour <= 23:
		    # Turno 3: desde las 10 PM
		    newNow = system.date.setTime(now, 22, 0, 0)
		else:
		    # Entre 12 AM y 6 AM → 10 PM del día anterior
		    yesterday = system.date.addDays(now, -1)
		    newNow = system.date.setTime(yesterday, 22, 0, 0)
		
		#---Obtenemos AssetsID------------------------------------
		#query = "SELECT AssetID FROM COEEasset "
		#query = query + "WHERE AssetName = 'C" + celula + "'"
		
		#data = system.db.runQuery(query, database)
		#AssetId = data[0][0]
		
		path = tp + "Variables/Datos_Celula/Celula" + str(celula) + "/AssetID"
		rutaTag = [path]
		AssetId = system.tag.readBlocking(rutaTag)[0].value
		
		# Obtenemos contador
		query = """
		    SELECT COUNT(*) FROM COEEproduction 
		    WHERE Job = ? 
		    AND AssetID = ? 
		    AND TimeComplete >= ?
		"""
		params = [str(referencia), str(AssetId), newNow]
		
		data = system.db.runPrepQuery(query, params, database)
		return data[0][0]
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerAutoContador: {}".format(str(e)))
		return 'NULL'
	
def elegirPLCContador(celula, num, idMaquina, referencia):
	# Sinoptico.Data.General.elegirPLCContador(celula, num, idMaquina, referencia)
	"""
	Script para elegir el tipo de Contador del PLC
	Dado que hay dos tipos(incluso 3 con la celula)
	Se usa para el sinoptico y para el Gateway Timer Script
	"""
	tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
	
	if tipoMaq == "CELULA":
		contador = Sinoptico.Data.General.obtenerAutoContador(celula, referencia)
	elif tipoMaq == "MARCADORA" or tipoMaq == "LAVADORA":
		contador = Sinoptico.Data.General.obtenerPLCContador_v2(celula, num, idMaquina)
	else:
		contador = Sinoptico.Data.General.obtenerPLCContador(celula, num, idMaquina)
	
	return contador

def obtenerPLCContador(celula, num, idMaquina):
    # Sinoptico.Data.General.obtenerPLCContador(celula, num, idMaquina)
    """
    Cuenta las piezas realizadas en el turno actual de una máquina PLC.
    Contabiliza parejas de 1 y 0 consecutivos (flanco descendente) desde el inicio del turno.
    
    Turnos:
    - Turno 1: 06:00 - 14:00 (6am - 2pm)
    - Turno 2: 14:00 - 22:00 (2pm - 10pm)
    - Turno 3: 22:00 - 06:00 (10pm - 6am)
    
    Args:
        celula: Número de celula
        num: Número de máquina
        idMaquina: ID de máquina para consulta BD (nombre de la máquina)
    
    Returns:
        piezasReales: Número de piezas completadas en el turno actual
    """
    import system.date
    
    database = constantes.Database_Tareas_2
    
    try:
        # --- CALCULAR INICIO DEL TURNO ACTUAL ---
        fechaActual = system.date.now()
        horaActual = system.date.getHour24(fechaActual)
        
        # Determinar a qué turno pertenece y calcular inicio
        if horaActual >= 6 and horaActual < 14:
            # Turno 1: 06:00 - 14:00
            inicioTurnoHora = 6
            diasAtras = 0
        elif horaActual >= 14 and horaActual < 22:
            # Turno 2: 14:00 - 22:00
            inicioTurnoHora = 14
            diasAtras = 0
        else:
            # Turno 3: 22:00 - 06:00
            if horaActual >= 22:
                # Después de las 22:00, inicio es hoy a las 22:00
                inicioTurnoHora = 22
                diasAtras = 0
            else:
                # Antes de las 06:00, inicio fue ayer a las 22:00
                inicioTurnoHora = 22
                diasAtras = 1
        
        # Calcular fecha de inicio del turno
        fechaBase = system.date.addDays(fechaActual, -diasAtras)
        fechaBase = system.date.midnight(fechaBase)
        fechaInicioTurno = system.date.addHours(fechaBase, inicioTurnoHora)
        
        # --- OBTENER ID MAQUINA DE LA BASE DE DATOS ---
        query = """
            SELECT IdMaquina FROM CMaquinas
            WHERE Maquina = ?
        """
        params = [str(idMaquina)]
        
        data = system.db.runPrepQuery(query, params, database)
        if len(data) == 0:
            return 0
            
        bdIdMaq = data[0][0]
        
        # --- CONSULTAR DATOS DE ENCICLO DESDE INICIO DE TURNO ---
        query = """
        SELECT Fecha, Valor
        FROM CDatosMaquina
        WHERE IdTipoDatoMaquina = 3 
            AND IdMaquina = ?
            AND Fecha >= ? 
            AND Fecha <= ?
        ORDER BY Fecha ASC
        """
        params = [str(bdIdMaq), fechaInicioTurno, fechaActual]
        
        datos = system.db.runPrepQuery(query, params, database)
        
        if len(datos) == 0:
            return 0
        
        # --- CONTAR PAREJAS DE 1 Y 0 CONSECUTIVOS (FLANCO DESCENDENTE) ---
        piezasReales = 0
        
        for i in range(len(datos) - 1):
            valorActual = datos[i]['Valor']
            valorSiguiente = datos[i + 1]['Valor']
            
            # Detectar flanco descendente: 1 seguido de 0
            if valorActual == '1' and valorSiguiente == '0':
                piezasReales += 1
        
        return piezasReales
        
    except Exception as e:
    	referencia = Sinoptico.Data.General.obtenerReferencia(celula)
        valor = Sinoptico.Data.General.obtenerAutoContador(celula, referencia)
        return valor

def obtenerPLCContador_v2(celula, num, idMaquina):
    # Sinoptico.Data.General.obtenerPLCContador(celula, num, idMaquina)
    """
    PARA MARCADORA Y LAVADORA Y BIN PICKING!!!!! IdTipoMaquina = 2
    Cuenta las piezas realizadas en el turno actual de una máquina PLC. 
    Contabiliza parejas de 1 y 0 consecutivos (flanco descendente) desde el inicio del turno.
    
    Turnos:
    - Turno 1: 06:00 - 14:00 (6am - 2pm)
    - Turno 2: 14:00 - 22:00 (2pm - 10pm)
    - Turno 3: 22:00 - 06:00 (10pm - 6am)
    
    Args:
        celula: Número de celula
        num: Número de máquina
        idMaquina: ID de máquina para consulta BD (nombre de la máquina)
    
    Returns:
        piezasReales: Número de piezas completadas en el turno actual
    """
    import system.date
    
    database = constantes.Database_Tareas_2
    
    try:
        # --- CALCULAR INICIO DEL TURNO ACTUAL ---
        fechaActual = system.date.now()
        horaActual = system.date.getHour24(fechaActual)
        
        # Determinar a qué turno pertenece y calcular inicio
        if horaActual >= 6 and horaActual < 14:
            # Turno 1: 06:00 - 14:00
            inicioTurnoHora = 6
            diasAtras = 0
        elif horaActual >= 14 and horaActual < 22:
            # Turno 2: 14:00 - 22:00
            inicioTurnoHora = 14
            diasAtras = 0
        else:
            # Turno 3: 22:00 - 06:00
            if horaActual >= 22:
                # Después de las 22:00, inicio es hoy a las 22:00
                inicioTurnoHora = 22
                diasAtras = 0
            else:
                # Antes de las 06:00, inicio fue ayer a las 22:00
                inicioTurnoHora = 22
                diasAtras = 1
        
        # Calcular fecha de inicio del turno
        fechaBase = system.date.addDays(fechaActual, -diasAtras)
        fechaBase = system.date.midnight(fechaBase)
        fechaInicioTurno = system.date.addHours(fechaBase, inicioTurnoHora)
        
        # --- OBTENER ID MAQUINA DE LA BASE DE DATOS ---
        query = """
            SELECT IdMaquina FROM CMaquinas
            WHERE Maquina = ?
        """
        params = [str(idMaquina)]
        
        data = system.db.runPrepQuery(query, params, database)
        if len(data) == 0:
            return 0
            
        bdIdMaq = data[0][0]
        
        # --- CONSULTAR DATOS DE ENCICLO DESDE INICIO DE TURNO ---
        query = """
        SELECT Fecha, Valor
        FROM CDatosMaquina
        WHERE IdTipoDatoMaquina = 2 
            AND IdMaquina = ?
            AND Fecha >= ? 
            AND Fecha <= ?
        ORDER BY Fecha ASC
        """
        params = [str(bdIdMaq), fechaInicioTurno, fechaActual]
        
        datos = system.db.runPrepQuery(query, params, database)
        
        if len(datos) == 0:
            return 0
        
        # --- CONTAR PAREJAS DE 1 Y 0 CONSECUTIVOS (FLANCO DESCENDENTE) ---
        piezasReales = 0
        
        for i in range(len(datos) - 1):
            valorActual = datos[i]['Valor']
            valorSiguiente = datos[i + 1]['Valor']
            
            # Detectar flanco descendente: 1 seguido de 0
            if valorActual == '1' and valorSiguiente == '0':
                piezasReales += 1
        
        return piezasReales
        
    except Exception as e:
    	referencia = Sinoptico.Data.General.obtenerReferencia(celula)
        valor = Sinoptico.Data.General.obtenerAutoContador(celula, referencia)
        return valor

def obtenerAutoHerramienta(celula, num):
	# Sinoptico.Data.General.obtenerAutoHerramienta(celula, num)
	"""
	Obtener Vida Teorica y Vida Util de una Maquina Auto
	"""
	try:
		tp = constantes.tag_provider
		
		path1 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Cuasiconstantes/HtaVidaMax" # Vida Teorica
		path2 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/HtaVidaActual" # Vida Util
		path = [path1, path2]
		
		data = system.tag.readBlocking(path)
		
		vidaTeorica = data[0].value
		vidaUtil = data[1].value
		
		vidaHerr = [vidaTeorica, vidaUtil]
		
		return vidaHerr
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerAutoHerramienta: {}".format(str(e)))
		return ['NULL', 'NULL']
		
def obtenerAutoHerramientaConNombre(celula, num):
	# Sinoptico.Data.General.obtenerAutoHerramientaConNombre(celula, num)
	"""
	Obtener Vida Teorica y Vida Util de una Maquina Auto
	"""
	try:
		tp = constantes.tag_provider
		
		path1 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Cuasiconstantes/HtaVidaMax" # Vida Teorica
		path2 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/HtaVidaActual" # Vida Util
		path = [path1, path2]
		
		data = system.tag.readBlocking(path)
		
		vidaTeorica = data[0].value
		vidaUtil = data[1].value
		
		vidaHerr = [vidaTeorica, vidaUtil, "HERRAMIENTA"]
		
		return vidaHerr
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerAutoHerramienta: {}".format(str(e)))
		return ['NULL', 'NULL', 'NULL']
	
def obtenerSaturacion(celula, num):
	# Sinoptico.Data.General.obtenerSaturacion(celula, num)
	"""
	Obtener Saturacion y Presaturacion segun tags
	"""
	try:
		tp = constantes.tag_provider
		saturacion = []
		
		path1 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Saturacion/Pre" # preSaturacion
		path2 = tp + "Celula" + celula + "/Maq_" +  str(num) + "/Datos_Dinamicos/Saturacion/Sat" # Saturacion
			
		path = [path1, path2]
		
		data = system.tag.readBlocking(path)
		
		preSat = data[0].value
		Sat = data[1].value
		
		saturacion = [preSat, Sat]
		
		return saturacion
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerSaturacion: {}".format(str(e)))
		return ['NULL', 'NULL']
	
def obtenerIDMaquinaOriginal(celula, num):
	# Sinoptico.Data.General.obtenerIDMaquinaOriginal(celula, num)
	"""
	Obtener el id de la maquina de la célula segun un tag.
	Se devuelve el valor tal cual sinn procesar
	"""
	try:
		tp = constantes.tag_provider
		path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Constantes/ID_Maquina"
		path = [path]
		
		data = system.tag.readBlocking(path)
		valor = data[0].value
		
		return valor
		
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerIDMaquina: {}".format(str(e)))
		return 'NULL'
	

def obtenerConexion(celula, num):
	# Sinoptico.Data.General.obtenerConexion(celula, num)
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
		
	
def obtenerCNCHtaNombre(celula, num):
	# Sinoptico.Data.General.obtenerCNCHtaNombre(celula, num)
    """
    Obtener solo los nombres de las herramientas (sin número)
    """
    try:
        tp = constantes.tag_provider
        
        base_path = tp + "Celula" + celula + "/Maq_" + str(num) + "/Datos_Cuasiconstantes/HtaNombre/HtaNombre"
        
        paths_nombres = []
        for i in range(1, 121):
            paths_nombres.append(base_path + str(i))
        
        data = system.tag.readBlocking(paths_nombres)
        
        nombres = []
        
        for i in range(120):
            try:
                if data[i].quality.isGood() and data[i].value is not None:
                    nombre_valor = data[i].value
                    if str(nombre_valor).strip() != "":
                        nombres.append(nombre_valor)
            except Exception as tag_error:
                system.util.getLogger("ScriptError").debug("Error en tag nombre {}: {}".format(i + 1, str(tag_error)))
                continue
        
        return nombres
    except Exception as e:
        system.util.getLogger("ScriptError").error("obtenerCNCHtaNombreSolo: {}".format(str(e)))
        return ['NULL']
    
def obtenerNumeroMaquina(celula, maquina):
    # Sinoptico.Data.General.obtenerNumeroMaquina(celula, maquina)
    """
    Busca el número de máquina en base al nombre (tag Tipo) segun la celula y el nombre de la maquina
    Devuelve el número (ej: 1, 2, 3...) o None si no existe.
    """
    try:
        tp = constantes.tag_provider
        path = tp + "Celula" + str(celula)
        
        if maquina == "CELULA":
        	maquina = "CELULA_AUTOMATICA"

        # Contar cuántas máquinas hay en la celula
        total = len(system.tag.browse(path, {"name": "Maq_*"}))

        for num in range(1, total + 1):
            try:
                tagTipo = "{}/Maq_{}/Datos_Constantes/Tipo".format(path, num)
                valor = system.tag.readBlocking([tagTipo])[0].value

                if str(valor) == str(maquina):
                    return num  # Encontrado → devolvemos el número

            except Exception as e:
                system.util.getLogger("ScriptWarn").warn(
                    "Error leyendo Tipo en Celula {} Maq_{}: {}".format(celula, num, str(e))
                )
                continue

        # No encontrado
        return None

    except Exception as e:
        system.util.getLogger("ScriptError").error(
            "obtenerNumeroMaquina Celula {}: {}".format(celula, str(e))
        )
        return None
 