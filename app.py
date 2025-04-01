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
    "plomería": ["plomero", "caños", "agua", "desagüe"],
    "electricidad": ["electricista", "cableado", "enchufe", "luces"],
    "fletes": ["camioneta", "mudanza", "traslado"],
    "yoga": ["relajación", "meditación", "posturas"],
    "cultura infantil": ["niños", "infantil", "juegos", "niñera"],
    "dulces caseros": ["mermeladas", "conservas", "casero", "dulces"],
    "carnes": ["asado", "pescado", "pollo", "carne"]
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

df_val = pd.DataFrame(hoja_val.get_all_records())

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
        if palabra in lista or palabra == clave:
            resultados.append(clave)
            resultados.extend(lista)
    return list(set(resultados))

def mostrar_estrellas(promedio):
    llenas = int(promedio)
    media = promedio - llenas >= 0.5
    vacias = 5 - llenas - int(media)
    return "⭐" * llenas + ("✴️" if media else "") + "☆" * vacias

def contacto_ya_existe(nombre, telefono, hoja):
    df_existente = pd.DataFrame(hoja.get_all_records())
    telefono_normalizado = str(telefono).strip().replace(" ", "").replace("-", "")
    df_existente["Telefono_check"] = df_existente[df_existente.columns[2]].astype(str).str.replace(" ", "").str.replace("-", "")
    ya_existe = (
        (df_existente["Nombre"].str.lower() == nombre.lower()) &
        (df_existente["Telefono_check"] == telefono_normalizado)
    ).any()
    return ya_existe

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
                        numero_llamada = numero.replace(" ", "").replace("-", "")
                        if not numero_llamada.startswith("+54"):
                            if numero_llamada.startswith("0"):
                                numero_llamada = "+549" + numero_llamada[1:]
                            else:
                                numero_llamada = "+549" + numero_llamada
                        link = f'<a href="tel:{numero_llamada}">📞 {numero}</a>'
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
