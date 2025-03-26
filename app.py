# app.py
import streamlit as st
import pandas as pd
import unicodedata
import gspread
import json
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
    info = st.secrets["google_sheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(str(info)), scope)
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
# CARGAR DATOS PRINCIPALES
# --------------------------

@st.cache_data
def cargar_datos():
    archivo = pd.ExcelFile("Datos Comarca.xlsx")
    return {
        "Prov. de Servicios": archivo.parse("Prov. de Servicios & Más"),
        "Actividades": archivo.parse("Actividades"),
        "Comestibles": archivo.parse("Comestibles"),
        "Servicios Básicos": archivo.parse("Servicios Básicos"),
        "Contactos Comarca": archivo.parse("Contactos Comarca")
    }

datos = cargar_datos()

# Ejemplos por categoría
ejemplos = {
    "Prov. de Servicios": ["Herrería", "Carpinteria", "Fletes"],
    "Actividades": ["Yoga", "Cultural / Niños", "Vitrofusión"],
    "Comestibles": ["Cerveza", "Dulces Caseros", "Carnes y Pescados"]
}

# --------------------------
# INTERFAZ DE USUARIO
# --------------------------

st.markdown("<h1 style='text-align: center;'>Buscador de servicios, actividades y productos</h1>", unsafe_allow_html=True)

st.markdown("<div style='text-align: center;'>Seleccioná una categoría para explorar los datos disponibles en la comarca. Podés buscar palabras como estas:</div>", unsafe_allow_html=True)
for cat, ej in ejemplos.items():
    st.markdown(f"<div style='text-align: center;'>**{cat}** → _" + ", ".join(ej) + "_</div>", unsafe_allow_html=True)

st.divider()

# Botones de categoría
categoria = st.session_state.get("categoria", None)
with st.container():
    st.button("Prov. de Servicios", use_container_width=True, key="btn1")
    st.button("Actividades", use_container_width=True, key="btn2")
    st.button("Comestibles", use_container_width=True, key="btn3")

if st.session_state.get("btn1"):
    categoria = "Prov. de Servicios"
elif st.session_state.get("btn2"):
    categoria = "Actividades"
elif st.session_state.get("btn3"):
    categoria = "Comestibles"

if categoria:
    st.session_state["categoria"] = categoria
    st.markdown(f"<h2 style='text-align: center;'>Búsqueda en: {categoria}</h2>", unsafe_allow_html=True)
    query = st.text_input("¿Qué estás buscando?")

    if query:
        df = datos[categoria]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        if "Nombre" in df.columns:
            df["Nombre"] = df["Nombre"].fillna("N/N")

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

# Botones finales horizontales
st.divider()
st.markdown("<h3 style='text-align: center;'>Otros datos útiles</h3>", unsafe_allow_html=True)

with st.container():
    st.button("Ver Servicios Básicos", use_container_width=True, key="basicos")
    st.button("Ver Contactos Comarca", use_container_width=True, key="comarca")

if st.session_state.get("basicos"):
    mostrar_tabla_con_telefonos(datos["Servicios Básicos"], "Servicios Básicos", permitir_valoracion=False)
if st.session_state.get("comarca"):
    mostrar_tabla_con_telefonos(datos["Contactos Comarca"], "Contactos Comarca", permitir_valoracion=False)
