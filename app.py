# app.py
import streamlit as st
import pandas as pd
import unicodedata
import gspread
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
    hoja_agregados = sheet.add_worksheet(title="Contactos Nuevos", rows="1000", cols="6")
    hoja_agregados.append_row(["Nombre", "Rubro", "Teléfono", "Zona", "Usuario", "Fecha"])

df_val = pd.DataFrame(hoja_val.get_all_records())

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
                        numero = str(val)
                        link = f'<a href="tel:{numero}">📞 {numero}</a>'
                        info += f"**{col}:** {link}  <br>"
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
                enviado = st.form_submit_button("Enviar valoración")
                if enviado:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    hoja_val.append_row([nombre, categoria, estrellas, comentario, fecha])
                    st.success("¡Gracias por tu valoración!")

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
    if st.button("🚨 Emergencia Comarca", use_container_width=True):
        st.markdown("""
            <meta http-equiv="refresh" content="0; url=tel:01123456789">
        """, unsafe_allow_html=True)

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
df = pd.DataFrame(sheet.worksheet(nombres_hojas[categoria]).get_all_records())

termino = st.text_input("¿Qué estás buscando?")

if termino:
    palabras = incluir_sinonimos(normalizar_texto(termino))
    df_filtro = df[df.apply(lambda fila: any(p in normalizar_texto(str(v)) for p in palabras for v in fila.values), axis=1)]
    if not df_filtro.empty:
        st.success(f"{len(df_filtro)} resultado(s) encontrado(s):")
        mostrar_tabla_con_telefonos(df_filtro, categoria)
    else:
        st.warning("No se encontraron resultados. Podés intentar con otra palabra o categoría.")

# OTROS DATOS ÚTILES
if st.button("Ver servicios básicos"):
    df_basicos = pd.DataFrame(sheet.worksheet("Servicios Básicos").get_all_records())
    st.subheader("Servicios Básicos en la zona")
    mostrar_tabla_con_telefonos(df_basicos, "Servicios Básicos", permitir_valoracion=False)

if st.button("Ver contactos comarca"):
    df_comarca = pd.DataFrame(sheet.worksheet("Datos Comarca").get_all_records())
    st.subheader("Datos de contacto oficiales de Comarca")
    mostrar_por_rubro(df_comarca, "Comarca")

if st.button("Ver emergencias"):
    df_emergencias = pd.DataFrame(sheet.worksheet("Emergencias").get_all_records())
    st.subheader("Emergencias, Urgencias y Centros de Atención")
    mostrar_por_rubro(df_emergencias, "Emergencias")

# FORMULARIO PARA AGREGAR NUEVO CONTACTO
st.markdown("---")
with st.expander("➕ Agregar nuevo contacto al directorio"):
    with st.form("form_nuevo_contacto"):
        nombre = st.text_input("Nombre del contacto")
        rubro = st.text_input("Rubro")
        telefono = st.text_input("Teléfono (sin +54 9)")
        zona = st.text_input("Zona")
        usuario = st.text_input("Tu nombre (opcional)")
        enviar = st.form_submit_button("Agregar contacto")

        if enviar:
            ya_existe = hoja_agregados.get_all_records()
            df_existente = pd.DataFrame(ya_existe)
            if not df_existente[(df_existente["Teléfono"] == telefono) & (df_existente["Rubro"] == rubro)].empty:
                st.warning("Este contacto ya fue ingresado previamente.")
            else:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                hoja_agregados.append_row([nombre, rubro, telefono, zona, usuario, fecha])
                st.success("¡Contacto agregado para revisión!")
