def doPost(request, session):
	# ---------------- CORS ----------------
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	
	import system.util
	import system.file
	import traceback
	from java.util import Base64
	import json as jsonlib  # Importar json para serializar
	
	logger = system.util.getLogger("CargarEstandar")
	
	try:
	    logger.info("=== INICIO doPost Carga Excel ===")
	    
	    # --------- 1. Recibir datos desde React ----------
	    logger.info("PASO 1: Recibiendo datos desde React")
	    data = None
	    if "postData" in request:
	        data = request["postData"]
	        logger.info("Datos recibidos via postData")
	    elif "json" in request:
	        data = request["json"]
	        logger.info("Datos recibidos via json")
	    else:
	        logger.error("No se recibio payload")
	        return {"json": {"error": "No se recibió payload"}}, 400
	    
	    # Asegurar que sea diccionario (si llega como string)
	    logger.info("PASO 2: Validando tipo de datos")
	    if isinstance(data, (str, unicode)):
	        logger.info("Datos son string, parseando a JSON")
	        data = jsonlib.loads(data)
	    logger.info("Tipo de datos validado correctamente")
	
	    # --------- 2. Extraer campos ----------
	    logger.info("PASO 3: Extrayendo campos")
	    fileName = data.get("fileName")
	    base64String = data.get("fileContent") 
	    numPaginas = data.get("paginas", 1)
	    
	    logger.info("Campos extraidos - fileName: " + str(fileName) + ", paginas: " + str(numPaginas))
	    
	    if not fileName or not base64String:
	        logger.error("Falta fileName o fileContent")
	        return {"json": {"error": "Faltan datos obligatorios (fileName, fileContent)"}}, 400
	    
	    logger.info("Bytes recibidos para excel: len= " + str(len(base64String)))
	
	    # --------- 3. Decodificar Base64 a Java Byte Array ----------
	    logger.info("PASO 4: Decodificando Base64 a byte array")
	    try:
	        fileJavaBytes = Base64.getDecoder().decode(base64String)
	        logger.info("Archivo decodificado. Bytes: " + str(len(fileJavaBytes)))
	    except Exception as e:
	        logger.error("Error al decodificar Base64: " + str(e))
	        logger.error(traceback.format_exc())
	        return {"json": {"error": "El archivo Base64 esta corrupto o mal formado"}}, 400
	
	    # --------- 4. Procesar Datos (Llamada a la librería) ----------
	    logger.info("PASO 5: Iniciando procesamiento del Excel con multipleExcelToDb_fb")
	    logger.info("Parametros: fileBytes length=" + str(len(fileJavaBytes)) + ", paginas=" + str(numPaginas))
	    try:
	        #resultado = Tareas.Data.fromExcelToDB.multipleExcelToDb_fb(fileJavaBytes, numPaginas)
	        resultado = Tareas.Secuencia.General.cargarEstandar(fileJavaBytes, numPaginas)
	        logger.info("PASO 6: Excel procesado correctamente")
	        logger.info("Resultado del procesamiento: " + str(resultado))
	    except Exception as e:
	        logger.error("ERROR en multipleExcelToDb_fb: " + str(e))
	        logger.error("Stack trace completo:")
	        logger.error(traceback.format_exc())
	        return {"json": {"error": "Error procesando el contenido del Excel: " + str(e)}}, 500
	
	    # --------- 5. Respuesta final ----------
	    logger.info("PASO 7: Preparando respuesta exitosa")
	    
	    # IMPORTANTE: Construir respuesta sin caracteres especiales
	    response_data = {
	        "success": True,
	        "Info": "Estandar cargado correctamente",  # Sin tilde
	        "archivo": fileName,
	        "detalles": resultado
	    }
	    
	    logger.info("PASO 8: Serializando respuesta a JSON")
	    response_json = jsonlib.dumps(response_data)
	    logger.info("JSON serializado: " + response_json)
	    
	    # Configurar headers manualmente
	    servletResponse.setContentType("application/json")
	    servletResponse.setStatus(200)
	    
	    logger.info("PASO 9: Escribiendo respuesta al output stream")
	    # Escribir directamente al output stream
	    out = servletResponse.getWriter()
	    out.write(response_json)
	    out.flush()
	    out.close()
	    
	    logger.info("=== FIN EXITOSO doPost Carga Excel ===")
	    
	    # NO usar return, ya escribimos directamente
	    return None
	
	except Exception as e:
	    logger.error("=== ERROR CRITICO EN doPost ===")
	    logger.error("Tipo de error: " + str(type(e)))
	    logger.error("Mensaje de error: " + str(e))
	    logger.error("Stack trace completo:")
	    logger.error(traceback.format_exc())
	    
	    # En caso de error, también escribir directamente
	    error_response = jsonlib.dumps({"error": "Error critico: " + str(e)})
	    servletResponse.setContentType("application/json")
	    servletResponse.setStatus(500)
	    out = servletResponse.getWriter()
	    out.write(error_response)
	    out.flush()
	    out.close()
	    return None
	 