def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se cierra sesion y se escribe en el tag de ignition asociado un 0.
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		tp = constantes.tag_provider
		
		# Reseteamos el tag de idUsuario registrado
		path = tp + "Variables/Inicio/idUsuario"
		system.tag.writeBlocking(path, 0)
	
		return {
	        "json": {
	            "dataUsuario": "Sesion Cerrada."
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}

 