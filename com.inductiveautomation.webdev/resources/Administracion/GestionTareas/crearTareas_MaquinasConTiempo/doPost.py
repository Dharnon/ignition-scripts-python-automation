def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Esto se usa para cuando creas una tarea haga la comprobacion de las maquinas 
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		# DATOS QUE RECIBIMOS------------------------------------------------
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "No data proporcionada"}}
	    
		celula = data['celula']
		logger.info("Celula: " + str(celula))
		referencia = data['referencia']
		logger.info("Referencia: " + str(referencia))
		
		dataset = Tareas.Data.Teorico.obtenerTiemposMaquina_crearTareas(celula, referencia)
		logger.info("Dataset: " + str(dataset))
		
		return {"json": dataset}
				
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}