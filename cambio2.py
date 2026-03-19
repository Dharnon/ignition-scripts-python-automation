# ...existing code...

def completarTarea(celula, num, nombreTarea):
    # Tareas.Data.TagsMaquina.completarTarea(celula, num, nombreTarea)
    """
    Script para completar una tarea específica en el dataset de contadores

    Retorno:
    - 0: Contador se puso a cero
    - contador: Valor actual del contador (entre 1 y ocurrencia-1)
    - -1: Contador mayor que ocurrencia, completar de nuevo en siguiente ciclo
    - -2: Error
    """
    #---PARAMETROS--------------------------------------------------
    tp = constantes.tag_provider
    #---------------------------------------------------------------

    try:
        rutaTag = tp + "Datos_Celula/Celula" + str(celula) + "/Maq_" + str(num) + "/ContadorTareas"

        # --- Leer dataset actual ---
        dsOld = system.tag.readBlocking([rutaTag])[0].value
        if dsOld is None or dsOld.getRowCount() == 0:
            print("Error: No hay dataset en la ruta especificada")
            return -2

        # --- Validar columnas ---
        expectedCols = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
        colNames = list(dsOld.getColumnNames())
        for col in expectedCols:
            if col not in colNames:
                print("Error: Dataset corrupto - falta columna: " + col)
                return -2

        # --- Buscar y procesar la tarea ---
        tareaEncontrada = False
        newRows = []
        resultado = -2
        tipoMaq = Sinoptico.Data.General.obtenerTipoMaquina(celula, num)

        for i in range(dsOld.getRowCount()):
            try:
                fecha = dsOld.getValueAt(i, "fecha")
                tarea = dsOld.getValueAt(i, "tarea")
                ocurrencia = dsOld.getValueAt(i, "ocurrencia")
                contador = dsOld.getValueAt(i, "contador")
                elementos = dsOld.getValueAt(i, "elementos")

                if tarea == nombreTarea:
                    tareaEncontrada = True

                    if ocurrencia is None or ocurrencia <= 0:
                        print("Error: Ocurrencia invalida para la tarea: " + nombreTarea)
                        return -2

                    # Caso especial: CH de herramienta en TALLADORA / AFEITADORA
                    esCHHerramienta = nombreTarea.startswith("CH") and (tipoMaq == "TALLADORA" or tipoMaq == "AFEITADORA")

                    if esCHHerramienta:
                        contador = 0
                        resultado = 0
                        print("CH completada: " + nombreTarea + " - Contador reseteado a cero")
                    else:
                        contador = int(contador - ocurrencia)
                        print("Contador tras restar ocurrencia: " + str(contador))

                        if contador < 0:
                            contador = 0
                            resultado = 0
                            print("Tarea completada: " + nombreTarea + " - Contador puesto a cero")
                        elif contador < ocurrencia:
                            resultado = contador
                            print("Tarea completada: " + nombreTarea + " - Contador actual: " + str(contador))
                        else:
                            resultado = -1
                            print("Contador aun mayor que ocurrencia (" + str(contador) + " >= " + str(ocurrencia) + "). Se completara de nuevo en el siguiente ciclo.")

                newRows.append([fecha, tarea, ocurrencia, contador, elementos])

            except Exception as e:
                print("Error procesando fila " + str(i) + ": " + str(e))
                continue

        # --- Verificar si se encontró la tarea ---
        if not tareaEncontrada:
            print("Error: No se encontro la tarea especificada: " + nombreTarea)
            return -2

        if len(newRows) == 0:
            print("Error: No hay datos validos en el dataset")
            return -2

        # --- Crear dataset y escribir ---
        headers = ["fecha", "tarea", "ocurrencia", "contador", "elementos"]
        dsNew = ds.toDataSet(headers, newRows)

        try:
            writeResult = system.tag.writeBlocking([rutaTag], [dsNew])
            if writeResult and len(writeResult) > 0 and not writeResult[0].isGood():
                print("Error: No se pudo escribir el dataset actualizado")
                return -2
        except Exception as we:
            print("Error al escribir dataset: " + str(we))
            return -2

        print("Dataset actualizado correctamente. Resultado: " + str(resultado))
        return resultado

    except Exception as e:
        print("Error general en completarTarea: " + str(e))
        return -2

# ...existing code...