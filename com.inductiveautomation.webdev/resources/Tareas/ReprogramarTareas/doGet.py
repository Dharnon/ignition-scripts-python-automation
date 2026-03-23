def doGet(request, session):
	
	#---Seguridad, Permitir Cors-----------------------------------------------------
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	
	#---INFO-------------------------------------------------------------------------
	"""
	Se obtiene la data general para la vista de Tareas desde el tag del dataset de Tareas 'Dataset/Tareas'
	"""
	#--------------------------------------------------------------------------------
	#---PARAMETROS-------------------------------------------------------------------
	tp = constantes.tag_provider
	celulaLinea = constantes.celulaLinea
	path = tp + "Dataset/Tareas_Celula" + celulaLinea
	#--------------------------------------------------------------------------------
	#---Leemos del tag dataset de tareas
	tareas = system.tag.readBlocking([path])
	dataset = tareas[0].value
	
	#---Transformamos el dataset de tareas a un array para el return
	columnNames = list(dataset.getColumnNames())
	rowCount = dataset.getRowCount()
	rows = []
	for rowIndex in range(rowCount):
		rowData = []
		for col in columnNames:
			rowData.append(dataset.getValueAt(rowIndex, col))
		rows.append(rowData)
	
	#---Realizamos el return
	return {
		"json": {
			"tareas": rows
			}
		}