def crearTareaTorno(celula, num):
	# Tareas.Data.Independiente.crearTareaTorno(celula, num, prefijo)
	"""
	Funcion para añadir tareas de CH para torno o para cualquier maquina que use diferentes Cambios de Herramienta
	Prefijo coge el primer nombre completo
	"""
	#---PARAMETROS----------------------------------------------
	# prefijo = constantes.prefijo - Se escribe mas adelante en el codigo
	total = 0
	#-----------------------------------------------------------
	
	nombres = Sinoptico.Data.General.obtenerCNCHtaNombre(celula, num)
	prefijo = nombres[0]
	vidaHta = Sinoptico.Data.General.obtenerCNCHerramienta(celula, num)
	
	cantidad = len([nombre for nombre in nombres if nombre.startswith(prefijo)])
	
	for i in range(0, cantidad):
		print vidaHta[i][0]
		total += vidaHta[i][0] # Sumamos todas las vidas utiles de las herramientas
	
	return total

def crearTareaLimpieza(celula):
	# Tareas.Data.Independiente.crearTareaLimpieza(celula)
	"""
	Script que programa automáticamente una tarea de limpieza para la célula indicada.
	Selecciona el mejor momento según tareas existentes (CH de talladora/afeitadora o Grafico) 
	y asegura que hayan pasado al menos 4 horas desde la última limpieza.
	"""
	from system.dataset import toDataSet
	#---PARAMETROS---------------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
	#----------------------------------------------------------
	
	try:
		# 1. Leer dataset actual de tareas
		dataset = system.tag.readBlocking([tagPath])[0].value
		columnas = list(dataset.columnNames)
		
		# 2. Obtener última limpieza completada para esta célula
		query = """
			SELECT TOP 1 fecha 
			FROM G_Pilot_Completado
			WHERE tarea LIKE 'Limpieza%' AND celula = ?
			ORDER BY fecha DESC
		"""
		try:
			ultima_limpieza = system.db.runScalarQuery(query, [celula])
		except:
			now = system.date.now()
			ultima_limpieza = system.date.addYears(now, -20)
			
		# 3. Determinar hora actual y turno
		ahora = system.date.now()
		hora_actual = system.date.getHour24(ahora)
		
		if 6 <= hora_actual < 14:
			inicio_turno = system.date.midnight(ahora)
			inicio_turno = system.date.addHours(inicio_turno, 6)
			fin_turno = system.date.addHours(inicio_turno, 8)
		elif 14 <= hora_actual < 22:
			inicio_turno = system.date.midnight(ahora)
			inicio_turno = system.date.addHours(inicio_turno, 14)
			fin_turno = system.date.addHours(inicio_turno, 8)
		else:
			inicio_turno = system.date.midnight(ahora)
			if hora_actual < 6:
				inicio_turno = system.date.addDays(inicio_turno, -1)
				inicio_turno = system.date.addHours(inicio_turno, 22)
			else:
				inicio_turno = system.date.addHours(inicio_turno, 22)
			fin_turno = system.date.addHours(inicio_turno, 8)
		
		# 4. Buscar candidatos dentro del dataset filtrando por celula
		candidatos = []
		for i in range(dataset.rowCount):
			row = {col: dataset.getValueAt(i, col) for col in columnas}
			
			if row["completado"] == 0 and row["celula"] == celula:
				if row["tarea"].upper().startswith("CH") and row["maquina"].upper() == "TALLADORA":
					candidatos.append((row, 1))
				elif row["tarea"].upper().startswith("CH") and row["maquina"].upper() == "AFEITADORA":
					candidatos.append((row, 2))
				elif row["tarea"].upper().startswith("Grafico"):
					candidatos.append((row, 3))
		
		# Ordenar por prioridad y fecha "cuando"
		candidatos.sort(key=lambda x: (x[1], x[0]["cuando"]))
		
		# 5. Validar candidatos con regla de 4 horas
		tarea_limpieza = None
		for row, prioridad in candidatos:
			if ultima_limpieza is None:
				tarea_limpieza = row
				break
			diff_horas = system.date.hoursBetween(ultima_limpieza, row["cuando"])
			if diff_horas >= 4:
				tarea_limpieza = row
				break
		
		# 6. Si no hay candidato válido, programar a 2h antes del fin de turno
		if not tarea_limpieza:
			tarea_limpieza = {
				"tarea": "Limpieza",
				"cuando": system.date.addHours(fin_turno, -2),
				"celula": celula,
				"maquina": "GENERAL",
				"elemento": "Limpieza del puesto",
				"ocurrencia": 0,
				"completado": 0
			}
		else:
			tarea_limpieza = {
				"tarea": "Limpieza",
				"cuando": tarea_limpieza["cuando"],
				"celula": celula,
				"maquina": "GENERAL",
				"elemento": "Limpieza del puesto",
				"ocurrencia": 0,
				"completado": 0
			}
		
		# 7. Insertar nueva tarea en dataset
		nuevas_filas = [ [dataset.getValueAt(i, col) for col in columnas] for i in range(dataset.rowCount) ]
		nuevas_filas.append([tarea_limpieza.get(col, None) for col in columnas])
		
		dataset_actualizado = toDataSet(columnas, nuevas_filas)
		system.tag.writeBlocking([tagPath], [dataset_actualizado])
		
		print("Tarea de limpieza programada en:", tarea_limpieza["cuando"], "para celula:", celula)
		return True
	
	except Exception as e:
		return("Error en Tareas.Data.Independiente.crearTareaLimpieza():", str(e))
		

def crearTareaGrafico(celula):
    # Tareas.Data.Independiente.crearTareaGrafico(celula)
    """
    Script programa automaticamente una tarea Grafico para la celula indicada.
    Intenta ubicarla en la misma hora que una tarea de CH de Talladora o Afeitadora
    Si no hay candidatos, la programa 2 horas despues del inicio de turno
    """
    from system.dataset import toDataSet
	#---PARAMETROS---------------------------------------------
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
    #----------------------------------------------------------
    try:
        # 1. Leer dataset actual
        dataset = system.tag.readBlocking([tagPath])[0].value
        columnas = list(dataset.columnNames)
        nuevas_filas = []

        # 2. Hora actual y base del turno
        base_time = system.date.now()

        # 3. Recorrer dataset para encontrar candidatos
        candidatos = []
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}

            if row["celula"] != celula or row["completado"] != 0:
                continue

            # Programar junto a CH de Talladora
            if row["tarea"].startswith("CH") and row["maquina"].upper() == "TALLADORA":
                candidatos.append((row, 1))
            # Programar junto a CH de Afeitadora
            elif row["tarea"].startswith("CH") and row["maquina"].upper() == "AFEITADORA":
                candidatos.append((row, 2))

        # 4. Seleccionar el candidato de mayor prioridad
        if candidatos:
            candidatos.sort(key=lambda x: x[1])
            fila_candidato = candidatos[0][0]
            hora_programada = fila_candidato["cuando"]
        else:
            # Si no hay candidatos, poner a 2 horas del inicio de turno
            hora_programada = system.date.addHours(base_time, 2)

        # 5. Crear nueva fila para la tarea Grafico
        base_row = None
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}
            if row["celula"] == celula and row["completado"] == 0:
                base_row = row
                break

        if base_row:
            nueva_fila = base_row.copy()
            nueva_fila["tarea"] = "Grafico"
            nueva_fila["elemento"] = "Solicitud de grafico"
            nueva_fila["ocurrencia"] = 1
            nueva_fila["completado"] = 0
            nueva_fila["cuando"] = hora_programada
            nuevas_filas.append([nueva_fila[col] for col in columnas])

        # 6. Mantener el resto del dataset
        for i in range(dataset.rowCount):
            row = [dataset.getValueAt(i, col) for col in columnas]
            nuevas_filas.append(row)

        # 7. Crear dataset actualizado
        dataset_actualizado = toDataSet(columnas, nuevas_filas)

        # 8. Escribir en el tag
        system.tag.writeBlocking([tagPath], [dataset_actualizado])

        print("Tarea 'Grafico' programada para la célula:", celula)
        return True

    except Exception as e:
        print("Error en programarTareaGrafico():", str(e))
        return {"error": "Error interno al actualizar tag"}


def actualizarTareaGrafico(celula):
    # Tareas.Data.Independiente.actualizarTareaGrafico(celula)
    """
    Actualiza la hora 'cuando' de la tarea 'Grafico' (o que empiece por 'Grafico')
    para la célula indicada, según:
    - Si hay una tarea CH de Talladora o Afeitadora SIN completar y dentro del turno actual: usar su hora.
    - Si no hay ninguna válida o está fuera del turno: usar 2 horas después del inicio de turno.
    """

    from system.dataset import toDataSet
    import system.date

    try:
        #---PARAMETROS---------------------------------------------
        tp = constantes.tag_provider
        celulaLinea = constantes.celulaLinea
        tagPath = tp + "Dataset/Tareas_Celula" + celulaLinea
        #----------------------------------------------------------

        # === Funciones auxiliares ===
        def obtenerInicioYFinTurno():
            ahora = system.date.now()
            hora = system.date.getHour24(ahora)

            if 6 <= hora < 14:  # Turno mañana
                inicio = system.date.setTime(ahora, 6, 0, 0)
                fin = system.date.setTime(ahora, 14, 0, 0)
                turno = 1
            elif 14 <= hora < 22:  # Turno tarde
                inicio = system.date.setTime(ahora, 14, 0, 0)
                fin = system.date.setTime(ahora, 22, 0, 0)
                turno = 2
            else:  # Turno noche
                if hora < 6:
                    # Si son las 00:00–05:59 → turno empezó el día anterior
                    inicio = system.date.addDays(system.date.setTime(ahora, 22, 0, 0), -1)
                else:
                    inicio = system.date.setTime(ahora, 22, 0, 0)
                fin = system.date.addHours(inicio, 8)
                turno = 3
            return inicio, fin, turno

        def estaEnTurno(fecha, inicio, fin):
            # Verifica si una fecha cae dentro del rango del turno actual
            return (fecha >= inicio) and (fecha < fin)

        # 1. Leer dataset actual
        dataset = system.tag.readBlocking([tagPath])[0].value
        columnas = list(dataset.columnNames)
        nuevas_filas = []

        # 2. Calcular turno actual
        inicio_turno, fin_turno, nro_turno = obtenerInicioYFinTurno()

        # 3. Buscar candidatos válidos
        candidatos = []
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}
            if row["celula"] != celula or row["completado"] != 0:
                continue

            if row["tarea"].startswith("CH") and row["maquina"].upper() == "TALLADORA":
                if estaEnTurno(row["cuando"], inicio_turno, fin_turno):
                    candidatos.append((row, 1))
            elif row["tarea"].startswith("CH") and row["maquina"].upper() == "AFEITADORA":
                if estaEnTurno(row["cuando"], inicio_turno, fin_turno):
                    candidatos.append((row, 2))

        # 4. Determinar hora programada
        if candidatos:
            candidatos.sort(key=lambda x: x[1])
            fila_candidato = candidatos[0][0]
            hora_programada = fila_candidato["cuando"]
        else:
            # Sin candidatos válidos o fuera de turno
            hora_programada = system.date.addHours(inicio_turno, 2)

        # 5. Actualizar fila de la tarea "Grafico"
        grafico_encontrado = False
        for i in range(dataset.rowCount):
            row = {col: dataset.getValueAt(i, col) for col in columnas}

            if row["celula"] == celula and str(row["tarea"]).startswith("Grafico") and row["completado"] == 0:
                row["cuando"] = hora_programada
                grafico_encontrado = True

            nuevas_filas.append([row[col] for col in columnas])

        # 6. Si no se encontró la tarea “Grafico”
        if not grafico_encontrado:
            print("⚠️ No se encontró tarea 'Grafico' para la célula:", celula)
            return {"warning": "Tarea 'Grafico' no encontrada en el dataset"}

        # 7. Escribir el dataset actualizado
        dataset_actualizado = toDataSet(columnas, nuevas_filas)
        system.tag.writeBlocking([tagPath], [dataset_actualizado])

        print("Tarea 'Grafico' actualizada para la célula:", celula)
        print("Hora programada:", hora_programada)
        print("Turno actual:", nro_turno)
        return True

    except Exception as e:
        print("❌ Error en actualizarHoraGrafico():", str(e))
        return {"error": "Error interno al actualizar tag"}
 