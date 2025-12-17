import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from fpdf import FPDF
import matplotlib.pyplot as plt

def generar_pdf_reglamento(nombre, fecha_ingreso):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REGLAMENTO DEL ALBERGUE BELÉN", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Fecha de Ingreso: {fecha_ingreso}", ln=1, align="R")
    pdf.ln(20)
    pdf.multi_cell(0, 10, txt="REGLAMENTO INTERNO\n\n1. Respeto: Tratar con dignidad a todos los presentes.\n2. Limpieza: Mantener limpias las áreas comunes.\n3. Horarios: Respetar horas de silencio y salidas.\n4. Seguridad: Cuidar sus pertenencias personales.\n5. Convivencia: Resolver conflictos pacíficamente.\n\nAl firmar hago constar que he leído y acepto estas normas.")
    pdf.ln(50)
    pdf.cell(200, 10, txt="_" * 40, ln=1, align="C")
    pdf.cell(200, 10, txt=f"Firma: {nombre}", ln=1, align="C")
    
    # Retorna bytes (cadena latin-1 en py2/fpdf antiguo, pero usaremos encode para asegurar bytes en py3)
    return pdf.output(dest="S").encode("latin-1")

# --- CONFIGURACIÓN DE "BASE DE DATOS" (EXCEL) ---
DB_FILE = 'datos_albergue.xlsx'

def cargar_datos():
    if not os.path.exists(DB_FILE):
        # Crear archivo si no existe
        with pd.ExcelWriter(DB_FILE) as writer:
            pd.DataFrame(columns=['usuario', 'pass', 'rol']).to_excel(writer, sheet_name='Usuarios', index=False)
            # COLS ACTUALIZADAS
            pd.DataFrame(columns=[
                'folio', 'nombre', 'identificacion', 'edad', 'fecha_nacimiento', 
                'nacionalidad', 'genero', 'tipo', 'tutor_folio', 'fecha_ingreso', 'num_acompanantes'
            ]).to_excel(writer, sheet_name='Personas', index=False)
            
            # SCHEMA ENCUESTAS ACTUALIZADO
            pd.DataFrame(columns=[
                'folio_persona', 'estado_civil', 'escolaridad', 'ocupacion', 
                'enfermedad_cronica', 'estado_migratorio', 'motivo_salida', 'destino', 'redes_apoyo', 'observaciones'
            ]).to_excel(writer, sheet_name='Encuestas', index=False)
    
    # Leer hojas
    xls = pd.ExcelFile(DB_FILE)
    df_personas = pd.read_excel(xls, 'Personas')
    # Podríamos leer encuestas también si fuera necesario
    return df_personas

def guardar_persona(nueva_persona):
    # Cargar excel existente, agregar fila y guardar
    df_actual = pd.read_excel(DB_FILE, sheet_name='Personas')
    df_nuevo = pd.concat([df_actual, pd.DataFrame([nueva_persona])], ignore_index=True)
    
    with pd.ExcelWriter(DB_FILE, mode='a', if_sheet_exists='replace') as writer:
        df_nuevo.to_excel(writer, sheet_name='Personas', index=False)

def guardar_encuesta(nueva_encuesta):
    # Guardar en la hoja Encuestas
    try:
        df_actual = pd.read_excel(DB_FILE, sheet_name='Encuestas')
    except:
        # Fallback si la hoja no existe
        df_actual = pd.DataFrame()
        
    # Eliminar registro previo si existe (Actualizar/Editar)
    folio = nueva_encuesta['folio_persona']
    if not df_actual.empty and 'folio_persona' in df_actual.columns:
        # Convertir a string ambos lados para asegurar match
        df_actual = df_actual[df_actual['folio_persona'].astype(str) != str(folio)]
        
    df_nuevo = pd.concat([df_actual, pd.DataFrame([nueva_encuesta])], ignore_index=True)
    
    with pd.ExcelWriter(DB_FILE, mode='a', if_sheet_exists='replace') as writer:
        df_nuevo.to_excel(writer, sheet_name='Encuestas', index=False)

# --- LÓGICA DE FOLIOS ---
def normalize_id(val):
    """Normaliza valores de ID/Folio para comparación consistente (elimina .0 de floats, strip espacios)."""
    s = str(val).strip()
    if s.endswith('.0'):
        return s[:-2]
    if s.lower() == 'nan' or s == '':
        return ''
    return s

def generar_folio(es_acompanante, folio_tutor=None):
    df = cargar_datos()
    if df.empty:
        ultimo_folio = 1000
    else:
        try:
            ultimo_folio = 1000
        except:
            ultimo_folio = 1000
    
    if not es_acompanante:
        # Generación simple: incrementamos según conteo de Titulares
        count_titulares = len(df[df['tipo'] == 'Titular']) if not df.empty else 0
        return str(1001 + count_titulares)
    else:
        # Lógica para acompañantes
        # 1. Validar que exista el Titular y recuperar límite
        folio_tutor_str = normalize_id(folio_tutor)
        
        # Filtrar Titular (asegurando string normalizado)
        if df.empty:
            raise ValueError("No hay datos en el sistema.")
            
        # Normalizamos la columna folio para buscar
        df['folio_norm'] = df['folio'].apply(normalize_id)
        titular_match = df[df['folio_norm'] == folio_tutor_str]
        
        if titular_match.empty:
            raise ValueError(f"No existe un Titular con el folio '{folio_tutor_str}'. Verifique el número.")
            
        titular = titular_match.iloc[0]
        try:
            limite_acompanantes = int(titular['num_acompanantes'])
        except:
            limite_acompanantes = 0
            
        # 2. Contar acompañantes existentes vinculados a este tutor
        # Normalizamos la columna tutor_folio
        df['tutor_folio_norm'] = df['tutor_folio'].apply(normalize_id)
        hijos_existentes = df[df['tutor_folio_norm'] == folio_tutor_str]
        cantidad_actual = len(hijos_existentes)
        
        # 3. Validar límite
        if cantidad_actual >= limite_acompanantes:
            raise ValueError(f"⚠️ El Titular {folio_tutor_str} tiene registrado un límite de {limite_acompanantes} acompañantes y ya tiene {cantidad_actual} vinculados. Consulte a un Administrador.")
            
        # 4. Generar Letra (A, B, C...)
        letra = chr(65 + cantidad_actual) # 65='A'
        return f"{folio_tutor_str}-{letra}"

# --- INTERFAZ GRAFICA (STREAMLIT) ---
st.title("Sistema de Gestión Albergue BELÉN")

# Simulación de Login (Sidebar)
rol_seleccionado = st.sidebar.selectbox("Selecciona tu Rol (Simulado)", ["Recepción", "Trabajo Social", "Enfermería", "Admin"])

if rol_seleccionado == "Recepción":
    st.header("Módulo de Ingreso")
    
    # Eliminamos st.form para permitir interactividad (cálculo de edad en tiempo real)
    # y lógica condicional visual
    st.subheader("Datos Personales")
    col1, col2 = st.columns(2)
    
    nombre = col1.text_input("Nombre Completo")
    identificacion = col2.text_input("Identificación / No. de Documento")
    
    # Ajuste de calendario: min_value desde 1900
    # Usuario solicitó regresar al formato calendario
    fecha_nac = col1.date_input(
        "Fecha de Nacimiento", 
        min_value=datetime(1900, 1, 1),
        max_value=datetime.now(),
        value=datetime(2000, 1, 1) # Default visual
    )
    
    nacionalidad = col2.text_input("Nacionalidad")
    
    # Género texto abierto para ser incluyentes
    genero = col1.text_input("Género (Especifique)")
    
    # Calcular edad automáticamente
    edad = 0
    if fecha_nac:
        edad = (datetime.now().date() - fecha_nac).days // 365
        col2.success(f"Edad calculada: {edad} años")
    
    st.subheader("Datos de Registro y Acompañamiento")
    
    # Lógica Reestructurada
    es_menor = (fecha_nac is not None and edad < 18)
    
    # Variables de estado para el formulario
    tipo_registro = "Titular" # Default
    folio_tutor_input = ""
    num_acompanantes = 0
    es_familiar_bool = False
    
    if es_menor:
        st.info(f"ℹ️ Al ser menor de edad ({edad} años), se registra automáticamente como Acompañante vinculado a un Titular.")
        tipo_registro = "Acompañante"
        es_familiar_bool = True
        folio_tutor_input = st.text_input("Ingrese Folio del Titular / Tutor (Obligatorio)", help="El folio de la persona adulta responsable.")
    else:
        # Es adulto (o no se ha puesto fecha aun)
        modo_ingreso = st.radio("Tipo de Registro:", ["Titular (Viene solo o es cabeza de familia)", "Acompañante (Es cónyuge/familiar de otro titular)"])
        
        if modo_ingreso.startswith("Titular"):
            tipo_registro = "Titular"
            es_familiar_bool = False
            if st.checkbox("¿Viene con personas a su cargo (familia, hijos, otros)?"):
                num_acompanantes = st.number_input("Número de acompañantes", min_value=1, step=1, value=1)
        else:
            tipo_registro = "Acompañante"
            es_familiar_bool = True
            folio_tutor_input = st.text_input("Ingrese Folio del Titular Responsable")

    submitted = st.button("Registrar Ingreso")
    
    if submitted:
        # Validaciones
        errores = []
        if not nombre:
            errores.append("El nombre es obligatorio.")
        
        if tipo_registro == "Acompañante" and not folio_tutor_input:
            errores.append("El Folio del Titular es obligatorio para acompañantes (y menores).")
            
        if errores:
            for e in errores:
                st.error(e)
        else:
            # Todo OK, procesar registro
            try:
                nuevo_folio = generar_folio(es_familiar_bool, folio_tutor_input if es_familiar_bool else None)
                
                # Guardar en Excel
                datos = {
                    'folio': nuevo_folio,
                    'nombre': nombre,
                    'identificacion': identificacion,
                    'edad': edad,
                    'fecha_nacimiento': fecha_nac.strftime("%Y-%m-%d") if fecha_nac else "",
                    'nacionalidad': nacionalidad,
                    'genero': genero,
                    'tipo': tipo_registro,
                    'tutor_folio': folio_tutor_input if es_familiar_bool else '',
                    'fecha_ingreso': datetime.now().strftime("%Y-%m-%d"),
                    'num_acompanantes': num_acompanantes
                }
                guardar_persona(datos)
                st.success(f"Registrado con éxito. Folio Asignado: {nuevo_folio}")
            except ValueError as e:
                st.error(str(e))

elif rol_seleccionado == "Trabajo Social":
    st.header("Entrevista Social")
    df = cargar_datos()
    
    if df.empty:
        st.info("No hay personas registradas.")
    else:
        # Buscador de personas
        folio_buscar = st.selectbox("Seleccione Migrante", df['folio'].tolist())
        
        # Cargar datos de encuestas para verificar existencia
        try:
            df_encuestas = pd.read_excel(DB_FILE, sheet_name='Encuestas')
        except:
            df_encuestas = pd.DataFrame()
            
        datos_previos = None
        if not df_encuestas.empty and 'folio_persona' in df_encuestas.columns:
             match = df_encuestas[df_encuestas['folio_persona'].astype(str) == str(folio_buscar)]
             if not match.empty:
                 datos_previos = match.iloc[0]

        # Mostrar datos traídos de recepción (Solo lectura)
        if folio_buscar:
            persona = df[df['folio'] == folio_buscar].iloc[0]
            st.markdown(f"""
            ### Datos del Paciente
            - **Nombre:** {persona['nombre']}
            - **Edad:** {persona['edad']} años
            - **Nacionalidad:** {persona['nacionalidad']}
            - **Género:** {persona.get('genero', 'N/A')}
            - **ID:** {persona.get('identificacion', 'N/A')}
            """)
            
            st.markdown("---")
            st.subheader("Cuestionario Social")
            
            # Listas de opciones
            opts_civil = ["Soltero/a", "Casado/a", "Unión Libre", "Divorciado/a", "Viudo/a"]
            opts_escolaridad = ["Ninguna", "Primaria", "Secundaria", "Preparatoria/Bachillerato", "Universidad", "Posgrado"]
            opts_migratorio = ["Irregular", "Solicitante", "TURH", "En Tránsito", "Retorno voluntario", "Refugiado"]
            
            # Defaults
            def_civil = 0
            def_escolaridad = 0
            def_ocupacion = ""
            def_enfermedad = ""
            def_migratorio = 0
            def_motivo = ""
            def_destino = ""
            
            # Pre-llenado si existe
            if datos_previos is not None:
                st.info("📝 Editando información existente.")
                try: def_civil = opts_civil.index(datos_previos['estado_civil'])
                except: pass
                
                try: def_escolaridad = opts_escolaridad.index(datos_previos['escolaridad'])
                except: pass
                
                def_ocupacion = datos_previos.get('ocupacion', "")
                def_enfermedad = datos_previos.get('enfermedad_cronica', "")
                
                try: def_migratorio = opts_migratorio.index(datos_previos['estado_migratorio'])
                except: pass
                
                def_motivo = datos_previos.get('motivo_salida', "")
                def_destino = datos_previos.get('destino', "")
            
            with st.form("form_social"):
                c1, c2 = st.columns(2)
                estado_civil = c1.selectbox("Estado Civil", opts_civil, index=def_civil)
                escolaridad = c2.selectbox("Escolaridad", opts_escolaridad, index=def_escolaridad)
                
                ocupacion = c1.text_input("Ocupación", value=def_ocupacion)
                enfermedad = c2.text_input("Enfermedad Crónica (Especifique / 'Ninguna')", value=def_enfermedad)
                
                estado_migratorio = c1.selectbox("Estado Migratorio", opts_migratorio, index=def_migratorio)
                
                motivo = st.text_area("Motivo de salida de origen", value=def_motivo)
                destino = st.text_input("Destino Final", value=def_destino)
                
                lbl_btn = "Editar e Imprimir Reglamento" if datos_previos is not None else "Guardar Entrevista y Generar Reglamento"
                guardar_btn = st.form_submit_button(lbl_btn)
                
                if guardar_btn:
                    # Guardar en Excel
                    datos_encuesta = {
                        'folio_persona': folio_buscar,
                        'estado_civil': estado_civil,
                        'escolaridad': escolaridad,
                        'ocupacion': ocupacion,
                        'enfermedad_cronica': enfermedad,
                        'estado_migratorio': estado_migratorio,
                        'motivo_salida': motivo,
                        'destino': destino,
                        'redes_apoyo': 'N/A', 
                        'observaciones': 'N/A'
                    }
                    guardar_encuesta(datos_encuesta)
                    
                    # Generar PDF
                    pdf_bytes = generar_pdf_reglamento(persona['nombre'], persona.get('fecha_ingreso', datetime.now().strftime("%Y-%m-%d")))
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<a href="data:application/pdf;base64,{b64_pdf}" download="Reglamento_{folio_buscar}.pdf" target="_blank" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">📄 Abrir/Descargar Reglamento PDF</a>'
                    
                    st.success("Datos guardados correctamente.")
                    st.markdown(pdf_display, unsafe_allow_html=True)


elif rol_seleccionado == "Admin":
    st.header("Dashboard General")
    df = cargar_datos()
    
    st.write("### Base de datos actual (Vista Excel)")
    st.dataframe(df)
    
    st.write("### Estadísticas Rápidas")
    
    # Limpieza ligera para gráficos
    if not df.empty:
        # Cargar datos de encuestas para Estado Civil
        try:
            df_encuestas = pd.read_excel(DB_FILE, sheet_name='Encuestas')
        except:
            df_encuestas = pd.DataFrame()
            
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Nacionalidad**")
            st.bar_chart(df['nacionalidad'].value_counts())
            
        with c2:
            st.write("**Distribución por Estado Civil**")
            if not df_encuestas.empty and 'estado_civil' in df_encuestas.columns:
                fig_pie, ax_pie = plt.subplots(figsize=(6, 3))
                # Limpiar nulos
                datos_civil = df_encuestas['estado_civil'].fillna('Sin Registro').value_counts()
                ax_pie.pie(datos_civil, labels=datos_civil.index, autopct='%1.1f%%', startangle=90)
                ax_pie.axis('equal') 
                st.pyplot(fig_pie)
            else:
                st.info("No hay datos de encuestas suficientes.")

        # Gráficas de Tiempo
        if 'fecha_ingreso' in df.columns:
            st.markdown("---")
            st.write("### Evolución de Registros")
            
            # Convertir a datetime para agrupar
            df['fecha_dt'] = pd.to_datetime(df['fecha_ingreso'], errors='coerce')
            
            t1, t2 = st.columns(2)
            
            with t1:
                st.write("**Registros Diarios**")
                # Agrupar por fecha (día)
                counts_dia = df['fecha_dt'].dt.date.value_counts().sort_index()
                st.line_chart(counts_dia)
                
            with t2:
                st.write("**Registros Mensuales**")
                # Agrupar por mes (Año-Mes)
                counts_mes = df['fecha_dt'].dt.strftime('%Y-%m').value_counts().sort_index()
                st.line_chart(counts_mes)