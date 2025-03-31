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

try:
    hoja_val = sheet.worksheet("Valoraciones")
except:
    hoja_val = sheet.add_worksheet(title="Valoraciones", rows="1000", cols="5")
    hoja_val.append_row(["Nombre", "Categoría", "Estrellas", "Comentario", "Fecha"])

df_val = pd.DataFrame(hoja_val.get_all_records())

# FUNCIONES AUXILIARES

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

# UI PRINCIPAL

st.title("Comarca del Sol - Guía de Servicios")
st.markdown("""
Seleccioná una categoría para explorar los datos disponibles de proveedores de servicios para Comarca del Sol y zonas aledañas.  
Podés buscar palabras como estas:
- **Prov. de Servicios** (Herrería, Carpintería, Fletes)  
- **Actividades** (Yoga, Niños, Vitrofusión)  
- **Comestibles** (Cerveza, Dulces, Carnes)
""")

categorias = ["Prov. de Servicios", "Actividades", "Comestibles"]
categoria = st.selectbox("Seleccioná una categoría:", categorias)
busqueda = st.text_input("Buscá un servicio (palabra clave):")

if categoria:
    st.markdown("---")
    if busqueda:
        try:
            df = pd.DataFrame(sheet.worksheet(categoria).get_all_records())
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df["Nombre"] = df["Nombre"].fillna("N/N")
            df_filtrado = df[df.apply(lambda row: busqueda.lower() in str(row.values).lower(), axis=1)]
            if not df_filtrado.empty:
                mostrar_tabla_con_telefonos(df_filtrado, categoria)
            else:
                st.warning("No contiene esta palabra. Podés buscarla en otra categoría o modificarla e intentarlo de nuevo.")
        except Exception:
            st.error("No pudimos cargar los datos. Revisá que la categoría exista en la planilla.")

    st.markdown("---")
    st.markdown("### Otros datos útiles")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Ver servicios básicos"):
            df_sb = pd.DataFrame(sheet.worksheet("Servicios Básicos").get_all_records())
            mostrar_tabla_con_telefonos(df_sb, "Servicios Básicos", permitir_valoracion=False)
    with colB:
        if st.button("Ver contactos comarca"):
            df_cc = pd.DataFrame(sheet.worksheet("Contactos Comarca").get_all_records())
            mostrar_tabla_con_telefonos(df_cc, "Contactos Comarca", permitir_valoracion=False)
    with colC:
        if st.button("Ver emergencias"):
            data_emergencias = [
                {"Nombre": "Bomberos Capilla del Señor", "Teléfono": "02323-491222"},
                {"Nombre": "Policía Capilla del Señor", "Teléfono": "02323-491222"},
                {"Nombre": "Hospital Capilla del Señor", "Teléfono": "02323-491555"},
                {"Nombre": "Clínica Parada Robles", "Teléfono": "02323-497000"},
                {"Nombre": "Veterinaria Sakura", "Teléfono": "0230-4667890"},
                {"Nombre": "Farmacia El Remanso", "Teléfono": "02323-499111"},
            ]
            df_emergencias = pd.DataFrame(data_emergencias)
            mostrar_tabla_con_telefonos(df_emergencias, "Emergencias", permitir_valoracion=False)

    st.markdown("---")
    st.markdown("### ¿Querés sumar un nuevo contacto?")
    with st.form("nuevo_contacto_form"):
        nombre_nuevo = st.text_input("Nombre")
        rubro_nuevo = st.text_input("Rubro")
        categoria_nuevo = st.selectbox("Categoría", categorias)
        telefono_nuevo = st.text_input("Teléfono (sin +54 9, solo desde 11 o 023)")
        zona_nueva = st.text_input("Zona")
        usuario = st.text_input("Tu nombre (opcional)")
        enviado = st.form_submit_button("Agregar contacto")
        if enviado:
            if nombre_nuevo and rubro_nuevo and telefono_nuevo and zona_nueva:
                hoja_cat = sheet.worksheet(categoria_nuevo)
                existentes = hoja_cat.get_all_records()
                repetido = any(
                    (r.get("Teléfono") == telefono_nuevo and r.get("Rubro") == rubro_nuevo)
                    for r in existentes
                )
                if not repetido:
                    nueva_fila = [nombre_nuevo, rubro_nuevo, telefono_nuevo, zona_nueva, usuario, datetime.now().strftime("%Y-%m-%d %H:%M")]
                    hoja_cat.append_row(nueva_fila)
                    st.success("Contacto agregado correctamente.")
                else:
                    st.warning("Este contacto ya existe con ese teléfono y rubro.")
            else:
                st.error("Faltan completar algunos campos obligatorios.")
