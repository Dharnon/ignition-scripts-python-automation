def doGet(request, session):
	# CORS headers
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	#---INFO-------------------------------------------------------------------------
	"""
	Enviamos los usuarios de G Pilot registrados
	"""
	#--------------------------------------------------------------------------------
	
	usuarios = Administracion.Data.GestionUsuarios.mostrarUsuarios()
	
	return {
        "json": {
            "usuarios": usuarios
        }
    }