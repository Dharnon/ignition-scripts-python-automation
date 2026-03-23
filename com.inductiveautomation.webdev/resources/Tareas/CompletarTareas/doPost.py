def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se usa para completar tareas.
	Se debe proporcionar. Celula, maquina y tarea.
	"""
	#--------------------------------------------------------------------------------
	#---PARAMETROS-------------------------------------------------------------------
	#--------------------------------------------------------------------------------
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "Data no proporcionada"}}
	    
		celula = data['celula']
		tipoMaq = data['maquina']
		tarea = data['tarea']
		referencia = Sinoptico.Data.General.obtenerReferencia(celula) # Obtenemos referencia
		num = Sinoptico.Data.General.obtenerNumeroMaquina(celula, tipoMaq) # Obtenemos el num
		manual = 1 # Significa que ha sido completado de manera manual
		
		completado = Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
		
		logger.info("Completado")
		
		if completado:
			return {
		        "json": {
		            "completado": "Tarea completada"
		        }
		    }
		else:
			return {"json": {"error": "Tarea no encontrada"}}
	

	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}