def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se elimina un usuario en la parte de gestion de Administracion en la tabla TUsuarios
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "No data proporcionada"}}
	    
		idUsuario = idUsuario = data['IdUsuario']
		logger.info("idUsuario: " + str(idUsuario))
		
		usuarioEliminado = Administracion.Data.GestionUsuarios.eliminarUsuarios(idUsuario)
		
		if usuarioEliminado:
			return {
		        "json": {
		            "info": "Usuario eliminado"
		        }
		    }
		else:
			return {
		        "json": {
		            "info": "Usuario NO encontrado"
		        }
		    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}