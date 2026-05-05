import xml.etree.ElementTree as ET

def cambioHerramientas(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None):
    # Tareas.Data.GearFlow.cambioHerramientas(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None)
    """
    fecha: la fecha de cuando deberia ser el cambio de herramientas (coger previamente de: Tareas.Data.General.obtenerProximaFecha())
    tipoSolicitud: "CONTROL" o "HERRAMIENTA"
    referencia: "R120636" por ejemplo
    celula: "142A" por ejemplo
    herramienta: "TALLADORA" o "AFEITADORA"
    Si se envia algun parametro como None no afecta a la consulta
    """
    
    # Fechas dinámicas usando system.date de Ignition
    #now = system.date.now()
    #antes = system.date.addDays(now, -1)  # 1 días atrás
    
    # Formato ISO compatible con SOAP usando system.date
    #now_iso = system.date.format(now, "yyyy-MM-dd'T'HH:mm:ss")
    #antes_iso = system.date.format(antes, "yyyy-MM-dd'T'HH:mm:ss")
    
    # +- 2 horas de la fecha asignada
    now = fecha
    #now = system.date.addHours(fecha, 2)
    antes = system.date.addSeconds(fecha, -60)
    #antes = system.date.addHours(fecha, -2)
    
    now_iso = system.date.format(now, "yyyy-MM-dd'T'HH:mm:ss")
    antes_iso = system.date.format(antes, "yyyy-MM-dd'T'HH:mm:ss")
    print now_iso
    print antes_iso
    
    celulas = constantes.celulas
    idCelulas = constantes.idCelulas
    
    if celula in celulas:
    	indice = celulas.index(celula)
    	idCelula = idCelulas[indice]
    else:
    	idCelula = None
    
    if herramienta == "CELULA":
        herramienta = None
    # Parámetros de filtrado
    filtros = {
        "fecha_inicio": antes_iso,
        "fecha_fin": now_iso,
        "tipo_solicitud": tipoSolicitud,
        "referencia": referencia,
        "celula": idCelula,
        "herramienta": herramienta  # "AFEITADORA", o "TALLADORA"
    }
    print filtros
    
    # Llamar a la función de filtrado (debe estar en el mismo módulo)
    resultados = filtrar_racks(**filtros)
    
    for r in resultados:
        print("Código Rack: {0} | Criterio: {1} | Fecha: {2}".format(r["codigo_rack"], r["criterio"], r["fecha"]))
    
    if resultados:
    	return resultados[0]["criterio"]
    else:
    	return None # Sin datos
    	
def grafico(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None):
    # Tareas.Data.GearFlow.grafico(fecha, tipoSolicitud=None, referencia=None, celula=None, herramienta=None)
    """
    fecha: la fecha de cuando deberia ser el cambio de herramientas (coger previamente de: Tareas.Data.General.obtenerProximaFecha())
    tipoSolicitud: "CONTROL" o "HERRAMIENTA"
    referencia: "R120636" por ejemplo
    celula: "142A" por ejemplo
    herramienta: "TALLADORA" o "AFEITADORA"
    Si se envia algun parametro como None no afecta a la consulta
    """
    
    # Fechas dinámicas usando system.date de Ignition
    #now = system.date.now()
    #antes = system.date.addDays(now, -1)  # 1 días atrás
    
    # Formato ISO compatible con SOAP usando system.date
    #now_iso = system.date.format(now, "yyyy-MM-dd'T'HH:mm:ss")
    #antes_iso = system.date.format(antes, "yyyy-MM-dd'T'HH:mm:ss")
    
    # Obtener fecha y hora actual
    ahora = system.date.now()
    hora_actual = system.date.getHour24(fecha)
    
    # Determinar el turno y calcular antes y now
    if 6 <= hora_actual < 14:  # Turno 1: 6 AM - 2 PM
        antes = system.date.setTime(ahora, 6, 0, 0)
        now = system.date.setTime(ahora, 14, 0, 0)
        
    elif 14 <= hora_actual < 22:  # Turno 2: 2 PM - 10 PM
        antes = system.date.setTime(ahora, 14, 0, 0)
        now = system.date.setTime(ahora, 22, 0, 0)
        
    else:  # Turno 3: 10 PM - 6 AM
        if hora_actual >= 22:  # Entre 10 PM y medianoche
            antes = system.date.setTime(ahora, 22, 0, 0)
            now = system.date.setTime(system.date.addDays(ahora, 1), 6, 0, 0)
        else:  # Entre medianoche y 6 AM
            antes = system.date.setTime(system.date.addDays(ahora, -1), 22, 0, 0)
            now = system.date.setTime(ahora, 6, 0, 0)
    
    
    now_iso = system.date.format(now, "yyyy-MM-dd'T'HH:mm:ss")
    antes_iso = system.date.format(antes, "yyyy-MM-dd'T'HH:mm:ss")
    print now_iso
    print antes_iso
    
    celulas = constantes.celulas
    idCelulas = constantes.idCelulas
    
    if celula in celulas:
    	indice = celulas.index(celula)
    	idCelula = idCelulas[indice]
    else:
    	idCelula = None
    
    if herramienta == "CELULA":
        herramienta = None
    # Parámetros de filtrado
    filtros = {
        "fecha_inicio": antes_iso,
        "fecha_fin": now_iso,
        "tipo_solicitud": tipoSolicitud,
        "referencia": referencia,
        "celula": idCelula,
        "herramienta": herramienta  # "AFEITADORA", o "TALLADORA"
    }
    print filtros
    
    # Llamar a la función de filtrado (debe estar en el mismo módulo)
    resultados = filtrar_racks(**filtros)
    
    for r in resultados:
        print("Código Rack: {0} | Criterio: {1} | Fecha: {2}".format(r["codigo_rack"], r["criterio"], r["fecha"]))
    
    if resultados:
    	return resultados[0]["criterio"]
    else:
    	return None # Sin datos

def filtrar_racks(fecha_inicio=None, fecha_fin=None, tipo_solicitud=None, referencia=None, celula=None, herramienta=None):
    """
    Filtra solicitudes del XML de laboratorio y devuelve lista de diccionarios con:
        - codigo_rack
        - criterio (verificado)
        - fecha
    
    Filtros opcionales:
        - fecha_inicio, fecha_fin: strings en formato ISO 'YYYY-MM-DDTHH:MM:SS'
        - tipo_solicitud: 'HERRAMIENTA', 'CONTROL', etc.
        - referencia: código de referencia
        - celula: id de célula
        - herramienta: 'TALLADORA' o 'AFEITADORA' (mapea según descripción)
    
    Parámetros vacíos o None no aplican filtro.
    """
    
    # --- URL del servicio ---
    url = "http://fgetceapp27:1682/svcsyncgf.asmx"

    # --- Envelope SOAP dinámico ---
    soapEnvelope = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                   xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <ListaGraficosdelrackLaboratorio xmlns="http://www.hexaingenieros_SvcSync.com/">
          <rack_salida></rack_salida>
          <id_ref>0</id_ref>
          <id_es>0</id_es>
          <fechaIni>{fechaIni}</fechaIni>
          <fechaFin>{fechaFin}</fechaFin>
          <zona>1</zona>
          <VerificadosOK_NOK_NA>TODOS</VerificadosOK_NOK_NA>
          <graficosMetalurgia>false</graficosMetalurgia>
          <NMostrarResoluciones>0</NMostrarResoluciones>
          <resultadoDocumento>TODOS</resultadoDocumento>
          <codigoSap></codigoSap>
        </ListaGraficosdelrackLaboratorio>
      </soap:Body>
    </soap:Envelope>
    """.format(fechaIni=fecha_inicio, fechaFin=fecha_fin)

    # --- Llamada HTTP usando system.net.httpClient() de Ignition ---
    try:
        client = system.net.httpClient()
        response = client.post(
            url,
            data=soapEnvelope,
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://www.hexaingenieros_SvcSync.com/ListaGraficosdelrackLaboratorio"
            }
        )

        # --- Parsear XML ---
        xml_text = response.getText()
        
        # Verificar si hay error en la respuesta
        if response.getStatusCode() != 200:
            print("Error en la respuesta SOAP. Código: {}".format(response.getStatusCode()))
            return []
            
    except Exception as e:
        print("Error al realizar la llamada SOAP: {}".format(str(e)))
        return []
    
    # Mapeo de herramienta según coincidencias parciales
    herramientas_map = {
        "TALLADORA": ["FRESA", "TALLADO"],
        "AFEITADORA": ["DISCO", "AFEITADO"]
    }
    
    def corresponde_herramienta(descripcion, busqueda):
        if not busqueda:
            return True
        if busqueda not in herramientas_map:
            return False
        claves = herramientas_map[busqueda]
        descripcion_upper = descripcion.upper() if descripcion else ""
        for clave in claves:
            if clave.upper() in descripcion_upper:
                return True
        return False
    
    # Namespace para parsear el XML
    ns = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns': 'http://www.hexaingenieros_SvcSync.com/'
    }
    
    try:
        root = ET.fromstring(xml_text)
        solicitudes = root.findall('.//ns:TObtenerSolicitudesGrafico', ns)
    except Exception as e:
        print("Error al parsear XML: {}".format(str(e)))
        return []

    resultados = []

    for s in solicitudes:
        try:
            # Obtener datos de cada solicitud
            codigo_rack = s.find('ns:rack', ns).text if s.find('ns:rack', ns) is not None else ""
            fecha = s.find('ns:solg_fecha', ns).text if s.find('ns:solg_fecha', ns) is not None else ""
            tipo = s.find('ns:solg_tipo', ns).text if s.find('ns:solg_tipo', ns) is not None else ""
            celula_id = s.find('ns:solg_es_id', ns).text if s.find('ns:solg_es_id', ns) is not None else ""
            ref = s.find('ns:rf_referencia', ns).text if s.find('ns:rf_referencia', ns) is not None else ""
            criterio = s.find('ns:verificado', ns).text if s.find('ns:verificado', ns) is not None else ""
            herr = s.find('ns:Herr_Descripcion', ns).text if s.find('ns:Herr_Descripcion', ns) is not None else ""

            # Aplicar filtros
            if fecha_inicio and fecha < fecha_inicio:
                continue
            if fecha_fin and fecha > fecha_fin:
                continue
            if tipo_solicitud and tipo_solicitud.upper() != tipo.upper():
                continue
            if referencia and referencia.upper() != ref.upper():
                continue
            if celula and str(celula) != str(celula_id):
                continue
            if not corresponde_herramienta(herr, herramienta):
                continue

            resultados.append({
                "codigo_rack": codigo_rack,
                "criterio": criterio,
                "fecha": fecha
            })
            
        except Exception as e:
            print("Error procesando solicitud: {}".format(str(e)))
            continue

    return resultados
    
    