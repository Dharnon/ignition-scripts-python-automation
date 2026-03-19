def excelToDataSet(fileBytes, hasHeaders, sheetNum, firstRow, lastRow, firstCol, lastCol):
    # ruta: Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders, sheetNum, firstRow, lastRow, firstCol, lastCol)
    """
    Versión mejorada con manejo de columnas fuera de rango
    """
    import org.apache.poi.ss.usermodel.WorkbookFactory as WorkbookFactory
    import org.apache.poi.ss.usermodel.DateUtil as DateUtil
    from java.io import ByteArrayInputStream
    from java.util import Date
    
    try:
        system.util.getLogger("CargarEstandar").info("Bytes recibidos para excel: len= " + str(len(fileBytes)))
        fileStream = ByteArrayInputStream(fileBytes)
        wb = WorkbookFactory.create(fileStream)
        sheet = wb.getSheetAt(sheetNum)

        # Ajustar rangos de filas
        firstRow = sheet.getFirstRowNum() if firstRow is None else firstRow
        lastRow = sheet.getLastRowNum() if lastRow is None else lastRow
        
        # Obtener el número REAL de columnas (usando la primera fila como referencia)
        sample_row = sheet.getRow(firstRow)
        actual_last_col = sample_row.getLastCellNum() if sample_row else 0
        
        # Ajustar los parámetros de columnas según lo que realmente existe
        firstCol = max(0, firstCol if firstCol is not None else 0)
        lastCol = min(lastCol if lastCol is not None else actual_last_col - 1, actual_last_col - 1)
        
        # Verificación importante para debug
        #print("Columnas detectadas: firstCol=" + str(firstCol) + ", lastCol=" + str(lastCol) + ", total=" + str(((lastCol - firstCol) + 1)) + ")")
        
        data = []
        headers = []
        
        for i in range(firstRow, lastRow + 1):
            row = sheet.getRow(i)
            if row is None:
                continue

            rowOut = []
            if i == firstRow:
                # Definir headers BASADOS EN COLUMNAS REALES
                headers = ['Col{c}' for c in range(firstCol, lastCol + 1)]
                if hasHeaders:
                    try:
                        headers = [
                            row.getCell(c).getStringCellValue() if (row.getCell(c) is not None and c <= lastCol) 
                            else 'Col{c}' 
                            for c in range(firstCol, lastCol + 1)
                        ]
                    except:
                        headers = ['Col{c}' for c in range(firstCol, lastCol + 1)]

            # Procesar SOLO las columnas que existen
            for j in range(firstCol, lastCol + 1):
                try:
                    cell = row.getCell(j)
                    if cell is None:
                        rowOut.append(None)
                        continue
                        
                    cellType = cell.getCellType().toString()
                    if cellType == 'NUMERIC':
                        value = cell.getDateCellValue() if DateUtil.isCellDateFormatted(cell) else cell.getNumericCellValue()
                    elif cellType == 'STRING':
                        value = cell.getStringCellValue()
                    elif cellType == 'BOOLEAN':
                        value = cell.getBooleanCellValue()
                    elif cellType == 'FORMULA':
                        formulaType = str(cell.getCachedFormulaResultType())
                        if formulaType == 'NUMERIC':
                            value = cell.getDateCellValue() if DateUtil.isCellDateFormatted(cell) else cell.getNumericCellValue()
                        elif formulaType == 'STRING':
                            value = cell.getStringCellValue()
                        elif formulaType == 'BOOLEAN':
                            value = cell.getBooleanCellValue()
                        else:
                            value = None
                    else:
                        value = None
                    rowOut.append(value)
                except:
                    rowOut.append(None)  # Si falla cualquier celda, la pone como None

            if len(rowOut) > 0 and (not hasHeaders or i != firstRow):
                data.append(rowOut)

        return system.dataset.toDataSet(headers, data)
        
    except Exception as e:
        system.util.getLogger("CargarEstandar").info("excelToDataset ERROR: " + str(e))
        return None
    finally:
        if 'fileStream' in locals():
            fileStream.close()

def excelToDataSet_Anterior(fileBytes, hasHeaders=False, sheetNum=0, firstRow=None, lastRow=None, firstCol=None, lastCol=None):
	# Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=False, sheetNum=0, firstRow=None, lastRow=None, firstCol=None, lastCol=None)
	#---INFO---------------------------------------------------------------
    """
    Lee el excel y genera un dataset segun filas y columnas.
    """
    #----------------------------------------------------------------------
    import org.apache.poi.ss.usermodel.WorkbookFactory as WorkbookFactory
    import org.apache.poi.ss.usermodel.DateUtil as DateUtil
    from java.io import ByteArrayInputStream
    from java.util import Date
    
    """
       Function to create a dataset from an Excel spreadsheet. It will try to automatically detect the boundaries of the data,
       but helper parameters are available:
       params:
            fileBytes  - The bytes of the uploaded Excel spreadsheet. (required)
            hasHeaders - If true, uses the first row of the spreadsheet as column names.
            sheetNum   - select the sheet to process. defaults to the first sheet.
            firstRow   - select first row to process.
            lastRow    - select last row to process.
            firstCol   - select first column to process
            lastCol    - select last column to process
    """
    
    # Convert bytes into an input stream
    fileStream = ByteArrayInputStream(fileBytes)
    
    # Read the Excel workbook from the input stream
    wb = WorkbookFactory.create(fileStream)
    
    # Select the sheet to process
    sheet = wb.getSheetAt(sheetNum)

    # Define boundaries if not provided
    if firstRow is None:
        firstRow = sheet.getFirstRowNum()
    if lastRow is None:
        lastRow = sheet.getLastRowNum()

    data = []
    headers = []
    for i in range(firstRow, lastRow + 1):
        row = sheet.getRow(i)
        if row is None:
            continue  # Skip empty rows

        rowOut = []
        if i == firstRow:
            if firstCol is None:
                firstCol = row.getFirstCellNum()
            if lastCol is None:
                lastCol = row.getLastCellNum()
            else:
                lastCol += 1  # If lastCol is specified, add 1 to it
            
            # Process headers if needed
            if hasHeaders:
                headers = [row.getCell(c).getStringCellValue() for c in range(firstCol, lastCol)]
            else:
                headers = ['Col' + str(cNum) for cNum in range(firstCol, lastCol)]
        
        # Process each cell in the row
        for j in range(firstCol, lastCol):
            cell = row.getCell(j)
            if cell is None:
                rowOut.append(None)
            else:
                cellType = cell.getCellType().toString()
                if cellType == 'NUMERIC':
                    if DateUtil.isCellDateFormatted(cell):
                        value = cell.dateCellValue
                    else:
                        value = cell.getNumericCellValue()
                        #if value == int(value):
                            #value = int(value)
                elif cellType == 'STRING':
                    value = cell.getStringCellValue()
                elif cellType == 'BOOLEAN':
                    value = cell.getBooleanCellValue()
                elif cellType == 'BLANK':
                    value = None
                elif cellType == 'FORMULA':
                    formulaType = str(cell.getCachedFormulaResultType())
                    if formulaType == 'NUMERIC':
                        if DateUtil.isCellDateFormatted(cell):
                            value = cell.dateCellValue
                        else:
                            value = cell.getNumericCellValue()
                            if value == int(value):
                                value = int(value)
                    elif formulaType == 'STRING':
                        value = cell.getStringCellValue()
                    elif formulaType == 'BOOLEAN':
                        value = cell.getBooleanCellValue()
                    elif formulaType == 'BLANK':
                        value = None
                else:
                    value = None
                rowOut.append(value)
        
        if len(rowOut) > 0 and not hasHeaders or i != firstRow:
            data.append(rowOut)

    # Close the input stream
    fileStream.close()
    
    return system.dataset.toDataSet(headers, data)

def checkStructure(dataSet, tablaSecuencia, referencia, celula):
 	# ruta: Tareas.Data.fromExcelToDB.checkStructure(dataSet, tablaSecuencia, referencia, celula)
    """
    Verifica que las columnas esperadas en el dataset coincidan con las de la tabla en BD
    Incluyendo las columnas adicionales (referencia y celula) que no están en el dataset principal
    """
    # 1. Verificar que tenemos los datos adicionales necesarios
    if referencia is None or celula is None:
        print("Faltan datos de referencia o célula en el Excel")
        return False

    # 2. Verificar que el dataset tiene suficientes columnas
    columnas_esperadas = [
        'maquina',
        'num',
        'elemento',
        'tipo',
        'T1',       
        'T2',       
        'T3',       
        'T4',       
        'T5',       
        'ac',
        'pf',
        'min_std',
        'ocurrencia',
        'min_std_ciclo',
        'min_std_ciclo_pf',
        'descripcion'
    ]
    headers_esperados = [
        'maquina',
        'nº',
        'elemento',
        'tipo', 
        'ac', 
        'p&f', 
        'minutos std', 
        'ocurrencia', 
        'min std/ciclo', 
        'min std/ciclo (p&f)', 
        'descripciÓn'
 	]
       
    headers_reales = [
     str(h).strip().lower() 
     for h in dataSet.getColumnNames() 
     if str(h).strip().lower() not in {'t1', 't2', 't3', 't4', 't5'}
 	]
    
    if len(headers_reales) != len(headers_esperados):
        print(
            "Número de columnas incorrecto. "
            "Esperadas: " + str(len(headers_esperados)) + ", Encontradas: " + str(len(headers_reales))
        )
        return False 
    # 3. Verificar estructura con la tabla en BD (incluyendo referencia y celula)
    for esperado, real in zip(headers_esperados, headers_reales):
        if esperado.lower() != real:
            print(
                "Error en columna " + str(headers_reales.index(real) + 1) + "\n"
                "Se esperaba: " + str(esperado) + "\n"
                "Se encontró: " + str(real)
            )
            return False
    
    # 3. Verificar estructura en BD (tu código actual)
    try:
        meta_query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
        result = system.db.runPrepQuery(meta_query, [tablaSecuencia])
        
        columnas_requeridas_bd = {
            'referencia', 'maquina', 'num', 'elemento', 'tipo',
            'ac', 'pf', 'min_std', 'ocurrencia', 'min_std_ciclo',
            'min_std_ciclo_pf', 'descripcion', 'prioridad', 'celula'
        }
        
        columnas_bd = {row[0].lower() for row in result}
        faltantes = columnas_requeridas_bd - columnas_bd
        
        if faltantes:
   			print("En BD faltan: " + str(', '.join(faltantes)))
   			return False
        
        print "Todo bien"    
        return True
        
    except Exception as e:
        print("Error al verificar BD: " + str(str(e)))
        return False
       
def excelToDb(filepath, page):
	#---INFO-----------------------------------------------------------
	"""
	Funciona con el Excel estándar.
	Borra la secuencia que hay en base de datos de esa referencia.
	Lee filas, columnas y la referencia.
	Lo ordena y lo inserta directamente en la base de datos.
	"""
	#------------------------------------------------------------------
	#---PARAMETROS-----------------------------------------------------
	tablaSecuencia = constantes.LINEA + "_Secuencia"
	database = constantes.Database_Tareas
	tp = constantes.tag_provider
	#------------------------------------------------------------------

	# Convertir archivo a bytes
	fileBytes = system.file.readFileAsBytes(filepath)

	# Obtener dataset desde el Excel
	dataSet = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=True, sheetNum=page, firstRow=14, lastRow=None, firstCol=None, lastCol=None)
	reference = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=False, sheetNum=page, firstRow=1, lastRow=1, firstCol=0, lastCol=1)
	celula = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=False, sheetNum=page, firstRow=2, lastRow=2, firstCol=0, lastCol=1)

	# Datos constantes de la referencia
	headerC1 = reference.data[0][0]
	dataC1 = reference.data[1][0]
	# Datos constantes de la celula
	headerC2 = celula.data[0][0]
	dataC2 = celula.data[1][0]
	
	# Ponemos la referencia al tag segun el estandar
	print "Celula: " + str(dataC2)
	print "Referencia: " + str(dataC1)
	referencia = str(dataC1)
	celula = str(dataC2)
	
	#tagPath = tp + 'Celula' + str(dataC2) + '/Maq_1/Datos_Cuasiconstantes/Referencia'
	#system.tag.writeBlocking([tagPath], [referencia])
	
 	# Comprobación de estructura de excel y tabla
 	
 	#if not Tareas.Data.fromExcelToDB.checkStructure(dataSet, tablaSecuencia, dataC1, dataC2):
	#	print("La estructura del Excel no coincide con la tabla de base de datos")
    #    return False
    
	
	# Borrar los datos existentes segun la referencia
	Tareas.Data.fromExcelToDB.deleteTable(tablaSecuencia, dataC1, dataC2)

	# Recorrer el dataset e insertar en la tabla
	filas = dataSet.getRowCount()

	for row in range(filas):
		if dataSet.data[0][row] is not None:
			# Parámetros para insertar
			parameters = [
				dataC1,  # referencia
				dataSet.data[0][row],  # maquina
				int(dataSet.data[1][row]),  # num
				dataSet.data[2][row],  # elemento
				dataSet.data[3][row],  # tipo
				int(dataSet.data[9][row]),  # ac
				dataSet.data[10][row],  # pf
				dataSet.data[11][row],  # min_std
				float(dataSet.data[12][row]),  # ocurrencia
				dataSet.data[13][row],  # min_std_ciclo
				dataSet.data[14][row],  # min_std_ciclo_pf
				dataSet.data[15][row],  # descripcion
				1,  # prioridad
				dataC2 # celula
			]

			# Consulta SQL dinámica
			query = """
				INSERT INTO {0} (
					referencia,
					maquina,
					num,
					elemento,
					tipo,
					ac,
					pf,
					min_std,
					ocurrencia,
					min_std_ciclo,
					min_std_ciclo_pf,
					descripcion,
					prioridad,
					celula
				) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
			""".format(tablaSecuencia)

			# Ejecutar el insert
			try:
				system.db.runPrepUpdate(query, parameters, database)
			except Exception as e:
				print "Error al insertar los datos: " + str(e)
	
	datos = [celula, referencia]
	
	return datos

def multipleExcelToDb(filepath, pages):
	# Tareas.Data.fromExcelToDB.multipleExcelToDb(filepath, pages)
	#---INFO----------------------------------------------------
	"""
	De un mismo excel lee de varias paginas.
	Si en pages pones 4, lee del 0 al 3.
	"""
	
	for page in range(pages):
		Tareas.Data.fromExcelToDB.excelToDb(filepath, page)
		
	return True

def deleteTable(table, reference, celula):
	# Tareas.Data.fromExcelToDB.deleteTable("table", reference, celula)
	#---INFO-----------------------------------------------------------
	"""
	Borra lo que haya de una referencia en las tablas permitidas
	"""
	#------------------------------------------------------------------
	#---PARAMETROS-----------------------------------------------------
	tablaSecuencia = constantes.LINEA + "_Secuencia"
	tablaTareas = constantes.LINEA + "_Tareas"
	tablaResumen = constantes.LINEA + "_Tareas_Resumen"
	database = constantes.Database_Tareas
	#------------------------------------------------------------------
	allowed_tables = [tablaSecuencia, tablaTareas, tablaResumen]  # ejemplo de control
	if table not in allowed_tables:
	    raise ValueError("Tabla no permitida")
	
	query = "DELETE FROM " + table + " WHERE referencia = '" + str(reference) + "' AND celula = '" + str(celula) + "'"
	print query
	try:
		system.db.runUpdateQuery(query, database)
		return True
	except Exception as e:
	    system.gui.errorBox("Error al borrar los datos: " + str(e))
	    return False
	    
def inactivoTable(table, reference, celula):
	# Tareas.Data.fromExcelToDB.inactivoTable("table", reference, celula)
	#---INFO-----------------------------------------------------------
	"""
	Pone la columna activo a 0 para ponerlo como inactivo.
	"""
	#------------------------------------------------------------------
	#---PARAMETROS-----------------------------------------------------
	tablaSecuencia = constantes.LINEA + "_Secuencia"
	tablaTareas = constantes.LINEA + "_Tareas"
	tablaResumen = constantes.LINEA + "_Tareas_Resumen"
	database = constantes.Database_Tareas
	#------------------------------------------------------------------
	allowed_tables = [tablaSecuencia, tablaTareas, tablaResumen]  # ejemplo de control
	if table not in allowed_tables:
	    raise ValueError("Tabla no permitida")
	
	query = "UPDATE " + table + " set activo = 0 WHERE referencia = '" + str(reference) + "' AND celula = '" + str(celula) + "'"
	print query
	try:
		system.db.runUpdateQuery(query, database)
		return True
	except Exception as e:
	    system.gui.errorBox("Error al ponerlo inactivo: " + str(e))
	    return False
	
def deleteTable_Secuencia():
	# Tareas.Data.fromExcelToDB.deleteTable_Secuencia()
	#---INFO-----------------------------------------------------------
	"""
	Borra lo quehay en la tabla Secuencia
	"""
	#------------------------------------------------------------------
	#---PARAMETROS-----------------------------------------------------
	tablaSecuencia = constantes.LINEA + "_Secuencia"
	database = constantes.Database_Tareas
	#------------------------------------------------------------------
	query = "DELETE FROM " + tablaSecuencia
	print query
	try:
		system.db.runUpdateQuery(query, database)
	except Exception as e:
	    system.gui.errorBox("Error al borrar los datos: " + str(e))
	return True
	
def tareasTable(celula, referencia):
	# Tareas.Data.fromExcelToDB.tareasTable(celula, referencia)
	#---INFO-----------------------------------------------------------
	"""
	Según la tabla Secuencia, inserta en la tabla de Tareas.
	"""
	#------------------------------------------------------------------
	#---PARAMETROS-----------------------------------------------------
	tablaSecuencia = constantes.LINEA + "_Secuencia"
	tablaTareas = constantes.LINEA + "_Tareas"
	database = constantes.Database_Tareas
	tablaSecCompl = "[" + database + "].[dbo].[" + tablaSecuencia + "]"
	#------------------------------------------------------------------
	
	#---Borrar tabla
	Tareas.Data.fromExcelToDB.deleteTable(tablaTareas, referencia, celula)
	
	#---Insertar tabla
	
	query = """
	INSERT INTO [dbo].[{tablaTareas}] (
	    referencia,
	    tarea,
	    maquina,
	    ocurrenciaStd,
	    ocurrencia,
	    turno,
	    elemento,
	    prioridad,
	    celula,
	    min_std,
	    min
	)
	SELECT
	    referencia,
	    CONCAT(descripcion, ' 1/', CAST(CAST(1.0 / ocurrencia AS INT) AS VARCHAR)) AS tarea,
	    maquina,
	    CAST(1.0 / ocurrencia AS INT) AS ocurrenciaStd,
	    NULL AS ocurrencia,
	    NULL AS turno,
	    elemento,
	    prioridad,
	    celula,
	    min_std,
	    NULL AS min
	FROM 
	    {tablaSecCompl}
	WHERE
	    ocurrencia > 0
	    AND referencia = ?
	    AND celula = ?
	""".format(
	    tablaTareas=tablaTareas,
	    tablaSecCompl=tablaSecuencia
	)

	# Ejecutar el query
	try:
	    system.db.runPrepUpdate(query, [referencia, celula], database)
	except Exception as e:
	    system.gui.errorBox("Error al insertar los datos: " + str(e))
	
	return True
	
def insertarTareasEnTablaResumen(celula, referencia):
	# Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(celula, referencia)
	"""
	Obtener la información general para la vista de tareas
	"""
	#---PARAMETROS----------------------------------------------
	# Obtener los datos desde la función existente
	dataset = Tareas.Data.Teorico.obtenerTareas(celula, referencia)

	# Nombre de la tabla de destino
	tablaTareasResumen = constantes.LINEA + "_Tareas_Resumen"
	
	# Nombre de la base de datos
	database = constantes.Database_Tareas
	
	#---Borrar tabla
	#Tareas.Data.fromExcelToDB.deleteTable(tablaTareasResumen, referencia, celula)
	#---Poner los ids de la tabla como inactivo
	Tareas.Data.fromExcelToDB.inactivoTable(tablaTareasResumen, referencia, celula)
	#-------------------------------------------------------------

	# Preparar la query de inserción
	insert_query = """
	INSERT INTO {tabla} (
		referencia,
		tarea,
		maquina,
		ocurrencia,
		elementos,
		celula,
		activo
	)
	VALUES (?, ?, ?, ?, ?, ?, ?)
	""".format(tabla=tablaTareasResumen)

	# Recorrer el dataset e insertar cada fila
	for i in range(dataset.rowCount):
		params = [
			dataset.getValueAt(i, "referencia"),
			dataset.getValueAt(i, "tarea"),
			dataset.getValueAt(i, "maquina"),
			dataset.getValueAt(i, "ocurrencia"),
			dataset.getValueAt(i, "elementos"),
			dataset.getValueAt(i, "celula"),
			1
		]

		system.db.runPrepUpdate(insert_query, params, database)

	print "Inserción completada: {} filas insertadas en '{}'.".format(dataset.rowCount, tablaTareasResumen)
	

import system.db
from java.io import ByteArrayInputStream

def multipleExcelToDb_fb(fileBytes, pages):
    """
    Recibe un byte[] de Java puro y procesa las paginas indicadas.
    """
    resultados = []
    
    for page in range(pages):
        # Procesamos cada página
        # Nota: fileBytes ya es un array de Java válido, se pasa directo.
        res = excelToDb_fb(fileBytes, page)
        resultados.append(res)

    return resultados

def excelToDb_fb(fileBytes, page):
    #--- INFO -----------------------------------------------------------
    # Lee el excel desde memoria y usa transacciones SQL para insertar
    #------------------------------------------------------------------
    
    # 1. Definición de Constantes
    tablaSecuencia = constantes.LINEA + "_Secuencia"
    database = constantes.Database_Tareas
    # database = "NombreDeTuConexion" # Descomentar si no usas la constante
    
    # 2. Lectura del Excel
    # Asumimos que tu función excelToDataSet acepta byte[] de Java.
    # Si falla, prueba envolviendo en: stream = ByteArrayInputStream(fileBytes)
    try:
        dataSet = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=True, sheetNum=page, firstRow=14, lastRow=None, firstCol=None, lastCol=None)
        reference = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=False, sheetNum=page, firstRow=1, lastRow=1, firstCol=0, lastCol=1)
        celula = Tareas.Data.fromExcelToDB.excelToDataSet(fileBytes, hasHeaders=False, sheetNum=page, firstRow=2, lastRow=2, firstCol=0, lastCol=1)
    except Exception as e:
        raise Exception("Error leyendo estructura del Excel en pag " + str(page) + ": " + str(e))

    # Validar que se leyó algo
    if reference.rowCount == 0 or celula.rowCount == 0:
        raise Exception("No se encontraron datos de Referencia o Célula en el Excel")

    # Extraer datos constantes
    headerC1 = reference.data[0][0]
    dataC1 = reference.data[1][0] # Referencia
    headerC2 = celula.data[0][0]
    dataC2 = celula.data[1][0]    # Celula
    
    print "Procesando Celula: %s, Referencia: %s" % (dataC2, dataC1)

    # 3. Limpieza previa
    # Borrar los datos existentes
    Tareas.Data.fromExcelToDB.deleteTable(tablaSecuencia, dataC1, dataC2)

    # 4. Inserción Masiva (Optimizada con Transacción)
    filas = dataSet.getRowCount()
    
    query = """
    INSERT INTO {0} (
        referencia, maquina, num, elemento, tipo, ac, pf, min_std, 
        ocurrencia, min_std_ciclo, min_std_ciclo_pf, descripcion, prioridad, celula
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """.format(tablaSecuencia)

    # Iniciamos transacción. Esto bloquea la tabla para escritura rápida y segura
    txId = system.db.beginTransaction(database)
    
    try:
        for row in range(filas):
            # Solo insertamos si la columna 'maquina' (indice 0) tiene datos
            if dataSet.data[0][row] is not None:
                parameters = [
                    dataC1,                         # referencia
                    dataSet.data[0][row],           # maquina
                    int(dataSet.data[1][row]),      # num
                    dataSet.data[2][row],           # elemento
                    dataSet.data[3][row],           # tipo
                    int(dataSet.data[9][row]),      # ac
                    dataSet.data[10][row],          # pf
                    dataSet.data[11][row],          # min_std
                    float(dataSet.data[12][row]),   # ocurrencia
                    dataSet.data[13][row],          # min_std_ciclo
                    dataSet.data[14][row],          # min_std_ciclo_pf
                    dataSet.data[15][row],          # descripcion
                    1,                              # prioridad
                    dataC2                          # celula
                ]
                
                # Ejecutar dentro de la transacción (fíjate en tx=txId)
                system.db.runPrepUpdate(query, parameters, database, tx=txId)
        
        # Si todo el bucle termina bien, guardamos cambios
        system.db.commitTransaction(txId)
        
    except Exception as e:
        # Si falla algo, deshacemos todo para no dejar datos a medias
        system.db.rollbackTransaction(txId)
        system.db.closeTransaction(txId) # Importante cerrar tras rollback
        raise Exception("Error SQL insertando datos: " + str(e))
        
    # Cerrar transacción exitosa
    system.db.closeTransaction(txId)
    
    return [str(dataC2), str(dataC1)]
 