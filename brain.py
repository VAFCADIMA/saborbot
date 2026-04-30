"""
brain.py - Cerebro de SaborBot
================================
Máquina de estados que controla el agente de ventas por WhatsApp.
Recibe texto transcrito desde el webhook de WhatsApp y devuelve
la respuesta que luego se convertirá a voz.

Autor: Superagente IA
Versión: 1.0
"""

import json
import re
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any

# =============================================================================
# 1. BASE DE DATOS DE PRODUCTOS (La única verdad)
# =============================================================================
PRODUCTOS = {
    "pulpa": {
        "copozu": {"tamaño": "estándar", "precio": 25, "sku": "PUL-COP-001"},
        "camucamu": {"tamaño": "estándar", "precio": 25, "sku": "PUL-CAM-001"},
        "guayaba": {"tamaño": "estándar", "precio": 25, "sku": "PUL-GUA-001"},
        "frutilla": {"tamaño": "estándar", "precio": 25, "sku": "PUL-FRU-001"},
        "noni": {"tamaño": "estándar", "precio": 25, "sku": "PUL-NON-001"},
    },
    "jugo": {
        "copozu": {
            "1_litro": {"precio": 10, "sku": "JUG-COP-1L"},
            "2_litros": {"precio": 15, "sku": "JUG-COP-2L"},
            "3_litros": {"precio": 20, "sku": "JUG-COP-3L"},
        },
        "camucamu": {
            "1_litro": {"precio": 10, "sku": "JUG-CAM-1L"},
            "2_litros": {"precio": 15, "sku": "JUG-CAM-2L"},
            "3_litros": {"precio": 20, "sku": "JUG-CAM-3L"},
        },
        "guayaba": {
            "1_litro": {"precio": 10, "sku": "JUG-GUA-1L"},
            "2_litros": {"precio": 15, "sku": "JUG-GUA-2L"},
            "3_litros": {"precio": 20, "sku": "JUG-GUA-3L"},
        },
        "frutilla": {
            "1_litro": {"precio": 10, "sku": "JUG-FRU-1L"},
            "2_litros": {"precio": 15, "sku": "JUG-FRU-2L"},
            "3_litros": {"precio": 20, "sku": "JUG-FRU-3L"},
        },
        "noni": {
            "1_litro": {"precio": 10, "sku": "JUG-NON-1L"},
            "2_litros": {"precio": 15, "sku": "JUG-NON-2L"},
            "3_litros": {"precio": 20, "sku": "JUG-NON-3L"},
        },
    },
    "helado": {
        "copozu": {
            "150g": {"precio": 5, "sku": "HEL-COP-150"},
            "500g": {"precio": 22, "sku": "HEL-COP-500"},
            "1000g": {"precio": 38, "sku": "HEL-COP-1000"},
        },
        "camucamu": {
            "150g": {"precio": 5, "sku": "HEL-CAM-150"},
            "500g": {"precio": 22, "sku": "HEL-CAM-500"},
            "1000g": {"precio": 38, "sku": "HEL-CAM-1000"},
        },
        "guayaba": {
            "150g": {"precio": 5, "sku": "HEL-GUA-150"},
            "500g": {"precio": 22, "sku": "HEL-GUA-500"},
            "1000g": {"precio": 38, "sku": "HEL-GUA-1000"},
        },
        "frutilla": {
            "150g": {"precio": 5, "sku": "HEL-FRU-150"},
            "500g": {"precio": 22, "sku": "HEL-FRU-500"},
            "1000g": {"precio": 38, "sku": "HEL-FRU-1000"},
        },
        "noni": {
            "150g": {"precio": 5, "sku": "HEL-NON-150"},
            "500g": {"precio": 22, "sku": "HEL-NON-500"},
            "1000g": {"precio": 38, "sku": "HEL-NON-1000"},
        },
    },
}

# =============================================================================
# 2. ESTADOS DE LA CONVERSACIÓN
# =============================================================================
class Estado(Enum):
    SALUDO = "saludo"
    CONSULTA = "consulta"
    TOMAR_PEDIDO = "tomar_pedido"
    ESPERANDO_CONFIRMACION = "esperando_confirmacion"
    PEDIDO_CONFIRMADO = "pedido_confirmado"
    CANCELAR = "cancelar"

# =============================================================================
# 3. CLASE PRINCIPAL: EL CEREBRO
# =============================================================================
class SaborBotBrain:
    """
    Controla toda la lógica del agente SaborBot.
    Cada conversación por WhatsApp debe tener su propia instancia.
    """

    def __init__(self, numero_cliente: str):
        self.numero_cliente = numero_cliente
        self.estado: Estado = Estado.SALUDO
        self.pedido_actual: List[Dict[str, Any]] = []
        self.pedido_pendiente_confirmacion: Optional[List[Dict[str, Any]]] = None
        self.nombre_cliente: Optional[str] = None

    # -------------------------------------------------------------------------
    # 3.1 Punto de entrada: recibe texto transcrito, devuelve respuesta
    # -------------------------------------------------------------------------
    def procesar_mensaje(self, texto: str) -> str:
        """Procesa el mensaje del cliente y devuelve la respuesta de SaborBot."""
        texto = texto.lower().strip()

        # Detección de cancelación
        if any(p in texto for p in ["cancela", "anula", "ya no quiero", "olvídalo"]):
            return self._cancelar_pedido()

        # Máquina de estados
        if self.estado == Estado.SALUDO:
            return self._estado_saludo(texto)
        elif self.estado == Estado.CONSULTA:
            return self._estado_consulta(texto)
        elif self.estado == Estado.TOMAR_PEDIDO:
            return self._estado_tomar_pedido(texto)
        elif self.estado == Estado.ESPERANDO_CONFIRMACION:
            return self._estado_confirmacion(texto)
        elif self.estado == Estado.PEDIDO_CONFIRMADO:
            return self._estado_resolver(texto)
        else:
            return "¡Hola! Soy SaborBot. ¿En qué puedo ayudarte? 🍹🍦"

    # -------------------------------------------------------------------------
    # 3.2 ESTADO: SALUDO
    # -------------------------------------------------------------------------
    def _estado_saludo(self, texto: str) -> str:
        """Primer contacto. Detecta intención y transiciona."""
        if any(p in texto for p in ["precio", "cuánto cuesta", "cuánto vale"]):
            self.estado = Estado.CONSULTA
            return self._consultar_precio(texto)

        if any(p in texto for p in ["qué tienes", "sabores", "productos", "catálogo"]):
            self.estado = Estado.CONSULTA
            return self._mostrar_catalogo()

        if any(p in texto for p in ["pedir", "encargar", "reservar", "comprar", "dame", "quiero", "me das", "un", "una"]):
            self.estado = Estado.TOMAR_PEDIDO
            return self._iniciar_pedido(texto)

        # Si no detecta intención clara
        return (
            "¡Hola! Soy SaborBot, el asistente de Jugos, Helados & Pulpas 🍹🍦\n\n"
            "Puedes:\n"
            "• Hacer un pedido (jugos, helados, pulpas)\n"
            "• Preguntar precios o sabores\n"
            "• Consultar el catálogo\n\n"
            "¿En qué te ayudo hoy?"
        )

    # -------------------------------------------------------------------------
    # 3.3 ESTADO: CONSULTA
    # -------------------------------------------------------------------------
    def _estado_consulta(self, texto: str) -> str:
        """Responde consultas de productos y precios."""
        if any(p in texto for p in ["precio", "cuánto cuesta", "cuánto vale"]):
            respuesta = self._consultar_precio(texto)
        else:
            respuesta = self._mostrar_catalogo()

        respuesta += "\n\n¿Quieres hacer un pedido o necesitas algo más?"
        self.estado = Estado.SALUDO
        return respuesta

    def _consultar_precio(self, texto: str) -> str:
        """Busca precios según lo que pregunte el cliente."""
        tipo_detectado = None
        sabor_detectado = None
        tamaño_detectado = None

        if "pulpa" in texto:
            tipo_detectado = "pulpa"
        elif "jugo" in texto:
            tipo_detectado = "jugo"
        elif "helado" in texto:
            tipo_detectado = "helado"

        for sabor in ["copozu", "camucamu", "guayaba", "frutilla", "noni"]:
            if sabor in texto:
                sabor_detectado = sabor
                break

        if "1 litro" in texto or "un litro" in texto:
            tamaño_detectado = "1_litro"
        elif "2 litros" in texto or "dos litros" in texto:
            tamaño_detectado = "2_litros"
        elif "3 litros" in texto or "tres litros" in texto:
            tamaño_detectado = "3_litros"
        elif "150" in texto:
            tamaño_detectado = "150g"
        elif "500" in texto:
            tamaño_detectado = "500g"
        elif "1000" in texto or "1 kilo" in texto:
            tamaño_detectado = "1000g"

        # Caso: pregunta por todos los precios de un tipo
        if tipo_detectado and not sabor_detectado:
            return self._precios_por_tipo(tipo_detectado)

        # Caso: pregunta por un producto específico
        if tipo_detectado and sabor_detectado:
            if tipo_detectado == "pulpa":
                return f"La pulpa de {sabor_detectado} cuesta 25 Bs. ¡Rendidora y deliciosa! 😋"
            elif tamaño_detectado:
                try:
                    precio = PRODUCTOS[tipo_detectado][sabor_detectado][tamaño_detectado]["precio"]
                    return f"El {tipo_detectado} de {sabor_detectado} de {tamaño_detectado.replace('_', ' ')} cuesta {precio} Bs. 🍹"
                except KeyError:
                    return f"Lo siento, no tengo {tipo_detectado} de {sabor_detectado} en ese tamaño. ¿Te ayudo con otra cosa?"
            else:
                return self._precios_por_sabor(tipo_detectado, sabor_detectado)

        return "Tengo pulpas (25 Bs), jugos (10/15/20 Bs según litros) y helados (5/22/38 Bs según tamaño). ¿Sobre cuál quieres más info?"

    def _precios_por_tipo(self, tipo: str) -> str:
        """Devuelve todos los precios de un tipo de producto."""
        if tipo == "pulpa":
            return "Todas las pulpas cuestan 25 Bs. Sabores: copozu, camucamu, guayaba, frutilla y noni."
        elif tipo == "jugo":
            return "Los jugos: 1 litro = 10 Bs, 2 litros = 15 Bs, 3 litros = 20 Bs. Sabores: copozu, camucamu, guayaba, frutilla y noni."
        elif tipo == "helado":
            return "Los helados: 150g = 5 Bs, 500g = 22 Bs, 1000g = 38 Bs. Sabores: copozu, camucamu, guayaba, frutilla y noni."
        return "No entendí. ¿Pulpas, jugos o helados?"

    def _precios_por_sabor(self, tipo: str, sabor: str) -> str:
        """Devuelve los precios de un sabor específico."""
        if tipo == "pulpa":
            return f"Pulpa de {sabor}: 25 Bs."
        elif tipo == "jugo":
            return f"Jugo de {sabor}: 1L = 10 Bs, 2L = 15 Bs, 3L = 20 Bs."
        elif tipo == "helado":
            return f"Helado de {sabor}: 150g = 5 Bs, 500g = 22 Bs, 1000g = 38 Bs."
        return "No tengo ese producto."

    def _mostrar_catalogo(self) -> str:
        """Muestra el catálogo completo resumido."""
        return (
            "📋 CATÁLOGO Jugos, Helados & Pulpas:\n\n"
            "🍈 PULPAS (25 Bs c/u): copozu, camucamu, guayaba, frutilla, noni\n\n"
            "🍹 JUGOS: 1L=10 Bs | 2L=15 Bs | 3L=20 Bs\n"
            "Sabores: copozu, camucamu, guayaba, frutilla, noni\n\n"
            "🍦 HELADOS: 150g=5 Bs | 500g=22 Bs | 1000g=38 Bs\n"
            "Sabores: copozu, camucamu, guayaba, frutilla, noni\n\n"
            "¿Qué se te antoja?"
        )

    # -------------------------------------------------------------------------
    # 3.4 ESTADO: TOMAR PEDIDO
    # -------------------------------------------------------------------------
    def _iniciar_pedido(self, texto: str) -> str:
        """Inicia la construcción del pedido a partir del primer mensaje."""
        items = self._extraer_items(texto)

        if items:
            self.pedido_actual.extend(items)
            return self._formatear_pedido_parcial()
        else:
            return "¡Claro! ¿Qué producto te gustaría? ¿Pulpa, jugo o helado? Y ¿de qué sabor? Tenemos: copozu, camucamu, guayaba, frutilla y noni. 😋"

    def _estado_tomar_pedido(self, texto: str) -> str:
        """Continúa construyendo el pedido."""
        # Si el cliente quiere cerrar
        if any(p in texto for p in ["es todo", "nada más", "solo eso", "eso es", "listo"]):
            return self._solicitar_confirmacion()

        # Si pide algo más
        items = self._extraer_items(texto)
        if items:
            self.pedido_actual.extend(items)
            return self._formatear_pedido_parcial() + "\n\n¿Algo más o cerramos el pedido?"
        else:
            return "No entendí bien. Dime: ¿pulpa, jugo o helado? ¿De qué sabor y tamaño? ¡Así te lo anoto rapidito! ✍️"

    def _extraer_items(self, texto: str) -> List[Dict[str, Any]]:
        """
        Extrae items del pedido desde texto libre.
        Busca patrones como: '2 pulpas de noni', 'jugo de guayaba 2 litros', etc.
        """
        items = []
        texto = texto.lower()

        # Detectar tipo
        tipos_detectados = []
        if "pulpa" in texto:
            tipos_detectados.append("pulpa")
        if "jugo" in texto:
            tipos_detectados.append("jugo")
        if "helado" in texto:
            tipos_detectados.append("helado")

        if not tipos_detectados:
            return []

        for tipo in tipos_detectados:
            # Buscar cantidad
            cantidad = 1
            match_cant = re.search(r'(\d+)\s*(?:pulpas|jugos|helados|de)', texto)
            if not match_cant:
                match_cant = re.search(r'(\d+)\s*(?=' + tipo + r')', texto)
            if match_cant:
                cantidad = int(match_cant.group(1))

            # Buscar sabor
            sabor = None
            for s in ["copozu", "camucamu", "guayaba", "frutilla", "noni"]:
                if s in texto:
                    sabor = s
                    break

            # Buscar tamaño
            tamaño = None
            if tipo == "jugo":
                if "1 litro" in texto or "un litro" in texto:
                    tamaño = "1_litro"
                elif "2 litros" in texto or "dos litros" in texto:
                    tamaño = "2_litros"
                elif "3 litros" in texto or "tres litros" in texto:
                    tamaño = "3_litros"
                else:
                    tamaño = "1_litro"  # default si no especifica
            elif tipo == "helado":
                if "150" in texto:
                    tamaño = "150g"
                elif "500" in texto:
                    tamaño = "500g"
                elif "1000" in texto or "1 kilo" in texto or "kilo" in texto:
                    tamaño = "1000g"
                else:
                    tamaño = "150g"  # default
            elif tipo == "pulpa":
                tamaño = "estándar"

            if sabor and tamaño:
                try:
                    precio_unitario = PRODUCTOS[tipo][sabor][tamaño]["precio"]
                    sku = PRODUCTOS[tipo][sabor][tamaño]["sku"]
                    items.append({
                        "tipo": tipo,
                        "sabor": sabor,
                        "tamaño": tamaño,
                        "cantidad": cantidad,
                        "precio_unitario": precio_unitario,
                        "subtotal": precio_unitario * cantidad,
                        "sku": sku,
                    })
                except KeyError:
                    continue

        return items

    def _formatear_pedido_parcial(self) -> str:
        """Formatea el pedido actual para mostrarlo al cliente."""
        if not self.pedido_actual:
            return "Todavía no has pedido nada. ¿Qué se te antoja?"

        lineas = ["📝 Tu pedido hasta ahora:"]
        total = 0
        for item in self.pedido_actual:
            tamaño_legible = item["tamaño"].replace("_", " ")
            lineas.append(
                f"  • {item['cantidad']}x {item['tipo']} de {item['sabor']} "
                f"({tamaño_legible}) = {item['subtotal']} Bs"
            )
            total += item["subtotal"]
        lineas.append(f"\n💰 Total parcial: {total} Bs")
        return "\n".join(lineas)

    def _solicitar_confirmacion(self) -> str:
        """Muestra el pedido completo y pide confirmación."""
        if not self.pedido_actual:
            self.estado = Estado.SALUDO
            return "No tengo ningún pedido anotado. ¿Querías pedir algo?"

        self.pedido_pendiente_confirmacion = self.pedido_actual.copy()
        self.estado = Estado.ESPERANDO_CONFIRMACION

        lineas = ["✅ A ver, confírmame por favor:"]
        total = 0
        for item in self.pedido_actual:
            tamaño_legible = item["tamaño"].replace("_", " ")
            lineas.append(
                f"  • {item['cantidad']}x {item['tipo']} de {item['sabor']} "
                f"({tamaño_legible}) = {item['subtotal']} Bs"
            )
            total += item["subtotal"]
        lineas.append(f"\n💵 TOTAL: {total} Bs")
        lineas.append("\n¿Todo bien? ¿Confirmamos el pedido? (Responde 'sí' o 'no')")

        return "\n".join(lineas)

    # -------------------------------------------------------------------------
    # 3.5 ESTADO: ESPERANDO CONFIRMACIÓN
    # -------------------------------------------------------------------------
    def _estado_confirmacion(self, texto: str) -> str:
        """Espera un sí o no para confirmar el pedido."""
        if any(p in texto for p in ["sí", "si", "ok", "dale", "confirmado", "bien", "perfecto", "de acuerdo"]):
            return self._confirmar_pedido()
        elif any(p in texto for p in ["no", "mal", "equivocado", "cambiar"]):
            self.estado = Estado.TOMAR_PEDIDO
            self.pedido_actual = []
            return "Entendido, empecemos de nuevo. Dime qué quieres pedir: ¿pulpa, jugo o helado? ¿De qué sabor?"
        else:
            return "Perdona, necesito un 'sí' o 'no' para continuar. ¿Confirmamos el pedido que te mostré?"

    def _confirmar_pedido(self) -> str:
        """Registra el pedido y notifica al dueño."""
        self.estado = Estado.PEDIDO_CONFIRMADO

        # Aquí iría la llamada a la API de Google Sheets o BD
        self._registrar_venta()

        total = sum(item["subtotal"] for item in self.pedido_actual)

        respuesta = (
            f"🎉 ¡Pedido confirmado!\n"
            f"💰 Total: {total} Bs\n\n"
        )

        if not self.nombre_cliente:
            respuesta += "¿A nombre de quién lo registro? 👤"
        else:
            respuesta += (
                f"Registrado a nombre de {self.nombre_cliente}.\n"
                f"Gracias por tu compra. ¡Que lo disfrutes mucho! 🧡🍹🍦"
            )
            self._enviar_notificacion_dueno()

        return respuesta

    def _registrar_venta(self):
        """
        Guarda la venta en la base de datos.
        TODO: Integrar con Google Sheets API o base de datos real.
        Por ahora imprime en consola.
        """
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = sum(item["subtotal"] for item in self.pedido_actual)
        items_str = ", ".join(
            f"{item['cantidad']}x {item['tipo']} {item['sabor']} ({item['tamaño']})"
            for item in self.pedido_actual
        )

        venta = {
            "fecha": fecha,
            "cliente": self.nombre_cliente or "Sin nombre",
            "telefono": self.numero_cliente,
            "items": self.pedido_actual,
            "total": total,
            "resumen": items_str,
        }

        print(f"[VENTA REGISTRADA] {json.dumps(venta, ensure_ascii=False, indent=2)}")
        # Aquí luego pegaremos el código de Google Sheets

    def _enviar_notificacion_dueno(self):
        """
        Envía notificación al dueño del negocio.
        TODO: Integrar con WhatsApp Business API o SMS.
        """
        total = sum(item["subtotal"] for item in self.pedido_actual)
        items_str = ", ".join(
            f"{item['cantidad']}x {item['tipo']} {item['sabor']}"
            for item in self.pedido_actual
        )
        mensaje = (
            f"🔔 NUEVA VENTA\n"
            f"Cliente: {self.nombre_cliente or 'Sin nombre'}\n"
            f"Teléfono: {self.numero_cliente}\n"
            f"Pedido: {items_str}\n"
            f"Total: {total} Bs"
        )
        print(f"[NOTIFICACIÓN DUEÑO] {mensaje}")

    # -------------------------------------------------------------------------
    # 3.6 ESTADO: PEDIDO CONFIRMADO
    # -------------------------------------------------------------------------
    def _estado_resolver(self, texto: str) -> str:
        """Resuelve datos pendientes post-confirmación (nombre, etc.)."""
        if not self.nombre_cliente:
            self.nombre_cliente = texto.strip().title()
            self._registrar_venta()
            self._enviar_notificacion_dueno()
            return (
                f"¡Gracias, {self.nombre_cliente}! Tu pedido está registrado.\n"
                f"Que disfrutes tus productos. ¡Hasta pronto! 🧡🍹🍦"
            )
        return "¿Necesitas algo más? Si no, ¡que tengas un excelente día! ☀️"

    # -------------------------------------------------------------------------
    # 3.7 CANCELACIÓN
    # -------------------------------------------------------------------------
    def _cancelar_pedido(self) -> str:
        """Cancela el pedido actual."""
        self.pedido_actual = []
        self.pedido_pendiente_confirmacion = None
        self.estado = Estado.SALUDO
        return "Entendido, he cancelado tu pedido. Si cambias de opinión, aquí estoy. ¡Buen día! 👋"


# =============================================================================
# 4. SIMULACIÓN PARA PRUEBAS
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SIMULACIÓN DE SaborBot")
    print("=" * 60)

    bot = SaborBotBrain(numero_cliente="+59177777777")

    # Simulación de conversación
    conversacion = [
        "hola",
        "qué sabores de helado tienen",
        "dame 2 helados de copozu de 500g y una pulpa de noni",
        "cuánto cuesta el jugo de guayaba de 3 litros",
        "agrega uno de esos",
        "es todo",
        "sí",
        "Carlos Méndez",
    ]

    for msg in conversacion:
        print(f"\n👤 Cliente: '{msg}'")
        respuesta = bot.procesar_mensaje(msg)
        print(f"🤖 SaborBot: '{respuesta}'")
        print("-" * 40)

    print("\n✅ Simulación completada")