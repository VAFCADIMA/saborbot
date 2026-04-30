"""
main.py - Punto de entrada del servidor de SaborBot
Recibe mensajes de WhatsApp y responde usando brain.py
"""

from flask import Flask, request, jsonify
from brain import SaborBotBrain
from dotenv import load_dotenv
import os

# Cargar variables del archivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave-por-defecto")

# Diccionario para guardar la conversación de cada cliente
sesiones = {}

# Configuración del negocio desde .env
NOMBRE_NEGOCIO = os.getenv("NOMBRE_NEGOCIO", "Jugos, Helados & Pulpas")
TELEFONO_DUENO = os.getenv("TELEFONO_DUENO", "")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

@app.route("/")
def home():
    return f"🤖 SaborBot de {NOMBRE_NEGOCIO} está vivo y escuchando 24/7."

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    WhatsApp manda los mensajes aquí.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    numero = data.get("telefono", "desconocido")
    mensaje = data.get("mensaje", "")
    es_audio = data.get("audio", False)  # Para futuro soporte de voz

    # Si el mensaje viene como audio, aquí irá la transcripción
    # if es_audio:
    #     mensaje = transcribir_audio(data.get("audio_url"))

    # Cada número tiene su propio cerebro
    if numero not in sesiones:
        sesiones[numero] = SaborBotBrain(numero_cliente=numero)

    bot = sesiones[numero]
    respuesta = bot.procesar_mensaje(mensaje)

    # Aquí luego convertiremos la respuesta a audio si es necesario
    # if data.get("responder_con_audio"):
    #     audio_url = texto_a_voz(respuesta)
    #     return jsonify({"audio_url": audio_url})

    return jsonify({"respuesta": respuesta, "tipo": "texto"})

@app.route("/simular", methods=["GET"])
def simular():
    """
    Ruta para probar sin WhatsApp.
    Entra a: https://tu-app.railway.app/simular?texto=hola&tel=123
    """
    texto = request.args.get("texto", "")
    telefono = request.args.get("tel", "prueba")

    if not texto:
        return jsonify({"error": "Falta el parámetro 'texto'"}), 400

    if telefono not in sesiones:
        sesiones[telefono] = SaborBotBrain(numero_cliente=telefono)

    bot = sesiones[telefono]
    respuesta = bot.procesar_mensaje(texto)

    if DEBUG_MODE:
        print(f"\n{'='*50}")
        print(f"📱 Cliente: {telefono}")
        print(f"💬 Mensaje: {texto}")
        print(f"🤖 Respuesta: {respuesta}")
        print(f"📊 Estado: {bot.estado}")
        print(f"🛒 Pedido actual: {bot.pedido_actual}")
        print(f"{'='*50}\n")

    return jsonify({
        "cliente": telefono,
        "mensaje_recibido": texto,
        "respuesta_saborbot": respuesta,
        "estado": bot.estado.value,
        "pedido_actual": bot.pedido_actual
    })

@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar que el servidor está vivo."""
    return jsonify({
        "estado": "ok",
        "negocio": NOMBRE_NEGOCIO,
        "sesiones_activas": len(sesiones),
        "debug": DEBUG_MODE
    })

@app.route("/reset", methods=["POST"])
def reset():
    """
    Reinicia la conversación de un cliente (útil para pruebas).
    POST con JSON: {"telefono": "123"}
    """
    data = request.get_json()
    telefono = data.get("telefono", "")

    if telefono in sesiones:
        del sesiones[telefono]
        return jsonify({"mensaje": f"Sesión de {telefono} eliminada"})
    return jsonify({"mensaje": f"No había sesión activa para {telefono}"})


# =============================================================================
# INICIO DEL SERVIDOR
# =============================================================================
if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 5000))
    print(f"""
╔══════════════════════════════════════════════╗
║  🤖 SaborBot - {NOMBRE_NEGOCIO}
║  Servidor iniciado en puerto {puerto}
║  Simulador: http://localhost:{puerto}/simular?texto=hola
║  Health: http://localhost:{puerto}/health
╚══════════════════════════════════════════════╝
    """)
    app.run(debug=DEBUG_MODE, host="0.0.0.0", port=puerto)