def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe la informacion correspondiente para editar los tiempos de maquina de las maquinas
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		#data = request.getJson()
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "No data proporcionada"}}
	    
		celula = data['celula']
		maquina = data['maquina']
		minutos = data['minutos']
		referencia = data['referencia']
		
		Administracion.Data.GestionTareas.editarMinutosMaquina(referencia, maquina, celula, minutos)
	
		return {
	        "json": {
	            "tarea": "Tiempo de maquina editada."
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}