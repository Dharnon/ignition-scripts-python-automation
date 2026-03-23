def doGet(request, session):
	#---Seguridad, Permitir Cors-----------------------------------------------------
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")  # Permitir todas las orígenes
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Se recibe 
	"""
	#--------------------------------------------------------------------------------
	
	#response.addHeader("Access-Control-Allow-Origin", "http://localhost:5173") #allow API calls from other hosts in addition to that of the gateway	
	#tag = system.tag.readBlocking(['[default]TagDeEjemplo'])[0].value
	
	json = {"tag": "Hola"}
	
	return {'json' : json}
	#return None
	#This response can be retrieved with fetch() in JavaScript.
	#return {"json": {'tagvalue': str(valor), "status": 200}}