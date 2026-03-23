def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe el numero del usuario y se mira en base de datos para devolver el rol y los nombres correspondientes
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		#data = request.getJson()
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data or "numUsuario" not in data:
			return {"json": {"error": "numUsuario no proporcionado"}}
	    
		numUsuario = data['numUsuario']
		logger.info("NumUsuario: " + str(numUsuario))
	
		dataUsuario = Inicio.Data.GestionUsuarios.obtenerDatos(numUsuario)
		if not dataUsuario:
			return {"json": {"error": "Usuario no encontrado"}}
	
		return {
	        "json": {
	            "dataUsuario": dataUsuario
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}

 