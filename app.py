# app.py
import streamlit as st
import pandas as pd
import unicodedata
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# SETEAR CONFIGURACIÓN DE PÁGINA DEBE SER LO PRIMERO
st.set_page_config(page_title="Comarca WebApp", layout="wide")

# --------------------------
# CONFIGURACIÓN GOOGLE SHEETS
# --------------------------

SHEET_URL = "https://docs.google.com/spreadsheets/d/1B1gSYnyx1VVNEuhI1iwwX_xZ9sFKOI4Ylh7Dhrsu9SM/edit"

def conectar_a_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    info = st.secrets["google_sheets"]  # ya es un diccionario
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
    cliente = gspread.authorize(creds)
    return cliente

cliente_sheets = conectar_a_sheets()
sheet = cliente_sheets.open_by_url(SHEET_URL)

# Intentar abrir la hoja "Valoraciones"
try:
    hoja_val = sheet.worksheet("Valoraciones")
except:
    hoja_val = sheet.add_worksheet(title="Valoraciones", rows="1000", cols="5")
    hoja_val.append_row(["Nombre", "Categoría", "Estrellas", "Comentario", "Fecha"])

# Cargar valoraciones existentes
df_val = pd.DataFrame(hoja_val.get_all_records())

# --------------------------
# FUNCIONES AUXILIARES
# --------------------------

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    return texto

def mostrar_estrellas(promedio):
    llenas = int(promedio)
    media = promedio - llenas >= 0.5
    vacias = 5 - llenas - int(media)
    return "⭐" * llenas + ("✴️" if media else "") + "☆" * vacias

def mostrar_tabla_con_telefonos(df, categoria, permitir_valoracion=True):
    df = df.copy()
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    if "Nombre" in df.columns:
        df["Nombre"] = df["Nombre"].fillna("N/N")

    for _, row in df.iterrows():
        with st.container():
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
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
            st.markdown("</div>", unsafe_allow_html=True)

        if not permitir_valoracion:
            continue

        nombre = row['Nombre'] if pd.notna(row['Nombre']) else "N/N"

        if all(col in df_val.columns for col in ['Nombre', 'Categoría', 'Estrellas']):
            valoraciones = df_val[(df_val['Nombre'] == nombre) & (df_val['Categoría'] == categoria)]
            if not valoraciones.empty:
                promedio = valoraciones["Estrellas"].mean()
                total = len(valoraciones)
                st.markdown(f"<div style='text-align: center;'>**Valoración promedio:** {mostrar_estrellas(promedio)} ({round(promedio,1)} / 5) basada en {total} opiniones</div>", unsafe_allow_html=True)
        else:
            st.info("Aún no hay valoraciones disponibles.")

        with st.form(f"form_{nombre}_{categoria}"):
            st.markdown("<div style='text-align: center;'>**Dejá tu valoración**</div>", unsafe_allow_html=True)
            estrellas = st.slider("Estrellas", 1, 5, 5)
            comentario = st.text_input("Comentario (opcional)")
            enviado = st.form_submit_button("Enviar valoración")
            if enviado:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                hoja_val.append_row([nombre, categoria, estrellas, comentario, fecha])
                st.success("¡Gracias por tu valoración!")

# --------------------------
# INTERFAZ INICIAL
# --------------------------

st.markdown("""
<h1 style='text-align: center;'>Buscador de servicios, actividades y productos</h1>
<p style='text-align: center;'>Seleccioná una categoría para explorar los datos disponibles de proveedores de servicios para Comarca del Sol y zonas aledañas. Podés buscar palabras como estas:</p>
<p style='text-align: center;'>
Prov. de Servicios (<i>Herrería, Carpintería, Fletes</i>)<br>
Actividades (<i>Yoga, Niños, Vitrofusión</i>)<br>
Comestibles (<i>Cerveza, Dulces, Carnes</i>)
</p>
""", unsafe_allow_html=True)

st.divider()

col1, col2, col3 = st.columns([1,1,1])
categoria = st.session_state.get("categoria", None)

with col1:
    if st.button("Prov. de Servicios", use_container_width=True):
        categoria = "Prov. de Servicios"
with col2:
    if st.button("Actividades", use_container_width=True):
        categoria = "Actividades"
with col3:
    if st.button("Comestibles", use_container_width=True):
        categoria = "Comestibles"

if categoria:
    st.session_state["categoria"] = categoria
    st.markdown(f"<h2 style='text-align: center;'>Búsqueda en: {categoria}</h2>", unsafe_allow_html=True)
    query = st.text_input("¿Qué estás buscando?")

    if query:
        df = pd.read_excel("Datos Comarca.xlsx", sheet_name=categoria)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        query_norm = normalizar_texto(query)

        def coincide(row):
            texto = " ".join([normalizar_texto(str(v)) for v in row.values])
            return query_norm in texto

        resultados = df[df.apply(coincide, axis=1)]

        if not resultados.empty:
            st.success(f"{len(resultados)} resultado(s) encontrado(s):")
            mostrar_tabla_con_telefonos(resultados, categoria)
        else:
            st.warning("No se encontraron resultados.")
    else:
        st.info("Escribí una palabra para buscar.")

# --------------------------
# SECCIÓN FINAL - INFORMACIÓN EXTRA
# --------------------------

st.markdown("<br><hr><h3 style='text-align: center;'>Otros datos útiles</h3>", unsafe_allow_html=True)
b1, b2 = st.columns(2)

with b1:
    if st.button("Ver Servicios Básicos", use_container_width=True):
        df_serv = pd.read_excel("Datos Comarca.xlsx", sheet_name="Servicios Básicos")
        st.subheader("Servicios Básicos")
        mostrar_tabla_con_telefonos(df_serv, "Servicios Básicos", permitir_valoracion=False)

with b2:
    if st.button("Ver Contactos Comarca", use_container_width=True):
        df_cont = pd.read_excel("Datos Comarca.xlsx", sheet_name="Contactos Comarca")
        st.subheader("Contactos Comarca")
        mostrar_tabla_con_telefonos(df_cont, "Contactos Comarca", permitir_valoracion=False)
