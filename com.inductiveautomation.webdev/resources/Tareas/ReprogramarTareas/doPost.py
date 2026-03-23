def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se usa para reprogramar tareas.
	Se debe proporcionar. Celula, maquina y tarea.
	"""
	#--------------------------------------------------------------------------------
	#---PARAMETROS-------------------------------------------------------------------
	#--------------------------------------------------------------------------------
	logger = system.util.getLogger("ReprogramarTareas")
	
	try:
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "Data no proporcionada"}}
	    
		celula = data['celula']
		tipoMaq = data['maquina']
		tarea = data['tarea']
		referencia = Sinoptico.Data.General.obtenerReferencia(celula)
		num = Sinoptico.Data.General.obtenerNumeroMaquina(celula, tipoMaq)
		rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq) # Obtenemos el ritmo de produccion
		ocurrencia = Tareas.Data.General.obtenerOcurrencia(celula, referencia, tipoMaq, tarea) # Obtenemos ocurrencia
		contador = Tareas.Data.TagsMaquina.completarTarea(celula, num, tarea)
	
		# Recalculamos los tiempo de esa tarea segun el contador
		if contador == 0: # Se ha completado antes de lo esperado, se recalcula desde ahora
			Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 0) # Actualiza el resto de tareas
			logger.info("REESTRUCTURADA, base 0")
		elif contador == -1: # Contador mayor que ocurrencia hay que completar la tarea de nuevo
			Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, -1) # Actualiza el resto de tareas
			logger.info("REESTRUCTURADA, YA!")
		elif contador == -2:
			logger.info("Error al realizar la comprobacion del contador en el tag")
			Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 0) # Actualiza el resto de tareas
			logger.info("ERROR pero reestructurada")
		else: # Contador ya ha empezado la siguiente asi que hay que tener en cuenta esas piezas para el siguiente
			nuevoTiempo = (ocurrencia-contador)*rpt
			Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, nuevoTiempo) # Actualiza el resto de tareas
			logger.info("REESTRUCTURADA, teniendo en cuenta el contador")
		
		logger.info("Completado")
		
		return {
	        "json": {
	            "completado": "Tarea reprogramada"
	        }
	    }
	
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}