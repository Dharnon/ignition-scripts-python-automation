def cargarEstandar(filepath, pages):
	# Tareas.Secuencia.General.cargarEstandar(filepath, pages)
	"""
	Llamadas a funciones para cargar un estnandar en base de datos.
	pages 4: del 0 al 3
	ruta = "\R120638-R120636-R120631-R120631.xlsx"
	"""
	try:
		#filepath = constantes.pathExcel + str(ruta)
		#filepath = str(ruta)
		#print filepath

		#---Leemos de las paginas del excel e insertamos en BBDD
		for page in range(pages):
			datos = Tareas.Data.fromExcelToDB.excelToDb_fb(filepath, page) # Actualizamos en la tabla Secuencia
			celula = datos[0]
			referencia = datos[1]
			#---Actualizamos ocurrencia de Bandeja descarga
			Tareas.Data.Teorico.accionesCambioBandejaDescarga(referencia)
			#---Transformamos los datos del excel a datos a la tabla de tareas final
			Tareas.Data.fromExcelToDB.tareasTable(celula, referencia)
			Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)
			
		return True
    
   	except Exception as e:
   		system.util.getLogger("ScriptError").error("Tareas.Secuencia.General.cargarEstandar(): {}".format(str(e)))
   		return False

def iniciarEstandar_v0(celula):
    # Tareas.Secuencia.General.iniciarEstandar_v0(celula)
    """
    Llamadas a funciones para iniciar un Estandar en el dataset y mostrar en REACT.
    CUIDADO!! Hace un reset a lo que hay y empieza con el nuevo Estandar
    
    VERSIÓN SIMPLIFICADA: Usa appendDataset + filterColumns para preservar tipos
    SE PUEDE BORRAR !!
    """
    import system.dataset as ds
    #try:
    #---PARAMETROS-------------------------
    tp = constantes.tag_provider
    celulaLinea = constantes.celulaLinea
    referencia = Sinoptico.Data.General.obtenerReferencia(celula)
    
    #---Obtenemos los tiempos que tarda cada maquina
    datasetMinutos = Tareas.Data.Teorico.obtenerTiemposMaquina(celula, referencia)
    #---Obtenemos las tareas de la tabla Tareas de base de datos
    datasetTareas = Tareas.Data.Teorico.obtenerTareas(celula, referencia)
    #---Segun los tiempos y las tareas, calculamos la data a enviar
    dataset = Tareas.Data.Teorico.generarDatasetTiempos(datasetMinutos, datasetTareas)
    
    # Leemos el dataset existente-----------------------------------------------------------------
    path = tp + "Dataset/Tareas_Celula" + celulaLinea
    existingDataset = system.tag.readBlocking([path])[0].value
    print existingDataset
    
    #---Escribir al tag
    system.tag.writeBlocking([path], [dataset])
    
    #----------------------------------------------------------------------------------------------
    
    #---Escribir en los tags el contador de tareas
    Tareas.Data.TagsMaquina.tareasPorMaquinaGeneral(celula)
    
    #---Inicializamos datasets
    Tareas.Data.TagsMaquina.inicializarTodosLosDatasetsPiezas(celula)
    
    return True
        
    #except Exception as e:
    #    system.util.getLogger("ScriptError").error("Tareas.Secuencia.General.iniciarEstandar(): {}".format(str(e)))
    #    return False
 

def iniciarEstandar(celula):
    # Tareas.Secuencia.General.iniciarEstandar(celula)
    """
    Reinicia el estándar en el dataset del tag:
    - Borra lo que haya de la célula indicada.
    - Inserta las nuevas filas generadas para esa célula.
    - Mantiene intactos los datos de las demás células.
    """
    import system.dataset as ds

    try:
        #---PARAMETROS-------------------------
        tp = constantes.tag_provider
        celulaLinea = constantes.celulaLinea
        referencia = Sinoptico.Data.General.obtenerReferencia(celula)

        #---Obtenemos los tiempos que tarda cada maquina
        datasetMinutos = Tareas.Data.Teorico.obtenerTiemposMaquina(celula, referencia)
        #---Obtenemos las tareas de la tabla Tareas de base de datos
        datasetTareas = Tareas.Data.Teorico.obtenerTareas(celula, referencia)
        #---Segun los tiempos y las tareas, calculamos la data a enviar
        datasetNuevo = Tareas.Data.Teorico.generarDatasetTiempos(datasetMinutos, datasetTareas)

        #---Leemos el dataset existente-----------------------------------------------------------------
        path = tp + "Dataset/Tareas_Celula" + celulaLinea
        existingDataset = system.tag.readBlocking([path])[0].value
        columns = list(existingDataset.getColumnNames())

        #---Filtrar las filas que NO sean de esta célula
        filasMantener = []
        for row in range(existingDataset.getRowCount()):
            if existingDataset.getValueAt(row, "celula") != celula:
                filasMantener.append([existingDataset.getValueAt(row, col) for col in columns])

        #---Añadir filas nuevas de la célula actual
        for row in range(datasetNuevo.getRowCount()):
            filasMantener.append([datasetNuevo.getValueAt(row, col) for col in datasetNuevo.getColumnNames()])

        #---Crear dataset final
        finalDataset = ds.toDataSet(columns, filasMantener)

        #---Escribir al tag
        system.tag.writeBlocking([path], [finalDataset])

        #----------------------------------------------------------------------------------------------
        # Actualizar tags derivados
        Tareas.Data.TagsMaquina.tareasPorMaquinaGeneral(celula)
        Tareas.Data.TagsMaquina.inicializarTodosLosDatasetsPiezas(celula)
        
        # Actualizar tarea grafico
        Tareas.Data.Independiente.actualizarTareaGrafico(celula)

        return True

    except Exception as e:
        system.util.getLogger("ScriptError").error(
            "Tareas.Secuencia.General.iniciarEstandar(): {}".format(str(e))
        )
        return False
 
		
def completarTarea(celula, referencia, tipoMaq, tarea, num, manual):
	# Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
	"""
	Llama a funciones para completar tareas.
	Primero completa en el tag dataset
	Luego en base de datos
	Despues reestructura los tiempos de esa tarea
	"""
	#---PARAMETROS----------------------
	elemento = ""
	logger = system.util.getLogger('Pruebas JD')
	logger.info("Tarea completada: {} de la celula: {} en la maquina: {}".format(tarea, celula, tipoMaq))
	#-----------------------------------
	#try:
	rpt = Tareas.Data.General.obtenerRitmoProd(celula, referencia, tipoMaq) # Obtenemos el ritmo de produccion (ya MC-normalizado)
	ocurrencia = Tareas.Data.General.obtenerOcurrencia(celula, referencia, tipoMaq, tarea) # Obtenemos ocurrencia
	
	# Observamos el contador efectivo (celula automatica o logica local segun tipo de tarea)
	contador = Tareas.Data.TagsMaquina.completarTarea(celula, referencia, num, tarea)
	
	# Recalculamos los tiempo de esa tarea segun el contador
	if contador == 0: # Se ha completado antes de lo esperado, se recalcula desde ahora
		Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 0) # Actualiza el resto de tareas
		print "REESTRUCTURADA, base 0"
	elif contador == -1: # Contador mayor que ocurrencia hay que completar la tarea de nuevo
		Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, -1) # Actualiza el resto de tareas
		print "REESTRUCTURADA, YA!"
	elif contador == -2:
		print "Error al realizar la comprobacion del contador en el tag"
		Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, 0) # Actualiza el resto de tareas
		print "ERROR pero reestructurada"
	else: # Contador ya ha empezado la siguiente asi que hay que tener en cuenta esas piezas para el siguiente
		nuevoTiempo = (ocurrencia-contador)*rpt
		Tareas.Data.General.programarTiemposTareas(celula, tipoMaq, tarea, ocurrencia, rpt, nuevoTiempo) # Actualiza el resto de tareas
		print "REESTRUCTURADA, teniendo en cuenta el contador"
		
	
	Tareas.Data.General.completarTarea(celula, tipoMaq, tarea) # Completa la tarea en el tag dataset y crea una nueva
	Tareas.Data.General.completarTareaBD(celula, referencia, tipoMaq, tarea, elemento, manual) # Completa la tarea en base de datos
	
	if contador == -2:
		return False
	else:
		return True
	
	#except Exception as e:
	#	system.util.getLogger("ScriptError").error("Tareas.Secuencia.General.completarTarea(): {}".format(str(e)))
	#	return True
	
	
def saveFile(bytes):
	# Tareas.Secuencia.General.saveFile(bytes)
	"""
	Un script para guardar el estandar
	"""
	try:
		system.file.writeFile("C:\Users\s4e2ihx\OneDrive-Deere&Co\OneDrive - Deere & Co\Escritorio\Tareas 4Comb\Estandar.xlsx", bytes)
		
		return "Archivo guardado en " + path
	except Exception as e:
		return "Error guardando archivo: " + str(e)