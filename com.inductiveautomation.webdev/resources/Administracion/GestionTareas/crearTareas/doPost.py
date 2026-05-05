def doPost(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe la informacion correspondiente para crear y añadir tareas nuevas
	"""
	#--------------------------------------------------------------------------------
	
	logger = system.util.getLogger("WebDevLogger")
	
	try:
		# DATOS QUE RECIBIMOS------------------------------------------------
		data = request['data']
		logger.info("Datos recibidos: " + str(data))
		if not data:
			return {"json": {"error": "No data proporcionada"}}
	    
		tarea_react = data['tarea']
		celula = data['celula']
		maquina = data['maquina']
		elemento = data['elemento']
		ocurrencia = data['ocurrencia']
		referencia = data['referencia']
		num = Sinoptico.Data.General.obtenerNumeroMaquina(celula, maquina)
		
		logger.info("Tarea React: " + str(tarea_react))
		logger.info("Celula: " + str(celula))
		
		logger.info("Referencia: " + str(referencia))
		rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, maquina) # Obtenemos el ritmo de produccion
		logger.info("rpt: " + str(rpt))
		
		# Si es la tarea CH se debe asignar la ocurrencia a mano, dependiendo de la maquina se hace de una manera o de otra
		if tarea_react == "CH":
			if maquina == "TALLADORA":
				datos = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
				ocurrencia = datos[0][0]
			elif maquina == "AFEITADORA":
				datos = Sinoptico.Data.General.obtenerAutoHerramienta(celula, num)
				ocurrencia = datos[0]
			elif maquina == "TORNO":
				ocurrencia = Tareas.Data.Independiente.crearTareaTorno(celula, num)
		
		
		logger.info("ocurrencia: " + str(ocurrencia))
		if ocurrencia == 0 or ocurrencia == 1 or ocurrencia == 'NULL':
			return {
		        "json": {
		            "tarea": "Ocurrencia 0 o 1 o 'NULL'. Mala ocurrencia"
		        }
		    }
		else:
			tarea = tarea_react + " 1/" + str(ocurrencia)
			logger.info("Tarea: " + str(tarea_react))
			# Creamos tarea
			Tareas.Data.General.crearNuevasTareas(tarea, celula, maquina, elemento, rpt, ocurrencia, referencia) # Creamos nueva tarea
			logger.info("Hemos creado tarea: Tareas.Data.General.crearNuevasTareas()")
			
			# Actualizamos los contadores de las tareas por si hace falta
			Tareas.Data.TagsMaquina.syncTareas(celula, referencia, maquina, num)
			logger.info("Sincreonizamos tareas con los tags : Tareas.Data.General.crearNuevasTareas()")
		
			return {
		        "json": {
		            "tarea": "Tarea creada."
		        }
		    }
	except Exception as e:
	    logger.error("Error en doPost: " + str(e))
	    return {"json": {"error": "Error interno del servidor"}}