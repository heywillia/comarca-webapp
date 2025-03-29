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

CATEGORIAS_PRINCIPALES = ["Prov. de Servicios", "Actividades", "Comestibles"]

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
    return texto.strip()

def mostrar_estrellas(promedio):
    llenas = int(promedio)
    media = promedio - llenas >= 0.5
    vacias = 5 - llenas - int(media)
    return "⭐" * llenas + ("✴️" if media else "") + "☆" * vacias

def mostrar_tabla_con_telefonos(df, categoria, permitir_valoracion=True):
    df = df.copy()
    try:
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    except Exception:
        st.warning("La categoría seleccionada no tiene columnas válidas para mostrar.")
        return

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

            if all(col in df_val.columns for col in ['Nombre', 'Categoría', 'Estrellas']):
                valoraciones = df_val[(df_val['Nombre'] == nombre) & (df_val['Categoría'] == categoria)]
                if not valoraciones.empty:
                    promedio = valoraciones["Estrellas"].mean()
                    total = len(valoraciones)
                    st.markdown(f"**Valoración promedio:** {mostrar_estrellas(promedio)} ({round(promedio,1)} / 5) basada en {total} opiniones")
            else:
                st.info("Aún no hay valoraciones disponibles.")

            with st.form(form_key):
                st.markdown("**Dejá tu valoración**")
                estrellas = st.slider("Estrellas", 1, 5, 5, key=f"slider_{form_key}")
                comentario = st.text_input("Comentario (opcional)", key=f"comentario_{form_key}")
                enviado = st.form_submit_button("Enviar valoración")
                if enviado:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    hoja_val.append_row([nombre, categoria, estrellas, comentario, fecha])
                    st.success("¡Gracias por tu valoración!")

# --------------------------
# FORMULARIO PARA AGREGAR NUEVO SERVICIO
# --------------------------

def agregar_formulario_servicio(categoria):
    st.markdown("---")
    with st.expander("➕ Agregar nuevo servicio"):
        with st.form("form_nuevo_servicio"):
            nombre = st.text_input("Nombre del servicio")
            rubro = st.text_input("Rubro")
            telefono = st.text_input("Teléfono (sin +54 9, ej: 11..., 023...)")
            zona = st.text_input("Zona / Localidad")
            usuario = st.text_input("Tu nombre (opcional)")
            enviar = st.form_submit_button("Enviar")

            if enviar:
                if not nombre or not rubro or not telefono:
                    st.warning("Por favor completá todos los campos obligatorios (nombre, rubro, teléfono).")
                    return

                try:
                    hoja_cat = sheet.worksheet(categoria)
                    registros = hoja_cat.get_all_records()
                except:
                    st.error("No se pudo acceder a la hoja correspondiente.")
                    return

                telefono_normalizado = telefono.replace(" ", "").replace("-", "").strip()
                rubro_normalizado = normalizar_texto(rubro)
                for r in registros:
                    tel_r = str(r.get("Teléfono", "")).replace(" ", "").replace("-", "").strip()
                    rubro_r = normalizar_texto(r.get("Rubro", ""))
                    if tel_r == telefono_normalizado and rubro_r == rubro_normalizado:
                        st.warning("Ya existe un servicio con ese teléfono y rubro en esta categoría.")
                        return

                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                nueva_fila = [nombre, rubro, telefono, zona, usuario, fecha]
                encabezados = hoja_cat.row_values(1)
                while len(nueva_fila) < len(encabezados):
                    nueva_fila.append("")
                hoja_cat.append_row(nueva_fila)
                st.success("¡Gracias! El servicio fue agregado correctamente.")
