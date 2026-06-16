from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify

from google_service import obtener_coordenadas_osm, obtener_rutas_osrm
from grafo import (
    calcular_ruta_con_algoritmo,
    zona_horaria_por_longitud,
    hora_local_por_offset,
    encontrar_zonas_rojas,
    estimar_peaje_por_vehiculo,
    obtener_rendimiento_por_vehiculo,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calcular_ruta", methods=["POST"])
def calcular_ruta():
    data = request.get_json(silent=True) or {}

    origen = data.get("origen", "").strip()
    destino = data.get("destino", "").strip()
    algoritmo = data.get("algoritmo", "manhattan")
    vehiculo = data.get("vehiculo", "auto")
    usar_peajes = bool(data.get("peajes", True))
    rendimiento_personalizado = data.get("rendimiento_personalizado")

    if not origen or not destino:
        return jsonify({
            "error": "Debes escribir origen y destino."
        }), 400

    try:
        origen_coord, origen_direccion = obtener_coordenadas_osm(origen)
        destino_coord, destino_direccion = obtener_coordenadas_osm(destino)

        if origen_coord == destino_coord:
            return jsonify({
                "error": "El origen y el destino son el mismo punto.",
                "detalle": "Selecciona dos puntos diferentes."
            }), 400

        rutas_osm = obtener_rutas_osrm(origen_coord, destino_coord)

        coordenadas, distancia_metros = calcular_ruta_con_algoritmo(
            rutas_osm, algoritmo
        )

        duracion_segundos = rutas_osm[0]["duration"]

        zonas_rojas = encontrar_zonas_rojas(coordenadas)
        costo_peaje, peajes_detectados = estimar_peaje_por_vehiculo(
            coordenadas, vehiculo, usar_peajes
        )

        rendimiento = obtener_rendimiento_por_vehiculo(
            vehiculo, rendimiento_personalizado
        )

    except Exception as error:
        return jsonify({
            "error": "No se pudo calcular la ruta.",
            "detalle": str(error)
        }), 500

    distancia_km = distancia_metros / 1000
    duracion_minutos = duracion_segundos / 60

    if duracion_minutos >= 60:
        duracion_texto = f"{int(duracion_minutos // 60)}h {int(duracion_minutos % 60)}min"
    else:
        duracion_texto = f"{round(duracion_minutos)} min"

    origen_tz = zona_horaria_por_longitud(origen_coord[1])
    destino_tz = zona_horaria_por_longitud(destino_coord[1])
    origen_hora = hora_local_por_offset(origen_tz)
    destino_hora = hora_local_por_offset(destino_tz)

    capacidad_tanque = 50
    rendimiento = obtener_rendimiento_por_vehiculo(
        vehiculo, rendimiento_personalizado
    )
    litros = distancia_km / rendimiento
    rango_km = rendimiento * capacidad_tanque

    if litros > capacidad_tanque:
        alerta_gasolina = "Advertencia: la ruta supera la autonomía con un tanque completo. Carga gasolina antes de salir."
    elif distancia_km > rango_km * 0.75:
        alerta_gasolina = "Atención: la ruta consume más del 75% de tu tanque. Considera una parada extra."
    else:
        alerta_gasolina = "Autonomía suficiente para la ruta planificada."

    alternativas = []
    for idx, ruta in enumerate(rutas_osm[:3], start=1):
        alternativas.append({
            "nombre": f"Alternativa {idx}",
            "distancia_km": round(ruta["distance"] / 1000, 2),
            "duracion_minutos": int(ruta["duration"] / 60),
            "tiene_caseta": ruta.get("tiene_caseta", False),
            "peaje_estimado": ruta.get("peaje_estimado", 0),
            "puntos": [[p[0], p[1]] for p in ruta["geometry"]]
        })

    return jsonify({
        "origen": origen,
        "destino": destino,
        "origen_direccion": origen_direccion,
        "destino_direccion": destino_direccion,
        "origen_coord": origen_coord,
        "destino_coord": destino_coord,
        "coordenadas": coordenadas,
        "distancia_metros": distancia_metros,
        "distancia_km": round(distancia_km, 2),
        "duracion_minutos": round(duracion_minutos),
        "duracion_texto": duracion_texto,
        "metodo": algoritmo.title().replace("_", " "),
        "zona_horaria_origen": origen_tz,
        "zona_horaria_destino": destino_tz,
        "hora_local_origen": origen_hora,
        "hora_local_destino": destino_hora,
        "zonas_rojas": zonas_rojas,
        "costo_peaje": round(costo_peaje, 2),
        "peajes_detectados": peajes_detectados,
        "alerta_gasolina": alerta_gasolina,
        "rutas_alternas": alternativas
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
