#---GENERAL-------------------------------------
LINEA = "G_PILOT" # Esto se usa para el inicio del nombre de las tablas que hemos creado "G_PILOT_TAREAS" por ejemplo
#DATABASE = "JD_Servidor_DEMO"
DATABASE = "GPILOT2"

#---BASE DE DATOS-------------------------------
#Database_Admin_Usuarios = "JD_Servidor_DEMO" # Donde creamos la tabla de gestion de usuarios, TUsuarios y TRoles
Database_Admin_Usuarios = "GPILOT2"
Database_Inicio = "GPILOT2"
Database_Sinoptico = "GPILOT2"
#Database_Tareas = "JD_Servidor_DEMO" # Donde creamos la tabla que proviene de excel
Database_Tareas = "GPILOT2"
Database_Tareas_2 = "GPILOT2"

#---TAGS----------------------------------------
tag_provider = "[G-PILOT_TAGS]"

#---PROYECTO------------------------------------
celulaLinea = "142"
celulas = ["142A", "142B", "142C", "142D"]
pages = 4
idCelulas = ["43","42","54","4"] # Id de la celula segun la base de datos general de John Deere !!! La celula 142A es 42 y la 142B es 43!!!!
pathExcel = "C:\Users\s4e2ihx\OneDrive-Deere&Co\OneDrive - Deere & Co\Escritorio\Tareas 4Comb"  # ruta = "\R120638-R120636-R120631-R120631.xlsx"

#---TAREAS--------------------------------------
tipoTareas = ["Verificación", "Descarga", "CH", "Cambio de carga", "Limpieza", "Grafico"]
prefijo = "OP10" # El prefijo para el CH del Torno, por ejemplo