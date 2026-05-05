def doGet(request, session):
	#---Seguridad, Permitir Cors-----------------------------------------------------
	servletResponse = request["servletResponse"]
	servletResponse.addHeader("Access-Control-Allow-Origin", "*")
	servletResponse.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	servletResponse.addHeader("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Requested-With")
	
	#---INFO--------------------------------------------------------------------------
	"""
	Obtiene la data general para la vista de Sinóptico, con transformaciones según el tipo de máquina.
	"""
	#---PARAMETROS---------------------------------------------------------------------
	celulas = constantes.celulas
	tp = constantes.tag_provider
	data = []
	
	#---PROCESAMIENTO------------------------------------------------------------------
	for celula in celulas:
		#---1.Obtener de la celula (Referencia y OEE Status)
	    referencia = Sinoptico.Data.General.obtenerReferencia(celula)
	    OEE_Status = Sinoptico.Data.General.obtenerOEEStatus(celula, referencia)
	    
	    # Numero de maquinas por celula
	    path = tp + "Celula" + celula
	    total = len(system.tag.browse(path, {"name": "Maq_*"})) # Mira el numero de tags dentro de una carpeta, que empiecen por "Maq_"
	
	    # Inicialización de estructuras
	    dispAuto, piezasAuto, idAuto, posAuto, conexionAuto = [], [], [], [], []
	    maquinas = []
	
	    for num in range(1, total + 1):
	    	#---2.Obtener si es Automatico o no
	        auto = Sinoptico.Data.General.obtenerAuto(celula, num) # 0 No auto; 1 Auto
	        plc_cnc = Sinoptico.Data.General.obtenerPLC_CNC(celula, num) # 0 PLC; 1 CNC
	        #---3.Tipo de maquina
	        tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)
	        idMaq = Sinoptico.Data.General.obtenerIDMaquinaOriginal(celula, num)
	
	        # --- Maquinas Automáticas (PLC Central) ---
	        if (tipoMaq == "CELULA" or tipoMaq == "BIN PICKING") and auto == 1 and plc_cnc == 0:
	            posAuto.append(Sinoptico.Data.General.obtenerPosicion(celula, num))					#---Posicion de la automatica respecto a la celula
	            idAuto.append(Sinoptico.Data.General.obtenerIDMaquina(celula, num))					#---Obtener id de la maquina
	            dispAuto.append(Sinoptico.Data.General.obtenerDisponibilidad(celula, num))			#---Obtener Status Disponibilidad (PLC Central)
	            if tipoMaq == "CELULA":
	            	piezasAuto.append(Sinoptico.Data.General.obtenerAutoContador(celula, referencia))#---Obtener Contador Piezas (PLC Central)
	            elif tipoMaq == "BIN PICKING":
	            	piezasAuto.append(Sinoptico.Data.General.obtenerPLCContador_v2(celula, num, idMaq))#---Obtener Contador Piezas (Bin Picking)
	            conexionAuto.append(Sinoptico.Data.General.obtenerConexion(celula, num))			#---Obtener estado de la conexion (PLC Central)
	            
	        # --- Maquinas Automáticas (PLC) Secundarias ---
	        elif (tipoMaq != "CELULA" or tipoMaq != "BIN PICKING") and auto == 1 and plc_cnc == 0:
	            maquinas.append([
	                Sinoptico.Data.General.obtenerPosicionAuto(celula, num),		#---0.Posicion de la maquina respecto a la celula automatica
	                [tipoMaq],														#---1.Tipo de maquina
	                [Sinoptico.Data.General.obtenerIDMaquina(celula, num)],			#---2.Id de la maquina
	                [Sinoptico.Data.General.obtenerDisponibilidad(celula, num)],	#---3.Status Disponibilidad (aunque haremos caso al Status Disponibilidad del PLC central)
	                [Sinoptico.Data.General.obtenerCiclo(celula, num)],				#---4.Status Ciclo
	                [0],															#---5.Contador de piezas (No aplica, debe poner PLC Central)
	                [Sinoptico.Data.General.obtenerSaturacion(celula, num)],		#---6.Saturacion de la maquina [PreSat, Sat]
	                Sinoptico.Data.General.obtenerAutoHerramienta(celula, num),		#---7.Herramientas de la maquina [VidaTeorica, Vida Util]
	                [Sinoptico.Data.General.obtenerAlarmas(celula, num)],			#---8.Alarmas de la maquina
	                Sinoptico.Data.General.obtenerPosicion(celula, num),			#---9.Posicion de la automatica dentro de la celula
	                Sinoptico.Data.General.obtenerConexion(celula, num)				#---10.Estado de la conexion de la amquina (Good or Bad)
	            ])
	            
	        # --- Maquinas PLC que no pertenecen a un grupo de auto ---
	        elif (tipoMaq != "CELULA" or tipoMaq != "BIN PICKING") and auto == 0 and plc_cnc == 0:
	            maquinas.append([
	                Sinoptico.Data.General.obtenerPosicion(celula, num), 			#---0.Posicion de la maquina respecto a la celula
	                [tipoMaq], 														#---1.Tipo de maquina
	                [Sinoptico.Data.General.obtenerIDMaquina(celula, num)],			#---2.Id de la maquina
	                [Sinoptico.Data.General.obtenerDisponibilidad(celula, num)],	#---3.Status Disponibilidad
	                [Sinoptico.Data.General.obtenerCiclo(celula, num)],				#---4.Status Ciclo
	                [Sinoptico.Data.General.elegirPLCContador(celula, num, idMaq, referencia)],	#---5.Contador de piezas 
	                [Sinoptico.Data.General.obtenerSaturacion(celula, num)],		#---6.Saturacion de la maquina [PreSat, Sat]
	                Sinoptico.Data.General.obtenerAutoHerramientaConNombre(celula, num),		#---7.Herramientas de la maquina [VidaTeorica, VidaUtil]
	                [Sinoptico.Data.General.obtenerAlarmas(celula, num)],			#---8.Alarmas de la maquina
	                0,																#---9.Posicion dentro de la automatica (No aplica por eso es 0); Sinoptico.Data.General.obtenerPosicionAuto(celula, num)
	                Sinoptico.Data.General.obtenerConexion(celula, num)				#---10.Estado de la conexion de la amquina (Good or Bad)
	            ])
	
	        # --- Maquinas CNC ---
	        elif (tipoMaq != "CELULA" or tipoMaq != "BIN PICKING") and auto == 0 and plc_cnc == 1:
	            maquinas.append([
	                Sinoptico.Data.General.obtenerPosicion(celula, num), 			#---0.Posicion de la maquina respecto a la celula
	                [tipoMaq], 														#---1.Tipo de maquina
	                [Sinoptico.Data.General.obtenerIDMaquina(celula, num)],			#---2.Id de la maquina
	                [Sinoptico.Data.General.obtenerDisponibilidad(celula, num)],	#---3.Status Disponibilidad
	                [Sinoptico.Data.General.obtenerCiclo(celula, num)],				#---4.Status Ciclo
	                [Sinoptico.Data.General.obtenerCNCContador(celula, num)],		#---5.Contador de piezas (Maquina CNC)
	                [Sinoptico.Data.General.obtenerSaturacion(celula, num)],		#---6.Saturacion de la maquina [PreSat, Sat]
	                Sinoptico.Data.General.obtenerCNCHerramientaConNombre(celula, num),		#---7.Herramientas de la maquina [VidaTeorica, VidaUtil]
	                [Sinoptico.Data.General.obtenerAlarmas(celula, num)],			#---8.Alarmas de la maquina
	                0,																#---9.Posicion dentro de la automatica (No aplica por eso es 0); Sinoptico.Data.General.obtenerPosicionAuto(celula, num)
	                Sinoptico.Data.General.obtenerConexion(celula, num)				#---10.Estado de la conexion de la amquina (Good or Bad)
	            ])
	           
	
	    data.append([celula, referencia, OEE_Status, dispAuto, piezasAuto, idAuto, posAuto, conexionAuto, maquinas])
	
	#---RESPUESTA JSON-----------------------------------------------------------------
	return { "json": 
				{ 
				"data": data 
				} 
			}