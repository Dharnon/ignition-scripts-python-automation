def filtroCrear(valorFiltro):
	# Administracion.Data.GestionUsuarios.filtroCrear(valorFiltro)
	"""
	Devolvemos todos los usuarios que haya en la tabla del servidor
	Que coincida con el valor del filtro
	Filtra por nombre usuario o numero de usuario
	"""
	#---PARAMETROS---------------------------------------------
	database = constantes.Database_Inicio
	databaseUsuarios = constantes.Database_Admin_Usuarios
	
	try:
		# Obtenemos hasta 30 usuarios activos que coincidan con el filtro
		query = """
		    SELECT TOP 30 IdUsuario, Nombre, Numero FROM Norm_TUsuarios
		    WHERE (
		    Numero LIKE ?
		    OR
		    Nombre LIKE ?
		    )
		    AND FechaBaja IS NULL
		"""
		params = ["%" + str(valorFiltro) + "%", "%" + str(valorFiltro) + "%"]
		
		data = system.db.runPrepQuery(query, params, database)
		
		# Obtenemos todos los IdUsuario existentes en TUsuarios
		
		query = "SELECT IdUsuario FROM TUsuarios"
		tusuarios_raw = system.db.runPrepQuery(query, [], databaseUsuarios)
		
		ids_existentes = set(row["IdUsuario"] for row in tusuarios_raw)
		
		#Convertir PyDataSet a lista de dicts
		result = []
		for row in data:
			if row["IdUsuario"] not in ids_existentes:
				result.append({
					"IdUsuario": row["IdUsuario"],
					"Nombre": row["Nombre"],
					"Numero": row["Numero"]
				})
		
		return result
	
	except Exception as e:
		return{"error": "Error al ejecutar Administracion.Data.GestionUsuarios.filtroCrear()"}
	
def mostrarRoles():
	# Administracion.Data.GestionUsuarios.mostrarRoles()
	"""
	Devolvemos todos los roles que hay
	"""
	#---PARAMETROS---------------------------------------------
	database = constantes.Database_Inicio
	databaseUsuarios = constantes.Database_Admin_Usuarios
	#----------------------------------------------------------
	
	try:
		query = "SELECT * FROM TRoles"
		data = system.db.runPrepQuery(query, [], databaseUsuarios)
		
		#Convertir PyDataSet a lista de dicts
		result = []
		for row in data:
			result.append({
				"IdRol": row["IdRol"],
				"Rol": row["Rol"]
			})
		
		return result
		
	except Exception as e:
		return{"error": "Error al ejecutar Administracion.Data.GestionUsuarios.mostrarRoles()"}
	
def mostrarUsuarios():
	# Administracion.Data.GestionUsuarios.mostrarUsuarios()
	"""
	Devolvemos todos los usuarios que hay registrados en Gpilot
	"""
	#---PARAMETROS---------------------------------------------
	database = constantes.Database_Inicio
	databaseUsuarios = constantes.Database_Admin_Usuarios
	#----------------------------------------------------------
	
	try:
		query = """
		    SELECT TU.IdUsuario, TR.Rol
		    FROM TUsuarios TU
		    INNER JOIN TRoles TR ON TU.IdRol = TR.IdRol
		"""
		data = system.db.runPrepQuery(query, [], databaseUsuarios)
		
		# Convertir resultado a lista de diccionarios
		usuarios = []
		for row in data:
		    usuarios.append({
		        "IdUsuario": row["IdUsuario"],
		        "Rol": row["Rol"]
		    })
		
		resultado = []
		for row in usuarios:
		    idUsuario = row["IdUsuario"]
		    Rol = row["Rol"]
		
		    # --- Paso 2: Buscar el nombre en la otra base de datos ---
		    query2 = """
		        SELECT Nombre, Mail
		        FROM Norm_TUsuarios
		        WHERE IdUsuario = ?
		        AND FechaBaja IS NULL
		    """
		    nombreData = system.db.runPrepQuery(query2, [idUsuario], database)
		
		    nombre = nombreData[0]["Nombre"] if nombreData else "Desconocido"
		    mail = nombreData[0]["Mail"] if nombreData else "Desconocido"
		
		    # --- Combinar y agregar al resultado final ---
		    resultado.append({
		        "Rol": Rol,
		        "Nombre": nombre,
		        "Mail": mail,
		        "idUsuario": idUsuario
		    })
		
		return resultado
	
	except Exception as e:
	    system.util.getLogger("MultiUsuarioLogger").error("Error: " + str(e))
	    return {"error": "Error al procesar usuarios"}
	
def crearUsuarios(idUsuario, idRol, idCreador):
	# Administracion.Data.GestionUsuarios.crearUsuarios(idUsuario, idRol, idCreador)
	"""
	Creamos usuarios para la base de datos de GPilot
	"""
	#---PARAMETROS---------------------------------------------
	databaseUsuarios = constantes.Database_Admin_Usuarios
	#----------------------------------------------------------
	now = system.date.now()
	
	try:
		query = """
			INSERT INTO TUsuarios (IdUsuario, IdRol, IdCreador, Fecha)
			VALUES (?, ?, ?, ?)
		"""
		
		params = [idUsuario, idRol, idCreador, now]
		system.db.runPrepUpdate(query, params, databaseUsuarios)
		
		return True
	
	except Exception as e:
		return{"error": "Error al ejecutar Administracion.Data.GestionUsuarios.crearUsuarios()"}
	
def eliminarUsuarios(idUsuario):
	# Administracion.Data.GestionUsuarios.eliminarUsuarios(idUsuario)
	"""
	Eliminamos usuarios de la base de datos de GPilot segun el idUsuario
	"""
	#---PARAMETROS---------------------------------------------
	databaseUsuarios = constantes.Database_Admin_Usuarios
	#----------------------------------------------------------
	
	try:
		query = "DELETE FROM TUsuarios WHERE IdUsuario = ?"
		
		system.db.runPrepUpdate(query,[idUsuario], databaseUsuarios)
		
		return True
	
	except Exception as e:
		return{"error": "Error al ejecutar Administracion.Data.GestionUsuarios.eliminarUsuarios()"}
	
def actualizarRolUsuario(idUsuario, idRol, idCreador):
	# Administracion.Data.GestionUsuarios.actualizarRolUsuario(idUsuario, idRol, idCreador)
	"""
	Creamos usuarios para la base de datos de GPilot
	"""
	#---PARAMETROS---------------------------------------------
	databaseUsuarios = constantes.Database_Admin_Usuarios
	#----------------------------------------------------------
	now = system.date.now()
	
	try:
		query = """
			UPDATE TUsuarios 
			SET IdRol = ?, IdCreador = ?, Fecha = ?
			WHERE IdUsuario = ?
		"""
		
		params = [idRol, idCreador, now, idUsuario]
		system.db.runPrepUpdate(query, params, databaseUsuarios)
		
		return True
		
	except Exception as e:
		return{"error": "Error al ejecutar Administracion.Data.GestionUsuarios.actualizarRolUsuario()"}
	
	