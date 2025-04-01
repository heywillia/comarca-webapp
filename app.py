# app.py
import streamlit as st
import pandas as pd
import unicodedata
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="Comarca WebApp", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1B1gSYnyx1VVNEuhI1iwwX_xZ9sFKOI4Ylh7Dhrsu9SM/edit"

@st.cache_resource
def conectar_a_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    info = st.secrets["google_sheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
    cliente = gspread.authorize(creds)
    return cliente

# Cacheamos la carga de datos para mejorar rendimiento
@st.cache_data(ttl=600)  # Refresca cada 10 minutos
def cargar_datos_val():
    return pd.DataFrame(sheet.worksheet("Valoraciones").get_all_records())

cliente_sheets = conectar_a_sheets()
sheet = cliente_sheets.open_by_url(SHEET_URL)

nombres_hojas = {
    "Prov. de Servicios": "Prov. de Servicios & Más",
    "Actividades": "Actividades",
    "Comestibles": "Comestibles",
    "Emergencias": "Emergencias",
    "Comarca": "Datos Comarca"
}

sinonimos = {
    "plomero": ["plomería", "caños", "agua", "desagüe"],
    "electricista": ["electricidad", "cableado", "enchufe", "luces"],
    "gasista": ["gas", "estufa", "calefacción"],
    "fletes": ["camioneta", "mudanza", "traslado"],
    "niños": ["niñera", "juegos", "infantil", "infancia"],
    "dulces": ["mermeladas", "conservas", "casero"]
}

try:
    hoja_val = sheet.worksheet("Valoraciones")
except:
    hoja_val = sheet.add_worksheet(title="Valoraciones", rows="1000", cols="5")
    hoja_val.append_row(["Nombre", "Categoría", "Estrellas", "Comentario", "Fecha"])

try:
    hoja_agregados = sheet.worksheet("Contactos Nuevos")
except:
    hoja_agregados = sheet.add_worksheet(title="Contactos Nuevos", rows="1000", cols="7")
    hoja_agregados.append_row(["Nombre", "Rubro", "Teléfono", "Zona", "Usuario", "Fecha", "Categoría"])

df_val = cargar_datos_val()

# UTILS

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    return texto

def incluir_sinonimos(palabra):
    resultados = [palabra]
    for clave, lista in sinonimos.items():
        if palabra in lista:
            resultados.append(clave)
            resultados.extend(lista)
        elif palabra == clave:
            resultados.extend(lista)
    return list(set(resultados))

def mostrar_estrellas(promedio):
    llenas = int(promedio)
    media = promedio - llenas >= 0.5
    vacias = 5 - llenas - int(media)
    return "⭐" * llenas + ("✴️" if media else "") + "☆" * vacias

def formatear_telefono(numero):
    """
    Formatea un número de teléfono argentino para llamadas o WhatsApp
    Maneja tanto celulares (comienzan con 11) como fijos (otros prefijos)
    """
    # Primero limpiamos el número de cualquier carácter no numérico
    numero_limpio = re.sub(r'[^\d]', '', numero)
    
    # Quitamos los prefijos +54 o +549 si existen
    if numero_limpio.startswith('549'):
        numero_limpio = numero_limpio[3:]
    elif numero_limpio.startswith('54'):
        numero_limpio = numero_limpio[2:]
    
    # Si empieza con 0, lo quitamos (por ejemplo, 011 -> 11)
    if numero_limpio.startswith('0'):
        numero_limpio = numero_limpio[1:]
    
    # Determinamos si es celular o fijo basado en el prefijo 11
    es_celular = numero_limpio.startswith('11') and len(numero_limpio) >= 10
    
    # Formateamos para visualización
    if len(numero_limpio) >= 6:
        if es_celular:
            # Para celulares: ejemplo +54 9 11 1234-5678
            if len(numero_limpio) >= 10:
                numero_formateado = f"+54 9 {numero_limpio[:2]} {numero_limpio[2:6]}-{numero_limpio[6:]}"
            else:
                numero_formateado = f"+54 9 {numero_limpio[:2]} {numero_limpio[2:]}"
        else:
            # Para fijos: ejemplo +54 2323 123456
            if len(numero_limpio) >= 10:
                # Por ejemplo, 2323 123456
                prefijo = numero_limpio[:4]
                resto = numero_limpio[4:]
                numero_formateado = f"+54 {prefijo} {resto}"
            else:
                # Hacemos nuestro mejor esfuerzo para números cortos
                prefijo = numero_limpio[:2]
                resto = numero_limpio[2:]
                numero_formateado = f"+54 {prefijo} {resto}"
    else:
        numero_formateado = numero  # Si es muy corto, lo dejamos como está
    
    # Preparamos los números para enlaces
    if es_celular:
        # Para WhatsApp necesitamos +549 seguido del número sin espacios ni guiones
        numero_whatsapp = f"+549{numero_limpio}"
        return {
            "formateado": numero_formateado,
            "whatsapp": numero_whatsapp,
            "llamada": f"+54{numero_limpio}",
            "es_celular": True
        }
    else:
        # Para teléfono fijo, solo llamada
        return {
            "formateado": numero_formateado,
            "llamada": f"+54{numero_limpio}",
            "es_celular": False
        }

def validar_telefono(numero):
    # Elimina espacios, guiones y paréntesis
    numero_limpio = re.sub(r'[\s\-\(\)]', '', numero)
    # Verifica que solo contenga números, + y quizás algún espacio
    numero_limpio = re.sub(r'[\+]', '', numero_limpio)
    return numero_limpio.isdigit()

def mostrar_tabla_con_telefonos(df, categoria, permitir_valoracion=True):
    df = df.copy()
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    if "Nombre" not in df.columns:
        if df.columns.size > 0:
            df.rename(columns={df.columns[0]: "Nombre"}, inplace=True)
        else:
            df["Nombre"] = "N/N"
    df["Nombre"] = df["Nombre"].fillna("N/N")
    form_ids = set()

    for i, row in df.iterrows():
        nombre = row.get("Nombre", "N/N")
        form_key = f"form_{nombre}_{categoria}_{i}"
        if form_key in form_ids:
            continue
        form_ids.add(form_key)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("---")
            info = ""
            for col, val in row.items():
                if pd.notna(val):
                    if "tel" in col.lower():
                        numero = str(val).strip()
                        telefono_info = formatear_telefono(numero)
                        
                        # Creamos los enlaces adecuados según el tipo de teléfono
                        if telefono_info["es_celular"]:
                            # Para celulares ofrecemos WhatsApp y llamada
                            links = f'<a href="tel:{telefono_info["llamada"]}">📞 Llamar</a> | <a href="https://wa.me/{telefono_info["whatsapp"]}">💬 WhatsApp</a>'
                        else:
                            # Para fijos solo llamada
                            links = f'<a href="tel:{telefono_info["llamada"]}">📞 Llamar</a>'
                            
                        info += f"**{col}:** {telefono_info['formateado']} {links}  <br>"
                    else:
                        info += f"**{col}:** {val}  <br>"

            st.markdown(info, unsafe_allow_html=True)

        with col2:
            if not permitir_valoracion:
                continue
            valoraciones = df_val[(df_val['Nombre'] == nombre) & (df_val['Categoría'] == categoria)]
            if not valoraciones.empty:
                promedio = valoraciones["Estrellas"].mean()
                total = len(valoraciones)
                st.markdown(f"**Valoración promedio:** {mostrar_estrellas(promedio)} ({round(promedio,1)} / 5) basada en {total} opiniones")
            with st.form(form_key):
                st.markdown("**Dejá tu valoración**")
                estrellas = st.slider("Estrellas", 1, 5, 5, key=f"slider_{form_key}")
                comentario = st.text_input("Comentario (opcional)", key=f"comentario_{form_key}")
                confirmar = st.checkbox("Confirmo que esta es mi valoración", key=f"confirm_{form_key}")
                enviado = st.form_submit_button("Enviar valoración")
                if enviado:
                    if confirmar:
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                        hoja_val.append_row([nombre, categoria, estrellas, comentario, fecha])
                        st.success("¡Gracias por tu valoración!")
                        # Actualizamos el dataframe de valoraciones
                        st.cache_data.clear()
                    else:
                        st.warning("Por favor confirma tu valoración marcando la casilla")

def mostrar_por_rubro(df, categoria):
    df = df.copy()
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df["Nombre"] = df["Nombre"].fillna("N/N")
    if "Rubro" not in df.columns:
        df["Rubro"] = "General"
    rubros = df["Rubro"].fillna("General").unique()
    for rubro in rubros:
        subset = df[df["Rubro"] == rubro]
        with st.expander(f"🔻 {rubro}"):
            mostrar_tabla_con_telefonos(subset, categoria, permitir_valoracion=False)

# === INTERFAZ ===

with st.sidebar:
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.experimental_rerun()
        
    if st.button("🚨 Emergencia Comarca", use_container_width=True):
        st.markdown("""
            <meta http-equiv="refresh" content="0; url=tel:01123456789">
        """, unsafe_allow_html=True)

    if st.button("📋 Ver contactos comarca", use_container_width=True):
        df_comarca = cargar_datos(sheet.worksheet("Datos Comarca"))
        st.subheader("Datos de contacto oficiales de Comarca")
        mostrar_por_rubro(df_comarca, "Comarca")

st.title("Comarca del Sol - Guía de Servicios")

st.markdown("""
Seleccioná una categoría para explorar los datos disponibles de proveedores de servicios para Comarca del Sol y zonas aledañas.

Podés buscar palabras como estas:

- **Prov. de Servicios** (Ej: Herrería, Carpintería, Fletes, Plomería)
- **Actividades** (Ej: Yoga, Niños, Vitrofusión, Taller)
- **Comestibles** (Ej: Cerveza, Dulces, Pan, Carnes)

Utilizá el buscador para filtrar por nombre, rubro o palabra clave. También podés dejar valoraciones ⭐ y sugerencias.
""")

with st.expander("🤝 Asociate a Comarca del Sol", expanded=False):
    st.markdown("""
    Para formar parte de la comunidad:
    1. 📩 Enviá un correo a **comarcadelsoloficial@gmail.com**
    2. 📝 Completá el formulario de Google que te enviaremos
    3. 💳 Aboná la cuota del mes en curso
    4. ✅ Te incluiremos en los grupos oficiales de difusión y coordinación (previa autorización)
    ¡Ser parte suma y fortalece a la comunidad!
    """)

categoria = st.selectbox("Seleccioná una categoría:", list(nombres_hojas.keys()))
df = cargar_datos(sheet.worksheet(nombres_hojas[categoria]))

termino = st.text_input("¿Qué estás buscando?")

if termino:
    palabras = incluir_sinonimos(normalizar_texto(termino))
    df_filtro = df[df.apply(lambda fila: any(p in normalizar_texto(str(v)) for p in palabras for v in fila.values), axis=1)]
    
    if not df_filtro.empty:
        st.success(f"✅ {len(df_filtro)} resultado(s) encontrado(s) para '{termino}':")
        with st.container():
            st.markdown("### Resultados de la búsqueda")
            mostrar_tabla_con_telefonos(df_filtro, categoria)
    else:
        st.warning(f"❌ No se encontraron resultados para '{termino}'. Podés intentar con otra palabra o categoría.")
        st.info("💡 Palabras similares que podrías probar: " + ", ".join(palabras))

# OTROS DATOS ÚTILES
if st.button("Ver servicios básicos"):
    df_basicos = cargar_datos(sheet.worksheet("Servicios Básicos"))
    st.subheader("Servicios Básicos en la zona")
    mostrar_tabla_con_telefonos(df_basicos, "Servicios Básicos", permitir_valoracion=False)

if st.button("Ver emergencias"):
    df_emergencias = cargar_datos(sheet.worksheet("Emergencias"))
    st.subheader("Emergencias, Urgencias y Centros de Atención")
    mostrar_por_rubro(df_emergencias, "Emergencias")

# FORMULARIO PARA AGREGAR NUEVO CONTACTO
st.markdown("---")
with st.expander("➕ Agregar nuevo contacto al directorio"):
    with st.form("form_nuevo_contacto"):
        nombre = st.text_input("Nombre del contacto")
        rubro = st.text_input("Rubro")
        telefono = st.text_input("Teléfono (con o sin código de área)")
        zona = st.text_input("Zona")
        categoria_form = st.selectbox("Categoría", ["Prov. de Servicios", "Actividades", "Comestibles"])
        usuario = st.text_input("Tu nombre (opcional)")
        confirmar_contacto = st.checkbox("Confirmo que esta información es correcta")
        enviar = st.form_submit_button("Agregar contacto")

        if enviar:
            if not nombre:
                st.error("Por favor ingresa un nombre para el contacto")
            elif not rubro:
                st.error("Por favor ingresa un rubro para el contacto")
            elif not telefono:
                st.error("Por favor ingresa un teléfono para el contacto")
            elif telefono and not validar_telefono(telefono):
                st.error("Por favor ingresa un teléfono válido (solo números, puede incluir + al principio)")
            elif not confirmar_contacto:
                st.warning("Por favor confirma que la información es correcta marcando la casilla")
            else:
                hoja_destino = sheet.worksheet(nombres_hojas[categoria_form])
                columnas = hoja_destino.row_values(1)
                nueva_fila = ["" for _ in columnas]
                mapeo = {"Nombre": nombre, "Rubro": rubro, "Teléfono": telefono, "Zona": zona}
                for i, col in enumerate(columnas):
                    if col in mapeo:
                        nueva_fila[i] = mapeo[col]
                hoja_destino.append_row(nueva_fila)

                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                hoja_agregados.append_row([nombre, rubro, telefono, zona, usuario, fecha, categoria_form])
                st.success("¡Contacto agregado correctamente!")
                # Limpiamos el caché para reflejar los cambios
                st.cache_data.clear()