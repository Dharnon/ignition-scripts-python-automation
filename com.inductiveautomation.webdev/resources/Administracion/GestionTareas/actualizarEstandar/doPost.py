def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe un trigger para actualizar el estándar
	"""
	#--------------------------------------------------------------------------------
	logger = system.util.getLogger("ActualizarEstandar")
	try:
		logger.info("Trigger recibido")
		celula = data.get('celula')
		if celula is None:
			raise ValueError("celula no proporcionada")
		Tareas.Secuencia.General.iniciarEstandar(celula)
	
		return {
	        "json": {
	            "Info": "Estandar Actualizado."
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}