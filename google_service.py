import requests


def intentar_parsear_coordenadas(texto):
    """
    Detecta si el texto viene como coordenadas directas.
    Ejemplo: 19.951234,-99.532456
    """
    try:
        partes = texto.split(",")

        if len(partes) != 2:
            return None

        lat = float(partes[0].strip())
        lng = float(partes[1].strip())

        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng

        return None

    except ValueError:
        return None


def obtener_coordenadas_osm(lugar):
    """
    Si recibe coordenadas, las usa directo.
    Si recibe texto, usa Nominatim de OpenStreetMap.
    """
    coordenadas_directas = intentar_parsear_coordenadas(lugar)

    if coordenadas_directas:
        lat, lng = coordenadas_directas
        direccion_formateada = f"{lat}, {lng}"
        return coordenadas_directas, direccion_formateada

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": lugar,
        "format": "json",
        "addressdetails": 0,
        "limit": 1,
        "countrycodes": "mx"
    }
    headers = {
        "User-Agent": "GPS-Main-App/1.0"
    }

    respuesta = requests.get(url, params=params, headers=headers, timeout=15)
    datos = respuesta.json()

    if not datos:
        raise RuntimeError("No se encontraron coordenadas con OSM para ese lugar.")

    resultado = datos[0]
    lat = float(resultado["lat"])
    lon = float(resultado["lon"])
    direccion_formateada = resultado.get("display_name", lugar)

    return (lat, lon), direccion_formateada


def obtener_rutas_osrm(origen_coord, destino_coord):
    """
    Pide rutas a OSRM con alternativas y devuelve geometrías y datos.
    """
    lon_origen, lat_origen = origen_coord[1], origen_coord[0]
    lon_destino, lat_destino = destino_coord[1], destino_coord[0]

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon_origen},{lat_origen};{lon_destino},{lat_destino}"
    )
    params = {
        "alternatives": "true",
        "geometries": "geojson",
        "overview": "full",
        "steps": "false"
    }

    respuesta = requests.get(url, params=params, timeout=20)
    datos = respuesta.json()

    if datos.get("code") != "Ok":
        motivo = datos.get("message", "Sin detalle")
        raise RuntimeError(f"OSRM respondió error: {motivo}")

    rutas = []
    for ruta in datos.get("routes", []):
        rutas.append({
            "geometry": [
                (punto[1], punto[0]) for punto in ruta["geometry"]["coordinates"]
            ],
            "distance": ruta["distance"],
            "duration": ruta["duration"],
            "weight_name": ruta.get("weight_name", "")
        })

    if not rutas:
        raise RuntimeError("No se encontraron rutas disponibles.")

    return rutas
