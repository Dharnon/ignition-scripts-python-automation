def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe la informacion correspondiente para eliminar una tarea de la tabla de tareas
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
		referencia = data['referencia']
		
		referencia_actual = Sinoptico.Data.General.obtenerReferencia(celula)
		
		eliminado = Administracion.Data.GestionTareas.eliminarTarea(tarea, referencia, maquina, celula, elemento) # Actualizamos en la base de datos
		
		if referencia != referencia_actual:
			eliminado = False 				# Significa que no estamos trabajando con la referencia a eliminar por lo que no hace falta cambiar
		
		# Da True si elimina
		if eliminado:
			Administracion.Data.GestionTareas.eliminarTareaActualizarTag(tarea, maquina, celula, elemento) # Actualizamos en el dataset
			
			# Actualizamos los contadores de las tareas por si hace falta
			num = Sinoptico.Data.General.obtenerNumeroMaquina(celula, maquina)
			Tareas.Data.TagsMaquina.syncTareas(celula, referencia, maquina, num)
	
		return {
	        "json": {
	            "tarea": "Tarea eliminada."
	        }
	    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}