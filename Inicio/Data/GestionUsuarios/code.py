def obtenerDatos(numUsuario):
	# Inicio.Data.GestionUsuarios.obtenerDatos(numUsuario)
	"""
	Obtener datos del usuario segun su numero y consultando en base de datos
	"""
	try:
		database = constantes.Database_Inicio
		databaseUsuarios = constantes.Database_Admin_Usuarios
		tp = constantes.tag_provider
		
		numUsu = str(numUsuario)
		
		# Rellena con ceros hasta llegar a 8 digitos
		while len(numUsu) < 8:
			numUsu = "0" + numUsu
		print numUsu
		
		# Obtenemos datos del usuario
		query = """
		    SELECT Usuario, Nombre, Mail, IdUsuario FROM Norm_TUsuarios
		    WHERE Numero = ?
		    AND FechaBaja IS NULL
		"""
		params = [numUsu]
		
		data = system.db.runPrepQuery(query, params, database)
		
		usuario = data[0][0]
		nombre = data[0][1]
		mail = data[0][2]
		idUsuario = data[0][3]
		
		usuarioFinal = usuario.split('\\')[-1] #Lee lo que hay apartir de la /
		
		# Obtenemos rol del usuario
		query = """
		    SELECT R.Rol
		    FROM TUsuarios U
		    INNER JOIN TRoles R ON U.IdRol = R.IdRol
		    WHERE U.IdUsuario = ?
		"""
		params = [idUsuario]
		
		roles = system.db.runPrepQuery(query, params, databaseUsuarios)
		rol = roles[0][0]
		
		# Guardamos en tag el idUsuario registrado
		path = tp + "Variables/Inicio/idUsuario"
		system.tag.writeBlocking(path, idUsuario)
		
		return [nombre, usuarioFinal, mail, rol, idUsuario]
	
	except Exception as e:
		system.util.getLogger("ScriptError").error("obtenerDatosUsuario: {}".format(str(e)))
		return ['NULL', 'NULL', 'NULL', 'NULL', 'NULL']