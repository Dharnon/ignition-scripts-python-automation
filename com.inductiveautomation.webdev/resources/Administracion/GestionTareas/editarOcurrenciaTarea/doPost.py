def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe la informacion correspondiente para editar la ocurrencia de las tareas
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		#data = request.getJson()
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "No data proporcionada"}}
	    
		tarea = data['tarea']
		celula = data['celula']
		maquina = data['maquina']
		elemento = data['elemento']
		ocurrencia = data['ocurrencia']
		referencia = data['referencia']
		
		referencia_actual = Sinoptico.Data.General.obtenerReferencia(celula)
		
		#tarea = tarea_react + " 1/" + str(ocurrencia)
		
		editar = Administracion.Data.GestionTareas.editarOcurrenciaTareas(tarea, referencia, maquina, celula, elemento, ocurrencia) # Actualizamos en la base de datos
		
		if referencia != referencia_actual:
			editar = False 				# Significa que no estamos trabajando con la referencia a actualizar por lo que no hace falta cambiar
		
		if editar:
			Administracion.Data.GestionTareas.editarOcurrenciaActualizarTag(tarea, maquina, celula, elemento, ocurrencia, referencia) # Actualizamos en el dataset del tag de Ignition
	
		return {
	        "json": {
	            "tarea": "Ocurrencia editada."
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}