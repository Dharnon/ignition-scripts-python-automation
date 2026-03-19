def desviacionesMaquina():
	# Tareas.Data.Desviacion.desviacionesMaquina()
	"""
	Repasa los tiempos de produccion por maquina de cada celula.
	Si hay alguna desviacion actualiza el dataset de tareas
	"""
	#---PARAMETROS--------------------------------------------------
	celulas = constantes.celulas
	tp = constantes.tag_provider
	logger = system.util.getLogger('Desviacion Maquina')
	#---------------------------------------------------------------
	
	for celula in celulas:
		print "============================ CELULA " + str(celula) + " ==========================================="
		# Numero de maquinas por celula
		path = tp + "Celula" + celula
		total = len(system.tag.browse(path, {"name": "Maq_*"})) # Mira el numero de tags dentro de una carpeta, que empiecen por "Maq_"
		logger.info("Celula: " + str(celula))
		for num in range(1, total + 1):
			try:
				conexion = Sinoptico.Data.General.obtenerConexion(celula, num)
				print "------ Numero: " + str(num) + " ------"
				print "------ Conexion: " + str(conexion) + " ------"
				tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)	# Mira el tipo de maquina para saber si es el plc general de automatica
				if conexion == 'Good':
					logger.info("Maquina: " + str(tipoMaq))
					plc_cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num) 		# Mira si es tipo plc
					referencia = Sinoptico.Data.General.obtenerReferencia(celula)				# Obtener referencia
					rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq)		# Obtener ritmo de produccion teorico
					print "------------------------------ " + str(tipoMaq) + " / num: " + str(num) + " / rpt: " + str(rpt) + " -----------------------------------------"
					#---Maquinas tipo PLC
					if plc_cnc == 0:
						if tipoMaq == "CELULA":
							desfaseMin = Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt)
							path = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_1/desfaseMin"
							system.tag.writeBlocking(path, desfaseMin)
							print "Desfase celula automatica: " + str(desfaseMin)
							logger.info("Desfase celula automatica: " + str(desfaseMin))
							if desfaseMin >= 1:
								Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)
						elif tipoMaq == "BROCHADORA" or tipoMaq == "AFEITADORA":
							desfaseMin = Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_v2(celula, num, referencia, rpt)
							logger.info("Desfase PLC v2: " + str(desfaseMin))
							print "Desfase PLC v2: " + str(desfaseMin)
							if desfaseMin >= 1:
								Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)
						elif tipoMaq == "MARCADORA" or tipoMaq == "LAVADORA" or tipoMaq == "BIN PICKING":
							desfaseMin = Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_v3(celula, num, referencia, rpt)
							logger.info("Desfase PLC v3: " + str(desfaseMin))
							print "Desfase PLC v3: " + str(desfaseMin)
							if desfaseMin >= 1:
								Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)
						else:
							idMaq = Sinoptico.Data.General.obtenerIDMaquinaOriginal(celula, num)		# Obtener id maquina segun el tag
							if idMaq != 'NULL':
								desfaseMin = Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC(celula, num, idMaq, rpt)	# Obtener ultimo registro de la pieza (ritmo produccion real)
								if desfaseMin >= 1:
									Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)	# Realizar la actualizacion del desfase de la maquina
									logger.info("Desfase PLC: " + str(desfaseMin))
									print "Desfase PLC: " + str(desfaseMin)
					#---Maquinas tipo CNC
					elif plc_cnc == 1:
						desfaseMin = Tareas.Data.Desviacion.obtenerUltimoRegistro_CNC(celula, num, rpt)	# Obtener el desfase en minutos de una maquina CNC
						if desfaseMin >= 1:
							Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)	# Realizar la actualizacion del desfase de la maquina
							logger.info("Desfase CNC: " + str(desfaseMin))
							print "Desfase CNC: " + str(desfaseMin)
				else:
					Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num)
			except Exception as e:
				logger.error("----------ERROR dentro de Tareas.Data.Desviacion.desviacionesMaquina()-------------")
				continue
	return True


def obtenerDesviacionMaquinaAuto(celula, num):
	# Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num)
	"""
	FUNCION AUXILIAR para las desviaciones de las maquinas
	Leemos el valor del desfase de la maquina automatica para corregir desvios del resto de las maquinas que no puedan obtener el desfase
	Ademas añade la fecha al desviacion de Piezas para los siguientes desfases
	"""
	#---PARAMETROS----------------------------------------------
	tp = constantes.tag_provider
	#-----------------------------------------------------------
	try:
		conexion = Sinoptico.Data.General.obtenerConexion(celula, 1)
		tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
		if conexion == 'Good':
			path = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_1/desfaseMin"
			desfaseMin = system.tag.readBlocking(path)[0].value
			print ("Entro en Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto("+ str(celula) + " ," + str(num) + ") con un desfase de: " + str(desfaseMin))
			if desfaseMin >= 1:
				Tareas.Data.General.modificarTiemposMaquinas(celula, tipoMaq, desfaseMin)
			
			# Guardamos la nueva fecha de las piezas
			pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
			fechaActual = system.date.now()
			
			dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
			columnNames = ["fecha", "piezas"]
			
			if dsHistorico.getRowCount() == 0:
				newData = [[fechaActual, 0]]
			else:
				piezasAnterior = dsHistorico.getValueAt(0, "piezas")
	        	newData = [[fechaActual, piezasAnterior]]
	        newDataset = system.dataset.toDataSet(columnNames, newData)
	        system.tag.writeBlocking([pathTagHistorico], [newDataset])
		
		return True
	except Exception as e:
		logger.error("Error en Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num): " + str(e))
		return 0

def obtenerUltimoRegistro_PLC(celula, num, idMaquina, rpt):
    # Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC(celula, num, idMaquina, rpt)
    """
    Lee las parejas de 1 y 0 desde la última fecha registrada y cuenta las piezas totales.
    Aplica la misma lógica de cálculo que obtenerUltimoRegistro_CNC().
    
    Args:
        celula: Número de celula
        num: Número de máquina
        idMaquina: ID de máquina para consulta BD
        rpt: Ritmo de producción teórico
    
    Returns:
        minDesfase: Minutos de desfase calculados
    """
    #---PARAMETROS-----------------------------------------------------
    tp = constantes.tag_provider
    pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
    database = constantes.Database_Tareas_2
    logger = system.util.getLogger("Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC")
    
    try:
        # Leer valores actuales
        fechaActual = system.date.now()
        
        # Leer dataset del tag (ultimo valor)
        dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
        columnNames = ["fecha", "piezas"]
        
        # Si está vacío o no tiene datos, crear nueva fila con 0 piezas
        if dsHistorico.getRowCount() == 0:
            newData = [[fechaActual, 0]]
            newDataset = system.dataset.toDataSet(columnNames, newData)
            system.tag.writeBlocking([pathTagHistorico], [newDataset])
        else:
            # Obtener fecha anterior del dataset
            fechaAnterior = dsHistorico.getValueAt(0, "fecha")
            piezasAnterior = dsHistorico.getValueAt(0, "piezas")
            
            # Diferencia de tiempo
            secDiferencia = system.date.secondsBetween(fechaAnterior, fechaActual)
            minDiferencia = secDiferencia / 60.0
            print "Diferencia en minutos: " + str(minDiferencia)
        
        #-------------------------------------------------------------------
        
        # Obtenemos Id Maquina segun base de datos
        query = """
            SELECT IdMaquina FROM CMaquinas
            WHERE Maquina = ?
        """
        params = [str(idMaquina)]
        
        data = system.db.runPrepQuery(query, params, database)
        if len(data) == 0:
            logger.error("No se encontró IdMaquina para: " + str(idMaquina))
            print ("No se encontró IdMaquina para: " + str(idMaquina))
            Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
            return 0
            
        bdIdMaq = data[0][0] # Base de datos Id Maquina
        
        # Consultamos en base de datos desde la fecha anterior hasta ahora
        query = """
        SELECT Fecha, Valor
        FROM CDatosMaquina
        WHERE IdTipoDatoMaquina = 3 AND IdMaquina = ?
        AND Fecha >= ? AND Fecha <= ?
        ORDER BY Fecha DESC
        """
        params = [str(bdIdMaq), fechaAnterior, fechaActual]
        
        datos = system.db.runPrepQuery(query, params, database)
        
        # Contar todas las parejas de 1 y 0 (piezas completadas)
        piezasReales = 0
        ultimaFechaPieza = fechaAnterior
        
        for i in range(len(datos) - 1):
            if datos[i]['Valor'] == '1' and datos[i + 1]['Valor'] == '0':
                piezasReales += 1
                # Guardamos la fecha de la última pieza encontrada
                if datos[i]['Fecha'] > ultimaFechaPieza:
                    ultimaFechaPieza = datos[i]['Fecha']
        
        print "Piezas reales encontradas: " + str(piezasReales)
        
        # Calcular piezas teóricas que deberíamos haber hecho
        piezasTeoricas = minDiferencia / rpt
        print "Piezas teoricas: " + str(piezasTeoricas)
        
        # Desfase de piezas
        piezasDesfase = piezasTeoricas - piezasReales
        print "Piezas desfase: " + str(piezasDesfase)
        
        if piezasDesfase >= 1:
            # Tiempo de desfase (min)
            minDesfase = piezasDesfase * rpt
            print "Minutos desfase: " + str(minDesfase)
        else:
            minDesfase = 0
        
        # Actualizar dataset con la fecha actual y las piezas acumuladas
        piezasActualizadas = piezasAnterior + piezasReales
        newData = [[fechaActual, piezasActualizadas]]
        newDataset = system.dataset.toDataSet(columnNames, newData)
        system.tag.writeBlocking([pathTagHistorico], [newDataset])
        
        logger.info("PLC C: " + str(celula) + " / M: " + str(num) + " - Piezas reales: " + str(piezasReales) + ", Desfase: " + str(minDesfase) + " min")
        
        return minDesfase
        
    except Exception as e:
        logger.error("Error: " + str(e))
        Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
        return 0

def obtenerUltimoRegistro_CNC(celula, num, rpt):
	# Tareas.Data.Desviacion.obtenerUltimoRegistro_CNC(celula, num, rpt)
	"""
	Lee un tag tipo dataset con dos columnas: fecha y piezas.
	Compara el valor actual con el almacenado y lo actualiza.
	rpt: ritmo de produccion teorico
	"""
	# PARAMETROS-------------------------------------------------------------------
	tp = constantes.tag_provider
	pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
	pathTagContador = tp + "Celula" + str(celula) + "/Maq_" + str(num) + "/Datos_Dinamicos/ContadorPiezas/Pos1"
	
	try:
	
		# Leer valores actuales
		fechaActual = system.date.now()
		piezasActuales = system.tag.readBlocking([pathTagContador])[0].value
		
		# Leer dataset del tag (ultimo valor)
		dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
		columnNames = ["fecha", "piezas"]
		
		# Si está vacío o no tiene datos, crear nueva fila
		if dsHistorico.getRowCount() == 0:
			newData = [[fechaActual, piezasActuales]]
		else:
			# Comparar valores actuales con los del dataset
			fechaAnterior = dsHistorico.getValueAt(0, "fecha")
			piezasAnterior = dsHistorico.getValueAt(0, "piezas")
			
			# Diferencia de tiempo
			secDiferencia = system.date.secondsBetween(fechaAnterior, fechaActual)
			minDiferencia = secDiferencia / 60.0
			print "Diferencia en minutos: "
			print minDiferencia
			# Diferencia de piezas real en el espacio de tiempo
			piezasReal = piezasActuales - piezasAnterior
			if piezasReal < 0:
				piezasReal = piezasReal + 2000 # La tag de piezas cuanta de 0 a 1999. Si el valor de negativo hay que sumarle 2000 para que de bien
			print "Piezas reales: "
			print piezasReal
			
			# Piezas teoricas que deberiamos llevar
			piezasTeoricas = minDiferencia / rpt
			print "Piezas teoricas: "
			print piezasTeoricas
			
			# Desfase de piezas
			piezasDesfase = piezasTeoricas - piezasReal
			print "Piezas desfase"
			print piezasDesfase
			
			if piezasDesfase >= 1:
				# Tiempo de desfase (min)
				minDesfase = piezasDesfase * rpt
				print "Minutos desfase"
				print minDesfase
			else:
				minDesfase = 0
	
			# Crear nueva fila con valores actuales
			newData = [[fechaActual, piezasActuales]]
		
		# Crear nuevo dataset y escribirlo
		newDataset = system.dataset.toDataSet(columnNames, newData)
		system.tag.writeBlocking([pathTagHistorico], [newDataset])
		
		return minDesfase
	except Exception as e:
		system.util.getLogger("Tareas.Data.Desviacion.obtenerUltimoRegistro_CNC(celula, num, rpt)").error("Error: " + str(e))
		Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
		return 0
	
def obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt):
	# Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt)
	"""
	Lee un tag tipo dataset con dos columnas: fecha y piezas.
	Compara el valor actual con el almacenado y lo actualiza.
	rpt: ritmo de produccion teorico
	"""
	# PARAMETROS-------------------------------------------------------------------
	tp = constantes.tag_provider
	pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
	valor_negativo = False
	minDesfase = 0
	
	try:
		# Leer valores actuales
		fechaActual = system.date.now()
		piezasActuales = Tareas.Data.TagsMaquina.piezasMaquinaTurno_Automatica(celula, referencia)
		
		# Leer dataset del tag (ultimo valor)
		dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
		columnNames = ["fecha", "piezas"]
		
		# Si está vacío o no tiene datos, crear nueva fila
		if dsHistorico.getRowCount() == 0:
			newData = [[fechaActual, piezasActuales]]
		else:
			# Comparar valores actuales con los del dataset
			fechaAnterior = dsHistorico.getValueAt(0, "fecha")
			piezasAnterior = dsHistorico.getValueAt(0, "piezas")
			
			# Diferencia de tiempo
			secDiferencia = system.date.secondsBetween(fechaAnterior, fechaActual)
			minDiferencia = secDiferencia / 60.0
			print "Diferencia en minutos: "
			print minDiferencia
			# Diferencia de piezas real en el espacio de tiempo
			piezasReal = piezasActuales - piezasAnterior
			if piezasReal < 0:
				valor_negativo = True
			print "Piezas reales: "
			print piezasReal
			
			# Piezas teoricas que deberiamos llevar
			piezasTeoricas = minDiferencia / rpt
			print "Piezas teoricas: "
			print piezasTeoricas
			
			# Desfase de piezas
			if valor_negativo:
				piezasDesfase = 0
			else:
				piezasDesfase = piezasTeoricas - piezasReal
			print "Piezas desfase"
			print piezasDesfase
			
			if piezasDesfase >= 1:
				# Tiempo de desfase (min)
				minDesfase = piezasDesfase * rpt
				print "Minutos desfase"
				print minDesfase
			else:
				minDesfase = 0
	
			# Crear nueva fila con valores actuales
			newData = [[fechaActual, piezasActuales]]
		
		# Crear nuevo dataset y escribirlo
		newDataset = system.dataset.toDataSet(columnNames, newData)
		system.tag.writeBlocking([pathTagHistorico], [newDataset])
		
		return minDesfase
	except Exception as e:
		system.util.getLogger("Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_Auto(celula, num, referencia, rpt)").error("Error: " + str(e))
		Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
		return 0
	
def obtenerUltimoRegistro_PLC_v2(celula, num, referencia, rpt):
	# Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_v2(celula, num, referencia, rpt)
	"""
	Lee un tag tipo dataset con dos columnas: fecha y piezas.
	Compara el valor actual con el almacenado y lo actualiza.
	rpt: ritmo de produccion teorico
	HECHO PARA BROCHADORA Y AFEITADORA
	"""
	# PARAMETROS-------------------------------------------------------------------
	tp = constantes.tag_provider
	pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
	valor_negativo = False
	minDesfase = 0
	
	try:
		# Leer valores actuales
		fechaActual = system.date.now()
		pathPiezasActuales = tp + "Celula" + str(celula) + "/Maq_" + str(num) + "/Datos_Dinamicos/HtaVidaActual"
		piezasActuales = system.tag.readBlocking([pathPiezasActuales])[0].value
		
		# Leer dataset del tag (ultimo valor)
		dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
		columnNames = ["fecha", "piezas"]
		
		# Si está vacío o no tiene datos, crear nueva fila
		if dsHistorico.getRowCount() == 0:
			newData = [[fechaActual, piezasActuales]]
		else:
			# Comparar valores actuales con los del dataset
			fechaAnterior = dsHistorico.getValueAt(0, "fecha")
			piezasAnterior = dsHistorico.getValueAt(0, "piezas")
			
			# Diferencia de tiempo
			secDiferencia = system.date.secondsBetween(fechaAnterior, fechaActual)
			minDiferencia = secDiferencia / 60.0
			print "Diferencia en minutos: "
			print minDiferencia
			# Diferencia de piezas real en el espacio de tiempo
			print piezasActuales
			print piezasAnterior
			piezasReal = piezasActuales - piezasAnterior
			if piezasReal < 0:
				valor_negativo = True
			print "Piezas reales: "
			print piezasReal
			
			# Piezas teoricas que deberiamos llevar
			piezasTeoricas = minDiferencia / rpt
			print "Piezas teoricas: "
			print piezasTeoricas
			
			# Desfase de piezas
			if valor_negativo:
				piezasDesfase = 0
			else:
				piezasDesfase = piezasTeoricas - piezasReal
			print "Piezas desfase"
			print piezasDesfase
			
			if piezasDesfase >= 1:
				# Tiempo de desfase (min)
				minDesfase = piezasDesfase * rpt
				print "Minutos desfase"
				print minDesfase
			else:
				minDesfase = 0
	
			# Crear nueva fila con valores actuales
			newData = [[fechaActual, piezasActuales]]
		
		# Crear nuevo dataset y escribirlo
		newDataset = system.dataset.toDataSet(columnNames, newData)
		system.tag.writeBlocking([pathTagHistorico], [newDataset])
		
		return minDesfase

	except Exception as e:
		system.util.getLogger("Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_v2(celula, num, referencia, rpt)").error("Error: " + str(e))
		Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
		return 0
		
def obtenerUltimoRegistro_PLC_v3(celula, num, idMaquina, rpt):
    # Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC_v3(celula, num, idMaquina, rpt)
    """
    SE USA PARA MARCADORA Y LAVADORA. IdTipoDatoMaquina = 2
    Lee las parejas de 1 y 0 desde la última fecha registrada y cuenta las piezas totales.
    Aplica la misma lógica de cálculo que obtenerUltimoRegistro_CNC().
    
    Args:
        celula: Número de celula
        num: Número de máquina
        idMaquina: ID de máquina para consulta BD
        rpt: Ritmo de producción teórico
    
    Returns:
        minDesfase: Minutos de desfase calculados
    """
    #---PARAMETROS-----------------------------------------------------
    tp = constantes.tag_provider
    pathTagHistorico = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/DesviacionPiezas"
    database = constantes.Database_Tareas_2
    logger = system.util.getLogger("Tareas.Data.Desviacion.obtenerUltimoRegistro_PLC")
    
    try:
        # Leer valores actuales
        fechaActual = system.date.now()
        
        # Leer dataset del tag (ultimo valor)
        dsHistorico = system.tag.readBlocking([pathTagHistorico])[0].value
        columnNames = ["fecha", "piezas"]
        
        # Si está vacío o no tiene datos, crear nueva fila con 0 piezas
        if dsHistorico.getRowCount() == 0:
            newData = [[fechaActual, 0]]
            newDataset = system.dataset.toDataSet(columnNames, newData)
            system.tag.writeBlocking([pathTagHistorico], [newDataset])
        else:
            # Obtener fecha anterior del dataset
            fechaAnterior = dsHistorico.getValueAt(0, "fecha")
            piezasAnterior = dsHistorico.getValueAt(0, "piezas")
            
            # Diferencia de tiempo
            secDiferencia = system.date.secondsBetween(fechaAnterior, fechaActual)
            minDiferencia = secDiferencia / 60.0
            print "Diferencia en minutos: " + str(minDiferencia)
        
        #-------------------------------------------------------------------
        
        # Obtenemos Id Maquina segun base de datos
        query = """
            SELECT IdMaquina FROM CMaquinas
            WHERE Maquina = ?
        """
        params = [str(idMaquina)]
        
        data = system.db.runPrepQuery(query, params, database)
        if len(data) == 0:
            logger.error("No se encontró IdMaquina para: " + str(idMaquina))
            print ("No se encontró IdMaquina para: " + str(idMaquina))
            Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
            return 0
            
        bdIdMaq = data[0][0] # Base de datos Id Maquina
        
        # Consultamos en base de datos desde la fecha anterior hasta ahora
        query = """
        SELECT Fecha, Valor
        FROM CDatosMaquina
        WHERE IdTipoDatoMaquina = 2 AND IdMaquina = ?
        AND Fecha >= ? AND Fecha <= ?
        ORDER BY Fecha DESC
        """
        params = [str(bdIdMaq), fechaAnterior, fechaActual]
        
        datos = system.db.runPrepQuery(query, params, database)
        
        # Contar todas las parejas de 1 y 0 (piezas completadas)
        piezasReales = 0
        ultimaFechaPieza = fechaAnterior
        
        for i in range(len(datos) - 1):
            if datos[i]['Valor'] == '1' and datos[i + 1]['Valor'] == '0':
                piezasReales += 1
                # Guardamos la fecha de la última pieza encontrada
                if datos[i]['Fecha'] > ultimaFechaPieza:
                    ultimaFechaPieza = datos[i]['Fecha']
        
        print "Piezas reales encontradas: " + str(piezasReales)
        
        # Calcular piezas teóricas que deberíamos haber hecho
        piezasTeoricas = minDiferencia / rpt
        print "Piezas teoricas: " + str(piezasTeoricas)
        
        # Desfase de piezas
        piezasDesfase = piezasTeoricas - piezasReales
        print "Piezas desfase: " + str(piezasDesfase)
        
        if piezasDesfase >= 1:
            # Tiempo de desfase (min)
            minDesfase = piezasDesfase * rpt
            print "Minutos desfase: " + str(minDesfase)
        else:
            minDesfase = 0
        
        # Actualizar dataset con la fecha actual y las piezas acumuladas
        piezasActualizadas = piezasAnterior + piezasReales
        newData = [[fechaActual, piezasActualizadas]]
        newDataset = system.dataset.toDataSet(columnNames, newData)
        system.tag.writeBlocking([pathTagHistorico], [newDataset])
        
        logger.info("PLC C: " + str(celula) + " / M: " + str(num) + " - Piezas reales: " + str(piezasReales) + ", Desfase: " + str(minDesfase) + " min")
        
        return minDesfase
        
    except Exception as e:
        logger.error("Error: " + str(e))
        Tareas.Data.Desviacion.obtenerDesviacionMaquinaAuto(celula, num) # Error: usamos la desviacion de la maquina automatica
        return 0