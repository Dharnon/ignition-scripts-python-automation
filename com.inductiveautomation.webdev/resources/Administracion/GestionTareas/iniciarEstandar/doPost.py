def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se usa para iniciar estandar o lo que es lo mismo
	Se debe proporcionar. Celula.
	"""
	#--------------------------------------------------------------------------------
	#---PARAMETROS-------------------------------------------------------------------
	#--------------------------------------------------------------------------------
	logger = system.util.getLogger("iniciarEstandar")
	
	try:
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "Data no proporcionada"}}
		celula = data['celula']
		
		Tareas.Secuencia.General.iniciarEstandar(celula)
		
		logger.info("Completado")
		
		return {
	        "json": {
	            "completado": "Estandar iniciado"
	        }
	    }
	
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}