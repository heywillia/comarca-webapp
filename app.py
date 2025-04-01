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

# (El resto del código sigue igual, pero por límite de longitud lo partimos en dos partes)