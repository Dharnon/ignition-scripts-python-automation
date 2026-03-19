def mostrarTareas():
	# Administracion.Data.GestionTareas.mostrarTareas()
	"""
    Obtiene tareas de una tabla dinámica:
    - Filtra tareas que no son tipo 'Carga%', 'Traslados%' o 'Tiempo de m%'
    - Consulta tareas 'Tiempo de máquina 1/1' para obtener tiempos mínimos
    - Une ambas consultas en un array con campos relevantes
    - Ajusta el nombre de la tarea si tiene formato '... /N'
	"""
	#---PARAMETROS---------------------------------------------
	database = constantes.DATABASE
	tablaTareas = constantes.LINEA + "_Tareas"
	tarea1 = "Tiempo de m%"
	tarea2 = "%quina 1/1"
	#----------------------------------------------------------------------
	
	try:
		# --- Consulta 1: Obtener MINs de 'Tiempo de máquina 1/1'
		query_min = """
		    SELECT referencia, maquina, celula, 
		           CASE WHEN min IS NULL THEN min_std ELSE min END AS min_calculado
		    FROM {0}
		    WHERE tarea LIKE ?
		    and tarea LIKE ?
		""".format(tablaTareas)
	
		min_data = system.db.runPrepQuery(query_min, [tarea1, tarea2], database)
		
		# Crear diccionario para lookup de min
		min_dict = {}
		for row in min_data:
		    key = (row["referencia"], row["maquina"], row["celula"])
		    min_dict[key] = row["min_calculado"]
		    print key
		
		# --- Consulta 2: Tareas útiles
		query_tareas = """
		    SELECT referencia, tarea, maquina, celula, elemento,
		           CASE WHEN ocurrencia IS NULL THEN ocurrenciaStd ELSE ocurrencia END AS ocurrencia_calculada
		    FROM {0}
		    WHERE tarea NOT LIKE 'Carga%'
		      AND tarea NOT LIKE 'Traslados%'
		      AND tarea NOT LIKE 'Tiempo de m%'
		""".format(tablaTareas)
		tarea_data = system.db.runPrepQuery(query_tareas, [], database)
		
		# --- Construcción del resultado final
		resultado = []
		
		for row in tarea_data:
		    referencia = row["referencia"]
		    tarea = row["tarea"]
		    maquina = row["maquina"]
		    celula = row["celula"]
		    elemento = row["elemento"]
		    ocurrencia = row["ocurrencia_calculada"]
		
		    # Buscar min en el diccionario
		    key = (referencia, maquina, celula)
		    min_valor = min_dict.get(key, None)
		
		    # Ajustar nombre de tarea si tiene "/"
		    if "/" in tarea:
		        #base = tarea.split("/")[0].strip()
		        #tarea = base + " 1/" + str(int(ocurrencia))
		
		        resultado.append({
		            "referencia": referencia,
		            "tarea": tarea,
		            "maquina": maquina,
		            "celula": celula,
		            "ocurrencia": ocurrencia,
		            "elemento": elemento,
		            "min": min_valor
		        })
		
		return resultado
		
	except Exception as e:
		print("Error en procesarAdministracion.Data.GestionTareas.mostrarTareas(): " + str(e))
        return {"error": "Error interno al procesar tareas"}
        
def eliminarTarea(tarea, referencia, maquina, celula, elemento):
    # Administracion.Data.GestionTareas.eliminarTarea(tarea, referencia, maquina, celula, elemento)
    """
    Elimina una tarea específica de la tabla intermedia de tareas
    y luego actualiza la tabla resumen.
    """
    tablaTareas = constantes.LINEA + "_Tareas"
    database = constantes.Database_Tareas

    try:
        # --- Eliminar en base de datos ------------------------------------
        query = """
        DELETE FROM {tabla}
        WHERE tarea = ?
        AND referencia = ?
        AND maquina = ?
        AND celula = ?
        AND elemento = ?
        """.format(tabla=tablaTareas)

        params = [
            tarea,
            referencia,
            maquina,
            celula,
            elemento
        ]

        system.db.runPrepUpdate(query, params, database)

        # Actualizar tabla resumen
        Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)

        return True

    except Exception as e:
        print("Error en Administracion.Data.GestionTareas.eliminarTarea(): " + str(e))
        return {"error": "Error al eliminar la tarea"}
	

def eliminarTareaActualizarTag(tarea, maquina, celula, elemento):
	# Administracion.Data.GestionTareas.eliminarTareaActualizarTag(tarea, maquina, celula, elemento)
	"""
	Actualiza el tag Ignition eliminando un elemento específico de una tarea.
	- Si la tarea tiene más de un elemento, se actualiza el campo 'elemento'.
	- Si es el único elemento, se elimina la fila completa.
	"""
	from system.dataset import toDataSet
	import system.tag
	
	# Ruta del tag donde está el dataset de tareas (ajústala a tu proyecto)
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	try:
	    # 1. Leer dataset actual
	    dataset = system.tag.readBlocking([tagPath])[0].value
	    columnas = list(dataset.columnNames)
	    nuevas_filas = []
	
	    # 2. Recorrer filas
	    for i in range(dataset.rowCount):
	        row_tarea = dataset.getValueAt(i, "tarea")
	        row_maquina = dataset.getValueAt(i, "maquina")
	        row_celula = dataset.getValueAt(i, "celula")
	        row_elemento = dataset.getValueAt(i, "elemento")
	
	        # Coincide con la tarea/maquina/célula
	        if (row_tarea == tarea and row_maquina == maquina and row_celula == celula):
	            # Separar elementos
	            elementos_lista = [e.strip() for e in row_elemento.split("|")]
	
	            if elemento in elementos_lista:
	                elementos_lista.remove(elemento)
	
	            if len(elementos_lista) > 0:
	                # Aún quedan elementos → actualizar fila
	                nueva_fila = [dataset.getValueAt(i, col) for col in columnas]
	                # Reemplazar campo "elemento" por la lista nueva concatenada
	                nueva_fila[columnas.index("elemento")] = " | ".join(elementos_lista)
	                nuevas_filas.append(nueva_fila)
	            else:
	                # Ya no queda ningún elemento → eliminar la fila completa
	                print("Eliminando fila completa de tarea:", row_tarea)
	                continue
	        else:
	            # No coincide, se mantiene igual
	            nuevas_filas.append([dataset.getValueAt(i, col) for col in columnas])
	
	    # 3. Crear dataset filtrado
	    dataset_filtrado = toDataSet(columnas, nuevas_filas)
	
	    # 4. Escribir en el tag
	    system.tag.writeBlocking([tagPath], [dataset_filtrado])
	
	    print("Tag actualizado correctamente. Tarea:", tarea, "Elemento eliminado:", elemento)
	    return True
	
	except Exception as e:
	    print("Error al actualizar el tag de tareas:", str(e))
	    return {"error": "No se pudo actualizar el tag"}

def editarOcurrenciaTareas(tarea, referencia, maquina, celula, elemento, ocurrencia):
	# Administracion.Data.GestionTareas.editarOcurrenciaTareas(tarea, referencia, maquina, celula, elemento, ocurrencia)
	"""
	Editamos la ocurrencia de las tareas en la tabla de datos intermedia
	Después se actualiza la tabla resumen (final)
	"""
	#---PARAMETROS---------------------------------------------
	tablaTareas = constantes.LINEA + "_Tareas"
	database = constantes.Database_Tareas
	#----------------------------------------------------------
	
	try:
		# Ajustar nombre de tarea si tiene "/"
		if "/" in tarea:
			base = tarea.split("/")[0].strip()
			editTarea = base + "/" + str(int(ocurrencia))
		else:
			editTarea = tarea
	        
		#---Actualizar en base de datos------------------------------------
		query = """
		UPDATE {tabla} 
		    SET ocurrencia = ?,  tarea = ?
		    WHERE referencia = ?
		    AND maquina = ?
		    AND celula = ?
		    AND elemento = ?
		""".format(tabla=tablaTareas)
		
		
		params = [
			ocurrencia, # Nuevo valor para ocurrencia
			editTarea,
			referencia,
			maquina,
			celula,
			elemento
		]
		system.db.runPrepUpdate(query, params, database)
		
		Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen() # Actualizar la tabla tareas resumen
		
		return True
		
	except Exception as e:
		print("Error en Administracion.Data.GestionTareas.editarOcurrenciaTareas(): " + str(e))
        return {"error": "Error interno al procesar tareas"}
    
def editarOcurrenciaActualizarTag(tarea, maquina, celula, elemento, ocurrencia, referencia):
	# Administracion.Data.GestionTareas.editarOcurrenciaActualizarTag(tarea, maquina, celula, elemento, ocurrencia, referencia)
	"""
	Actualiza la ocurrencia de un elemento específico dentro de una tarea en un Dataset de Ignition.
	- Si la tarea contiene varios elementos, solo se modifica el indicado, manteniendo los demás intactos.
	- Ajusta el nombre de la tarea según la nueva ocurrencia (ej. “Verificación 1/25” → “Verificación 1/50”).
	- Si ya existe un grupo de tareas con la misma ocurrencia, agrega el elemento a ese grupo; 
	     si no, crea nuevas filas periódicas para las próximas 12 horas según el tiempo base de la máquina.
	- Recalcula la columna cuando para programar la ejecución de la tarea.
	- Maneja correctamente caracteres con acentos, asegurando que se guarden bien en el Dataset.
	"""
	from system.dataset import toDataSet
	import system.tag
	import system.date
	
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
	
	try:
	    # 1. Leer dataset actual
	    dataset = system.tag.readBlocking([tagPath])[0].value
	    columnas = list(dataset.columnNames)
	    nuevas_filas = []
	
	    # 2. Buscar el tiempo base desde datasetMinutos
	    datasetMinutos = Tareas.Data.Teorico.obtenerTiemposMaquina(celula, referencia)
	    minutos = None
	    for i in range(datasetMinutos.rowCount):
	        if (datasetMinutos.getValueAt(i, "maquina") == maquina and 
	            datasetMinutos.getValueAt(i, "celula") == celula):
	            minutos = datasetMinutos.getValueAt(i, "minutos")
	            break
	
	    if minutos is None:
	        print("No se encontró configuración de minutos para la tarea:", tarea)
	        return {"error": "No se encontró configuración de minutos para la tarea"}
	
	    # 3. Hora base (ahora mismo)
	    base_time = system.date.now()
	
	    # Ajustar nombre de la nueva tarea
	    if "/" in tarea:
	        base = tarea.split("/")[0].strip()
	        nueva_tarea = base + "/" + str(int(ocurrencia))
	    else:
	        nueva_tarea = tarea
	
	    elemento_movido = False
	
	    # 4. Recorrer dataset y modificar filas
	    for i in range(dataset.rowCount):
	        row_dict = {col: dataset.getValueAt(i, col) for col in columnas}
	
	        if (row_dict["tarea"] == tarea and 
	            row_dict["maquina"] == maquina and 
	            row_dict["celula"] == celula and 
	            row_dict["completado"] == 0):
	
	            # Separar elementos en lista
	            elementos_lista = [e.strip() for e in row_dict["elemento"].split("|")]
	
	            if elemento in elementos_lista:
	                elementos_lista.remove(elemento)
	                elemento_movido = True
	
	                if len(elementos_lista) > 0:
	                    # Actualizar fila original
	                    row_dict["elemento"] = " | ".join(elementos_lista)
	                    nuevas_filas.append([row_dict[col] for col in columnas])
	                continue
	
	        # Mantener fila tal cual
	        nuevas_filas.append([row_dict[col] for col in columnas])
	
	    # 5. Si el elemento fue movido → buscar si ya existe grupo destino
	    if elemento_movido:
	        fusionado = False
	        for fila in nuevas_filas:
	            fila_dict = dict(zip(columnas, fila))
	            if (fila_dict["tarea"] == nueva_tarea and 
	                fila_dict["maquina"] == maquina and 
	                fila_dict["celula"] == celula and 
	                fila_dict["completado"] == 0):
	                # Agregar el elemento al grupo ya existente
	                nuevos_elem = fila_dict["elemento"] + " | " + elemento
	                fila[columnas.index("elemento")] = nuevos_elem
	                fusionado = True
	
	        # 6. Si no existe grupo destino → crear nueva serie de filas para las próximas 8 horas
	        if not fusionado and minutos:
	            total_minutos = 8 * 60
	            intervalo = minutos * int(ocurrencia)
	            num_repeticiones = total_minutos // intervalo
	
	            # Buscar fila base de la misma máquina/célula
	            base_row = None
	            for i in range(dataset.rowCount):
	                row_dict = {col: dataset.getValueAt(i, col) for col in columnas}
	                if (row_dict["maquina"] == maquina and 
	                    row_dict["celula"] == celula and 
	                    row_dict["completado"] == 0):
	                    base_row = row_dict
	                    break
	
	            if base_row:
	                for j in range(int(num_repeticiones)):
	                    new_row = base_row.copy()
	                    nueva_tarea = unicode(nueva_tarea, "utf-8")
	                    elemento = unicode(elemento, "utf-8")
	                    new_row["tarea"] = nueva_tarea
	                    new_row["ocurrencia"] = ocurrencia
	                    new_row["elemento"] = elemento
	                    new_row["completado"] = 0
	                    new_row["cuando"] = system.date.addMinutes(base_time, int((j+1)) * int(intervalo))
	                    nuevas_filas.append([new_row[col] for col in columnas])
	
	    # 7. Crear dataset actualizado
	    dataset_actualizado = toDataSet(columnas, nuevas_filas)
	
	    # 8. Escribir en el tag
	    system.tag.writeBlocking([tagPath], [dataset_actualizado])
	
	    print("Tarea actualizada en el tag:", nueva_tarea, "Elemento:", elemento)
	    return True
	
	except Exception as e:
	    print("Error en editarOcurrenciaTag():", str(e))
	    return {"error": "Error interno al actualizar tag"}
	
def editarMinutosMaquina(referencia, maquina, celula, minutos):
	# Administracion.Data.GestionTareas.editarMinutosMaquina(referencia, maquina, celula, minutos)
	"""
	Editamos la ocurrencia de las tareas en la tabla de datos intermedia
	Después se actualiza la tabla resumen (final)
	"""
	#---PARAMETROS---------------------------------------------
	tablaTareas = constantes.LINEA + "_Tareas"
	database = constantes.Database_Tareas
	#----------------------------------------------------------
	
	try:
		#---Actualizar en base de datos------------------------------------
		query = """
		UPDATE {tabla} 
		    SET min = ?
		    WHERE referencia = ?
		    AND maquina = ?
		    AND celula = ?
		    AND tarea LIKE 'Tiempo de m%'
		    AND tarea LIKE '%quina 1/1'
		""".format(tabla=tablaTareas)
		
		params = [
			minutos, # Nuevo valor para minutos
			referencia,
			maquina,
			celula
		]
		system.db.runPrepUpdate(query, params, database)
		
		Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen() # Actualizar la tabla tareas resumen
		
		return True
		
	except Exception as e:
		print("Error en Administracion.Data.GestionTareas.editarMinutosMaquina(): " + str(e))
        return {"error": "Error interno al procesar tareas"}