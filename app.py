import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from fpdf import FPDF
import matplotlib.pyplot as plt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- CONFIGURACIÓN DE CORREO (SECRETS) ---
try:
    SMTP_USER = st.secrets["SMTP_USER"]
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except:
    SMTP_USER = ""
    SMTP_PASSWORD = ""

def generar_pdf_reporte(df_diario, df_mensual):
    """
    Genera un PDF con las tablas de movimientos diarios y mensuales.
    Recibe DataFrames de Pandas (tablas).
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Reporte de Movimientos - Albergue Belén", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='R')
    pdf.ln(10)
    
    # --- TABLA DIARIA ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Movimientos Diarios (Altas y Bajas)", ln=True)
    pdf.set_font("Courier", size=10)
    
    # Encabezado Manual para tabla simple
    pdf.cell(60, 8, "Fecha", border=1)
    pdf.cell(40, 8, "Altas", border=1)
    pdf.cell(40, 8, "Bajas", border=1)
    pdf.ln()
    
    pdf.set_font("Courier", size=10)
    # df_diario index es la fecha, columnas son Altas, Bajas
    if not df_diario.empty:
        for fecha, row in df_diario.iterrows():
            # Convertir fecha a string si es necesario
            fecha_str = str(fecha)
            pdf.cell(60, 8, fecha_str[:12], border=1)
            pdf.cell(40, 8, str(int(row.get('Altas', 0))), border=1)
            pdf.cell(40, 8, str(int(row.get('Bajas', 0))), border=1)
            pdf.ln()
    else:
        pdf.cell(0, 8, "No hay movimientos registrados.", border=1)
    
    pdf.ln(10)
    
    # --- TABLA MENSUAL ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Movimientos Mensuales", ln=True)
    
    pdf.set_font("Courier", 'B', 10)
    pdf.cell(60, 8, "Mes", border=1)
    pdf.cell(40, 8, "Altas", border=1)
    pdf.cell(40, 8, "Bajas", border=1)
    pdf.ln()

    pdf.set_font("Courier", size=10)
    if not df_mensual.empty:
        for mes, row in df_mensual.iterrows():
            mes_str = str(mes)
            pdf.cell(60, 8, mes_str, border=1)
            pdf.cell(40, 8, str(int(row.get('Altas', 0))), border=1)
            pdf.cell(40, 8, str(int(row.get('Bajas', 0))), border=1)
            pdf.ln()
    else:
         pdf.cell(0, 8, "No hay movimientos mensuales.", border=1)
            
    return pdf.output(dest="S").encode("latin-1")

def enviar_correo(destinatarios, asunto, cuerpo, archivo_bytes, nombre_archivo, remitente, password):
    msg = MIMEMultipart()
    msg['From'] = remitente
    
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = asunto
    
    msg.attach(MIMEText(cuerpo, 'plain'))
    
    part = MIMEApplication(archivo_bytes, Name=nombre_archivo)
    part['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    msg.attach(part)
    
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        # Sendmail accepts a list for recipients
        server.sendmail(remitente, destinatarios, msg.as_string())
        server.quit()
        return True, "Correo enviado exitosamente."
    except Exception as e:
        return False, str(e)


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
                'nacionalidad', 'genero', 'tipo', 'tutor_folio', 'fecha_ingreso', 'num_acompanantes',
                'fecha_salida', 'motivo_salida'
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

def actualizar_persona(datos_actualizados):
    """Actualiza los datos de una persona existente basado en su folio."""
    try:
        df = pd.read_excel(DB_FILE, sheet_name='Personas')
        folio_str = str(datos_actualizados['folio']).strip()
        
        # Crear columna temporal para match exacto
        df['folio_str'] = df['folio'].astype(str).str.strip()
        
        # Buscar índice
        matches = df.index[df['folio_str'] == folio_str].tolist()
        
        if matches:
            idx = matches[0]
            # Actualizar campos
            for k, v in datos_actualizados.items():
                if k in df.columns:
                    df.at[idx, k] = v
            
            # Guardar (sin la columna temporal)
            df_final = df.drop(columns=['folio_str'])
            with pd.ExcelWriter(DB_FILE, mode='a', if_sheet_exists='replace') as writer:
                df_final.to_excel(writer, sheet_name='Personas', index=False)
            return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

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
    st.header("Módulo de Recepción")
    
    # Navegación por pestañas
    tab_ingreso, tab_salida = st.tabs(["Registro de Ingresos", "Registro de Bajas"])
    
    # --- PESTAÑA 1: ENTRADAS (Lógica Existente) ---
    with tab_ingreso:
        st.subheader("Nuevo Ingreso")
        # Eliminamos st.form para permitir interactividad (cálculo de edad en tiempo real)
        col1, col2 = st.columns(2)
        
        nombre = col1.text_input("Nombre Completo")
        identificacion = col2.text_input("Identificación / No. de Documento")
        
        fecha_nac = col1.date_input(
            "Fecha de Nacimiento", 
            min_value=datetime(1900, 1, 1),
            max_value=datetime.now(),
            value=datetime(2000, 1, 1) # Default visual
        )
        
        nacionalidad = col2.text_input("Nacionalidad")
        genero = col1.text_input("Género (Especifique)")
        
        # Calcular edad automáticamente
        edad = 0
        if fecha_nac:
            edad = (datetime.now().date() - fecha_nac).days // 365
            col2.success(f"Edad calculada: {edad} años")
        
        st.subheader("Datos de Registro y Acompañamiento")
        
        es_menor = (fecha_nac is not None and edad < 18)
        
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
            errores = []
            if not nombre:
                errores.append("El nombre es obligatorio.")
            
            if tipo_registro == "Acompañante" and not folio_tutor_input:
                errores.append("El Folio del Titular es obligatorio para acompañantes (y menores).")
                
            if errores:
                for e in errores:
                    st.error(e)
            else:
                try:
                    nuevo_folio = generar_folio(es_familiar_bool, folio_tutor_input if es_familiar_bool else None)
                    
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
                        'fecha_ingreso': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'num_acompanantes': num_acompanantes,
                        'fecha_salida': '',  # Nuevo campo vacío
                        'motivo_salida': ''  # Nuevo campo vacío
                    }
                    guardar_persona(datos)
                    st.success(f"Registrado con éxito. Folio Asignado: {nuevo_folio}")
                except ValueError as e:
                    st.error(str(e))

    # --- PESTAÑA 2: SALIDAS (Nueva Funcionalidad) ---
    with tab_salida:
        st.subheader("Procesar Baja")
        df_salida = cargar_datos()
        
        # Filtrar solo personas activas (fecha_salida es NaN o vacío)
        if not df_salida.empty:
            # Asegurar que existe columna fecha_salida (por si es archivo viejo)
            if 'fecha_salida' not in df_salida.columns:
                df_salida['fecha_salida'] = ''
            
            # Filtro: Aquellos que NO tienen fecha de salida (vacío o NaN)
            activos = df_salida[df_salida['fecha_salida'].isna() | (df_salida['fecha_salida'] == '')]
            
            if activos.empty:
                st.info("No hay personas activas en el albergue actualmente.")
            else:
                # Buscador: Folio - Nombre
                opciones = activos.apply(lambda x: f"{x['folio']} - {x['nombre']}", axis=1).tolist()
                seleccion = st.selectbox("Buscar persona por Folio o Nombre", opciones)
                
                if seleccion:
                    # Extraer folio
                    folio_sel = seleccion.split(" - ")[0]
                    # Convertir a string para evitar IndexError por mismatch de tipos
                    persona_sel = activos[activos['folio'].astype(str) == folio_sel].iloc[0]
                    
                    st.markdown("### Datos de la Persona")
                    st.markdown(f"""
                    - **Nombre:** {persona_sel['nombre']}
                    - **Folio:** {persona_sel['folio']}
                    - **Fecha Ingreso:** {persona_sel.get('fecha_ingreso', 'N/A')}
                    - **Número de Acompañantes:** {persona_sel.get('num_acompanantes', 0)}
                    """)
                    
                    tipo_persona = persona_sel.get('tipo', 'Titular')
                    lista_baja = [folio_sel] # Lista de folios a dar de baja
                    mensaje_alerta = ""
                    
                    # Lógica Familiar: Si es Titular, buscar acompañantes activos
                    if tipo_persona == 'Titular':
                        # Normalizar para buscar hijos
                        folio_norm = normalize_id(folio_sel)
                        activos['tutor_norm'] = activos['tutor_folio'].apply(normalize_id)
                        acompanantes = activos[activos['tutor_norm'] == folio_norm]
                        
                        if not acompanantes.empty:
                            nombres_acomp = acompanantes['nombre'].tolist()
                            folios_acomp = acompanantes['folio'].tolist()
                            lista_baja.extend(folios_acomp)
                            
                            st.warning(f"⚠️ **ATENCIÓN:** Al dar de baja a este Titular, también se dará de baja a sus {len(nombres_acomp)} acompañantes:")
                            st.write(f"**Acompañantes:** {', '.join(nombres_acomp)}")
                            mensaje_alerta = f"Se dará de baja al grupo familiar completo ({len(lista_baja)} personas)."
                    
                    motivo_baja = st.text_area("Motivo de Salida (Obligatorio)")
                    
                    if st.button("Confirmar Baja / Salida", disabled=(not motivo_baja), type="primary"):
                        # Procesar Baja
                        try:
                            df_update = pd.read_excel(DB_FILE, sheet_name='Personas')
                            # Asegurar columnas
                            if 'fecha_salida' not in df_update.columns: df_update['fecha_salida'] = ''
                            if 'motivo_salida' not in df_update.columns: df_update['motivo_salida'] = ''
                            
                            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Actualizar registros
                            # Convertimos a string para asegurar match
                            df_update['folio_str'] = df_update['folio'].astype(str)
                            lista_baja_str = [str(x) for x in lista_baja]
                            
                            mask = df_update['folio_str'].isin(lista_baja_str)
                            df_update.loc[mask, 'fecha_salida'] = ahora
                            df_update.loc[mask, 'motivo_salida'] = motivo_baja
                            
                            # Guardar
                            df_update = df_update.drop(columns=['folio_str'])
                            with pd.ExcelWriter(DB_FILE, mode='a', if_sheet_exists='replace') as writer:
                                df_update.to_excel(writer, sheet_name='Personas', index=False)
                                
                            st.success(f"✅ Salida registrada exitosamente. {mensaje_alerta}")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error al procesar la salida: {e}")

elif rol_seleccionado == "Trabajo Social":
    st.header("Entrevista Social")
    df = cargar_datos()
    
    # Filtrar solo activos para entrevista
    if 'fecha_salida' not in df.columns: df['fecha_salida'] = ''
    df_activos = df[df['fecha_salida'].isna() | (df['fecha_salida'] == '')]
    
    if df_activos.empty:
        st.info("No hay personas activas registradas para realizar entrevista.")
        folio_buscar = None
    else:
        # Buscador de personas (Solo Activos)
        folio_buscar = st.selectbox("Seleccione persona (Solo Activos)", df_activos['folio'].tolist())
        
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
            
            # Key para el estado de edición de este folio
            key_edit = f"edit_mode_{folio_buscar}"
            if key_edit not in st.session_state:
                st.session_state[key_edit] = False
            
            is_editing = st.session_state[key_edit]
            disabled_inputs = not is_editing
            
            st.subheader("Datos de la persona")
            
            # Usaremos contenedores o columnas para layout homogéneo
            c1, c2 = st.columns(2)
            
            # --- CAMPOS UNIFICADOS (Lectura/Edición controlados por 'disabled_inputs') ---
            # 1. Nombre
            val_nombre = c1.text_input("Nombre Completo", value=persona['nombre'], disabled=disabled_inputs, key=f"p_nom_{folio_buscar}")
            
            # 2. Edad
            val_edad_int = int(persona['edad']) if pd.notnull(persona['edad']) else 0
            val_edad = c2.number_input("Edad", value=val_edad_int, step=1, disabled=disabled_inputs, key=f"p_edad_{folio_buscar}")
            
            # 3. Nacionalidad
            val_nac = c1.text_input("Nacionalidad", value=persona['nacionalidad'], disabled=disabled_inputs, key=f"p_nac_{folio_buscar}")
            
            # 4. Género
            val_gen = c2.text_input("Género", value=persona.get('genero', ''), disabled=disabled_inputs, key=f"p_gen_{folio_buscar}")
            
            # 5. ID
            val_id = c1.text_input("Identificación / ID", value=persona.get('identificacion', ''), disabled=disabled_inputs, key=f"p_id_{folio_buscar}")
            
            # 6. Lógica condicional (Acompañantes / Tutor)
            tipo_p = persona.get('tipo', 'Titular')
            val_acompanantes = persona.get('num_acompanantes', 0)
            
            if tipo_p == 'Titular':
                # Titular: Campo numérico editable (si está en modo edición)
                val_acompanantes = c2.number_input("Número de Acompañantes", value=int(val_acompanantes) if pd.notnull(val_acompanantes) else 0, step=1, disabled=disabled_inputs, key=f"p_anum_{folio_buscar}")
            else:
                # Acompañante: Muestra folio tutor (Siempre deshabilitado para edición manual directa, es referencial)
                tutor_folio = persona.get('tutor_folio', 'N/A')
                tutor_clean = normalize_id(tutor_folio)
                c2.text_input("Folio del Titular/Tutor", value=tutor_clean, disabled=True, key=f"p_tut_{folio_buscar}")
                
                # Info extra visual
                df['folio_norm_temp'] = df['folio'].apply(normalize_id)
                tutor_row = df[df['folio_norm_temp'] == tutor_clean]
                if not tutor_row.empty:
                     lim = tutor_row.iloc[0].get('num_acompanantes', 0)
                     st.caption(f"ℹ️ Titular autoriza hasta {lim} acompañantes.")

            # --- BOTONES DE ACCIÓN ---
            st.write("") # Espaciador
            
            if not is_editing:
                if st.button("✏️ Editar", key=f"btn_edit_{folio_buscar}"):
                    st.session_state[key_edit] = True
                    st.rerun()
            else:
                # Detectar cambios para habilitar/deshabilitar botón Actualizar
                cambio_nombre = val_nombre != persona['nombre']
                cambio_edad = val_edad != val_edad_int
                cambio_nac = val_nac != persona['nacionalidad']
                cambio_gen = val_gen != persona.get('genero', '')
                cambio_id = str(val_id) != str(persona.get('identificacion', ''))
                
                cambio_num_acomp = False
                if tipo_p == 'Titular':
                    old_num = int(persona.get('num_acompanantes', 0)) if pd.notnull(persona.get('num_acompanantes', 0)) else 0
                    cambio_num_acomp = val_acompanantes != old_num
                
                hay_cambios = any([cambio_nombre, cambio_edad, cambio_nac, cambio_gen, cambio_id, cambio_num_acomp])
                
                col_b1, col_b2 = st.columns([1, 1])
                with col_b1:
                    if st.button("❌ Cancelar", key=f"btn_cancel_{folio_buscar}"):
                        st.session_state[key_edit] = False
                        st.rerun()
                with col_b2:
                    # Botón Actualizar
                    if st.button("💾 Actualizar y Guardar", disabled=not hay_cambios, key=f"btn_save_{folio_buscar}"):
                         datos_update = {
                            'folio': folio_buscar,
                            'nombre': val_nombre,
                            'edad': val_edad,
                            'nacionalidad': val_nac,
                            'genero': val_gen,
                            'identificacion': val_id
                        }
                         if tipo_p == 'Titular':
                             datos_update['num_acompanantes'] = val_acompanantes
                             
                         if actualizar_persona(datos_update):
                             st.success("Actualizado correctamente.")
                             st.session_state[key_edit] = False
                             st.rerun()
                         else:
                             st.error("No se pudo actualizar.")
            
            st.markdown("---")
            st.subheader("Cuestionario Social")
            
            # Key para estado de edición de la entrevista
            key_social = f"social_edit_{folio_buscar}"
            existe_encuesta = datos_previos is not None
            
            # Si no está en sesión, inicializar
            if key_social not in st.session_state:
                # Si existe encuesta -> Modo Lectura (False)
                # Si NO existe -> Modo Edición (True) para llenar por primera vez
                st.session_state[key_social] = not existe_encuesta
                
            is_social_editing = st.session_state[key_social]
            disabled_social = not is_social_editing
            
            # --- WIDGETS HOMOGÉNEOS ---
            # Listas de opciones
            opts_civil = ["Soltero/a", "Casado/a", "Unión Libre", "Divorciado/a", "Viudo/a"]
            opts_escolaridad = ["Ninguna", "Primaria", "Secundaria", "Preparatoria/Bachillerato", "Universidad", "Posgrado"]
            opts_migratorio = ["Irregular", "Solicitante", "TURH", "En Tránsito", "Retorno voluntario", "Refugiado"]
            
            # Valores por defecto para widgets (tomados de datos_previos si existen, o default)
            val_civil_idx = 0
            val_escolaridad_idx = 0
            val_ocupacion = ""
            val_enfermedad = ""
            val_migratorio_idx = 0
            val_motivo = ""
            val_destino = ""
            
            if datos_previos is not None:
                try: val_civil_idx = opts_civil.index(datos_previos.get('estado_civil', opts_civil[0]))
                except: pass
                try: val_escolaridad_idx = opts_escolaridad.index(datos_previos.get('escolaridad', opts_escolaridad[0]))
                except: pass
                val_ocupacion = datos_previos.get('ocupacion', "")
                val_enfermedad = datos_previos.get('enfermedad_cronica', "")
                try: val_migratorio_idx = opts_migratorio.index(datos_previos.get('estado_migratorio', opts_migratorio[0]))
                except: pass
                val_motivo = datos_previos.get('motivo_salida', "")
                val_destino = datos_previos.get('destino', "")
            
            # Layout de Inputs
            sc1, sc2 = st.columns(2)
            
            # Usar keys únicos para evitar conflictos
            inp_civil = sc1.selectbox("Estado Civil", opts_civil, index=val_civil_idx, disabled=disabled_social, key=f"s_civ_{folio_buscar}")
            inp_escolaridad = sc2.selectbox("Escolaridad", opts_escolaridad, index=val_escolaridad_idx, disabled=disabled_social, key=f"s_esc_{folio_buscar}")
            
            inp_ocupacion = sc1.text_input("Ocupación", value=val_ocupacion, disabled=disabled_social, key=f"s_ocu_{folio_buscar}")
            inp_enfermedad = sc2.text_input("Enfermedad Crónica", value=val_enfermedad, help="Especifique o escriba 'Ninguna'", disabled=disabled_social, key=f"s_enf_{folio_buscar}")
            
            inp_migratorio = sc1.selectbox("Estado Migratorio", opts_migratorio, index=val_migratorio_idx, disabled=disabled_social, key=f"s_mig_{folio_buscar}")
            
            inp_motivo = st.text_area("Motivo de salida de origen", value=val_motivo, disabled=disabled_social, key=f"s_mot_{folio_buscar}")
            inp_destino = st.text_input("Destino Final", value=val_destino, disabled=disabled_social, key=f"s_des_{folio_buscar}")
            
            st.write("") # Espaciador
            
            # --- LÓGICA DE BOTONES ---
            if not is_social_editing:
                # MODO LECTURA
                
                # 1. Botón Editar
                if st.button("✏️ Editar Entrevista", key=f"btn_s_edit_{folio_buscar}"):
                    st.session_state[key_social] = True
                    st.rerun()
                
                # 2. Botón PDF (SOLO SI ES MENOR DE 18, como solicitado)
                # Validar edad desde el registro de persona
                edad_val = 0
                try:
                    edad_val = int(persona.get('edad', 0))
                except:
                    pass
                    
                if edad_val >= 18:
                    if st.button("📄 Generar/Ver Reglamento", key=f"btn_pdf_{folio_buscar}"):
                         # Generación "al vuelo"
                         nombre_p = persona.get('nombre', 'Desconocido')
                         fecha_i = persona.get('fecha_ingreso', datetime.now().strftime("%Y-%m-%d"))
                         pdf_bytes = generar_pdf_reglamento(nombre_p, fecha_i)
                         b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                         pdf_link = f'<a href="data:application/pdf;base64,{b64_pdf}" download="Reglamento_{folio_buscar}.pdf" target="_blank">📥 Descargar PDF Generado</a>'
                         st.markdown(pdf_link, unsafe_allow_html=True)
            
            else:
                # MODO EDICIÓN / CRACIÓN
                col_sa, col_sb = st.columns([1, 1])
                
                with col_sa:
                    # Mostrar cancelar solo si ya existía datos previos (si es nuevo registro, cancelar quizás no tenga sentido o podría limpiar)
                    if existe_encuesta:
                        if st.button("❌ Cancelar", key=f"btn_s_cancel_{folio_buscar}"):
                            st.session_state[key_social] = False
                            st.rerun()
                            
                with col_sb:
                    label_save = "💾 Guardar Entrevista" if existe_encuesta else "💾 Registrar Entrevista"
                    if st.button(label_save, key=f"btn_s_save_{folio_buscar}"):
                        datos_encuesta = {
                            'folio_persona': folio_buscar,
                            'estado_civil': inp_civil,
                            'escolaridad': inp_escolaridad,
                            'ocupacion': inp_ocupacion,
                            'enfermedad_cronica': inp_enfermedad,
                            'estado_migratorio': inp_migratorio,
                            'motivo_salida': inp_motivo,
                            'destino': inp_destino,
                            'redes_apoyo': 'N/A', 
                            'observaciones': 'N/A'
                        }
                        guardar_encuesta(datos_encuesta)
                        st.success("Entrevista guardada exitosamente.")
                        
                        # Cambiar a modo lectura
                        st.session_state[key_social] = False
                        st.rerun()


elif rol_seleccionado == "Enfermería":
    st.header("Módulo de Enfermería")
    df = cargar_datos()
    
    # Filtrar solo activos para atención
    if 'fecha_salida' not in df.columns: df['fecha_salida'] = ''
    df_activos = df[df['fecha_salida'].isna() | (df['fecha_salida'] == '')]
    
    if df_activos.empty:
        st.info("No hay personas activas registradas para atención médica.")
        folio_buscar = None
    else:
        # Buscador de personas (Solo Activos)
        folio_buscar = st.selectbox("Seleccione paciente (Solo Activos)", df_activos['folio'].tolist(), key="enf_k_selector")
        
        # Mostrar datos de la persona
        if folio_buscar:
            persona = df[df['folio'] == folio_buscar].iloc[0]
            
            # Key único para edición en enfermería
            key_edit = f"enf_edit_mode_{folio_buscar}"
            if key_edit not in st.session_state:
                st.session_state[key_edit] = False
            
            is_editing = st.session_state[key_edit]
            disabled_inputs = not is_editing
            
            st.subheader("Datos del Paciente")
            
            c1, c2 = st.columns(2)
            
            # --- CAMPOS (Replicados de Trabajo Social) ---
            val_nombre = c1.text_input("Nombre Completo", value=persona['nombre'], disabled=disabled_inputs, key=f"enf_p_nom_{folio_buscar}")
            
            val_edad_int = int(persona['edad']) if pd.notnull(persona['edad']) else 0
            val_edad = c2.number_input("Edad", value=val_edad_int, step=1, disabled=disabled_inputs, key=f"enf_p_edad_{folio_buscar}")
            
            val_nac = c1.text_input("Nacionalidad", value=persona['nacionalidad'], disabled=disabled_inputs, key=f"enf_p_nac_{folio_buscar}")
            val_gen = c2.text_input("Género", value=persona.get('genero', ''), disabled=disabled_inputs, key=f"enf_p_gen_{folio_buscar}")
            val_id = c1.text_input("Identificación / ID", value=persona.get('identificacion', ''), disabled=disabled_inputs, key=f"enf_p_id_{folio_buscar}")
            
            # Acompañantes / Tutor Logic
            tipo_p = persona.get('tipo', 'Titular')
            val_acompanantes = persona.get('num_acompanantes', 0)
            
            if tipo_p == 'Titular':
                val_acompanantes = c2.number_input("Número de Acompañantes", value=int(val_acompanantes) if pd.notnull(val_acompanantes) else 0, step=1, disabled=disabled_inputs, key=f"enf_p_anum_{folio_buscar}")
            else:
                tutor_folio = persona.get('tutor_folio', 'N/A')
                tutor_clean = normalize_id(tutor_folio)
                c2.text_input("Folio del Titular/Tutor", value=tutor_clean, disabled=True, key=f"enf_p_tut_{folio_buscar}")
            
            # --- BOTONES DE ACCIÓN ---
            st.write("") 
            
            if not is_editing:
                if st.button("✏️ Editar Datos Personales", key=f"enf_btn_edit_{folio_buscar}"):
                    st.session_state[key_edit] = True
                    st.rerun()
            else:
                # Detectar cambios
                cambio_nombre = val_nombre != persona['nombre']
                cambio_edad = val_edad != val_edad_int
                cambio_nac = val_nac != persona['nacionalidad']
                cambio_gen = val_gen != persona.get('genero', '')
                cambio_id = str(val_id) != str(persona.get('identificacion', ''))
                
                cambio_num_acomp = False
                if tipo_p == 'Titular':
                    old_num = int(persona.get('num_acompanantes', 0)) if pd.notnull(persona.get('num_acompanantes', 0)) else 0
                    cambio_num_acomp = val_acompanantes != old_num
                
                hay_cambios = any([cambio_nombre, cambio_edad, cambio_nac, cambio_gen, cambio_id, cambio_num_acomp])
                
                col_b1, col_b2 = st.columns([1, 1])
                with col_b1:
                    if st.button("❌ Cancelar", key=f"enf_btn_cancel_{folio_buscar}"):
                        st.session_state[key_edit] = False
                        st.rerun()
                with col_b2:
                    if st.button("💾 Actualizar y Guardar", disabled=not hay_cambios, key=f"enf_btn_save_{folio_buscar}"):
                         datos_update = {
                            'folio': folio_buscar,
                            'nombre': val_nombre,
                            'edad': val_edad,
                            'nacionalidad': val_nac,
                            'genero': val_gen,
                            'identificacion': val_id
                        }
                         if tipo_p == 'Titular':
                             datos_update['num_acompanantes'] = val_acompanantes
                             
                         if actualizar_persona(datos_update):
                             st.success("Actualizado correctamente.")
                             st.session_state[key_edit] = False
                             st.rerun()
                         else:
                             st.error("No se pudo actualizar.")
            
            st.markdown("---")
            st.info("Módulo de Enfermería en construcción.")

elif rol_seleccionado == "Admin":
    st.header("Dashboard General")
    df = cargar_datos()
    
    st.write("### Base de datos actual (Vista Excel)")
    st.dataframe(df)
    
    st.write("### Estadísticas Rápidas")
    
    # --- FILTRO POBLACIÓN DINÁMICO ---
    if not df.empty:
        # Asegurar columna fecha_salida
        if 'fecha_salida' not in df.columns:
            df['fecha_salida'] = ''
        
        # Selector de filtro
        opcion_filtro = st.radio(
            "Filtro de Visualización para Gráficas:", 
            ["Activos (En Albergue)", "Inactivos (Salidas)", "Histórico (Todos)"], 
            horizontal=True
        )
        
        df_filtrado = pd.DataFrame()
        label_filtro = ""
        
        if opcion_filtro.startswith("Activos"):
            df_filtrado = df[df['fecha_salida'].isna() | (df['fecha_salida'] == '')]
            label_filtro = "Solo Activos"
        elif opcion_filtro.startswith("Inactivos"):
            df_filtrado = df[~(df['fecha_salida'].isna() | (df['fecha_salida'] == ''))]
            label_filtro = "Solo Salidas"
        else:
            df_filtrado = df
            label_filtro = "Todos"
        
        st.info(f"Mostrando datos para: **{len(df_filtrado)} personas** ({label_filtro})")
        
        # Cargar Encuestas
        try:
            df_encuestas = pd.read_excel(DB_FILE, sheet_name='Encuestas')
        except:
            df_encuestas = pd.DataFrame()

        c1, c2 = st.columns(2)
        
        with c1:
            st.write(f"**Nacionalidad ({label_filtro})**")
            if not df_filtrado.empty:
                st.bar_chart(df_filtrado['nacionalidad'].value_counts())
            else:
                st.caption("Sin datos para mostrar con este filtro.")
            
        with c2:
            st.write(f"**Estado Civil ({label_filtro})**")
            
            if not df_encuestas.empty and not df_filtrado.empty and 'estado_civil' in df_encuestas.columns:
                # Filtrar encuestas que coincidan con folios del filtro actual
                folios_validos = df_filtrado['folio'].astype(str).tolist()
                df_encuestas['folio_str'] = df_encuestas['folio_persona'].astype(str)
                
                encuestas_filtradas = df_encuestas[df_encuestas['folio_str'].isin(folios_validos)]
                
                if not encuestas_filtradas.empty:
                    fig_pie, ax_pie = plt.subplots(figsize=(6, 3))
                    datos_civil = encuestas_filtradas['estado_civil'].fillna('Sin Registro').value_counts()
                    ax_pie.pie(datos_civil, labels=datos_civil.index, autopct='%1.1f%%', startangle=90)
                    ax_pie.axis('equal') 
                    st.pyplot(fig_pie)
                else:
                    st.caption("No hay encuestas asociadas a este grupo.")
            else:
                st.caption("Datos insuficientes para graficar.")

        st.markdown("---")
        st.write("### Reporte de Altas y Bajas")
        
        if 'fecha_ingreso' in df.columns:
            # --- TABLA DIARIA ---
            st.write("#### 📅 Movimientos Diarios")
            
            # Altas por día (Robustez: convertir a string y tomar primeros 10 caracteres YYYY-MM-DD)
            df['ingreso_dt'] = pd.to_datetime(df['fecha_ingreso'].astype(str).str.strip().str[:10], errors='coerce').dt.date
            altas_dia = df['ingreso_dt'].value_counts().rename("Altas")
            
            # Bajas por día
            df['salida_dt'] = pd.to_datetime(df['fecha_salida'].astype(str).str.strip().str[:10], errors='coerce').dt.date
            bajas_dia = df['salida_dt'].value_counts().rename("Bajas")
            
            # Unir (Outer join para mostrar días donde solo hubo altas o solo bajas)
            # Convertimos indices a datetime para ordenar si es necesario, o concatenamos
            mov_diario = pd.concat([altas_dia, bajas_dia], axis=1).fillna(0).astype(int).sort_index()
            st.dataframe(mov_diario, use_container_width=True)
            
            # --- TABLA MENSUAL ---
            st.write("#### Movimientos Mensuales")
            
            # Extraer mes año (YYYY-MM)
            altas_mes = pd.to_datetime(df['fecha_ingreso'].astype(str).str.strip().str[:10], errors='coerce').dt.strftime('%Y-%m').value_counts().rename("Altas")
            bajas_mes = pd.to_datetime(df['fecha_salida'].astype(str).str.strip().str[:10], errors='coerce').dt.strftime('%Y-%m').value_counts().rename("Bajas")
            
            mov_mensual = pd.concat([altas_mes, bajas_mes], axis=1).fillna(0).astype(int).sort_index()
            st.dataframe(mov_mensual, use_container_width=True)
            
            st.markdown("---")
            st.markdown("---")
            st.header("Enviar Reporte PDF por Correo")
            
            # Input de destinatarios múltiple
            destinatarios_str = st.text_input("Destinatarios (separados por coma)", help="Ejemplo: correo1@gmail.com, correo2@hotmail.com")
            
            if st.button("Generar y Enviar Reporte PDF"):
                # Validar Credenciales del Sistema
                if not SMTP_USER or not SMTP_PASSWORD:
                    st.error(" Error de Configuración: No se encontraron las credenciales de correo.")
                    st.info("Por favor, configura 'SMTP_USER' y 'SMTP_PASSWORD' en los 'Secrets' de Streamlit Cloud o en '.streamlit/secrets.toml' localmente.")
                elif not destinatarios_str:
                    st.error("Ingresa al menos un destinatario.")
                else:
                    # Convertir string separado por comas a lista limpia
                    lista_destinos = [email.strip() for email in destinatarios_str.split(',') if email.strip()]
                    
                    if not lista_destinos:
                         st.error("No se detectaron correos válidos.")
                    else:
                        with st.spinner(f"Generando PDF y enviando a {len(lista_destinos)} destinatarios..."):
                            try:
                                pdf_bytes = generar_pdf_reporte(mov_diario, mov_mensual)
                                
                                asunto = f"Reporte Albergue - {datetime.now().strftime('%Y-%m-%d')}"
                                cuerpo = "Reporte detallado de Altas y Bajas (Diario y Mensual)."
                                
                                # Usar credenciales cargadas desde Secrets
                                exito, mensaje = enviar_correo(
                                    lista_destinos, asunto, cuerpo, 
                                    pdf_bytes, "Reporte_Movimientos.pdf", 
                                    SMTP_USER, SMTP_PASSWORD
                                )
                                
                                if exito:
                                    st.success(f"{mensaje}")
                                else:
                                    st.error(f"Error al enviar: {mensaje}")
                            except Exception as e:
                                st.error(f"Error generando reporte: {e}")