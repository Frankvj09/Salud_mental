# chatbot_xmpp.py - Versión CORREGIDA
import slixmpp
import asyncio
import re
import random
import requests
from datetime import datetime

class MentalHealthBot(slixmpp.ClientXMPP):
    """Chatbot XMPP para consultas simples de salud mental"""
    
    def __init__(self, jid, password):
        super().__init__(jid, password)
        
        # Configuración para 5222.de
        self.use_ssl = True
        
        # Respuestas del bot
        self.respuestas = {
            'saludo': [
                "¡Hola! Soy el asistente virtual de salud mental. ¿Cómo te sientes hoy?",
                "Hola, estoy aquí para escucharte. ¿Qué te preocupa?",
                "Bienvenido. Recuerda que no estás solo. ¿En qué puedo ayudarte?"
            ],
            'depresion': [
                "Entiendo que puedas sentirte así. ¿Has hablado con alguien sobre esto?",
                "La depresión es tratable. ¿Has considerado buscar ayuda profesional?",
                "Recuerda que tus sentimientos son válidos. ¿Quieres que te dé algunos consejos?"
            ],
            'ansiedad': [
                "La ansiedad puede ser abrumadora. Prueba respirar profundamente 5 veces.",
                "¿Has intentado técnicas de relajación como la respiración diafragmática?",
                "La ansiedad es una respuesta natural. ¿Qué situaciones la desencadenan?"
            ],
            'suicidio': [
                "⚠️ ALERTA CRÍTICA: Has mencionado algo muy importante. Por favor, llama a la línea de crisis: 0800-XXX-XXXX",
                "TU VIDA ES VALIOSA. No estás solo. Comunícate con la línea de emergencia: 911",
                "Necesitas ayuda inmediata. Por favor contacta a un profesional ahora mismo."
            ],
            'citas': [
                "Para agendar una cita con un psicólogo, inicia sesión en la plataforma y ve a 'Mis Citas'.",
                "¿Necesitas ayuda para agendar una cita? Puedo orientarte sobre cómo hacerlo en la web.",
                "Recuerda que las citas con psicólogos se gestionan desde tu panel de usuario."
            ],
            'consejos': [
                "¿Has intentado escribir cómo te sientes en un diario?",
                "El ejercicio ligero puede ayudar a mejorar tu estado de ánimo.",
                "Hablar con alguien de confianza siempre es un buen primer paso.",
                "Establecer pequeñas metas diarias puede ayudarte a sentirte mejor."
            ],
            'despedida': [
                "Cuídate mucho. Recuerda que siempre puedes volver a escribir.",
                "Estoy aquí cuando me necesites. ¡Cuídate!",
                "Espero haberte ayudado. No dudes en regresar si lo necesitas."
            ],
            'default': [
                "Gracias por compartir. ¿Puedes contarme más detalles?",
                "Estoy aquí para escucharte. Cuéntame más sobre cómo te sientes."
            ]
        }
        
        # Palabras clave de riesgo
        self.palabras_riesgo = ['suicidio', 'matarme', 'morir', 'acabar con todo', 'lastimarme', 'desaparecer']
        
        # URL de la API de Flask
        self.api_url = "http://localhost:5000/api/bot/alerta"
        
        # Eventos XMPP
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
    
    async def start(self, event):
        """Iniciar sesión XMPP"""
        self.send_presence()
        await self.get_roster()
        print(f"\n✅ ¡BOT CONECTADO EXITOSAMENTE!")
        print(f"🤖 ID: {self.boundjid}")
        print(f"📡 Servidor: 5222.de")
        print(f"💬 Esperando mensajes...\n")
    
    async def message(self, msg):
        """Procesar mensajes entrantes"""
        if msg['type'] in ('chat', 'normal'):
            usuario = msg['from'].bare
            mensaje = msg['body'].strip()
            
            print(f"\n📩 Mensaje de {usuario}: {mensaje}")
            
            # Verificar riesgo
            mensaje_lower = mensaje.lower()
            es_riesgo = any(p in mensaje_lower for p in self.palabras_riesgo)
            
            if es_riesgo:
                respuesta = random.choice(self.respuestas['suicidio'])
                self.send_message(mto=msg['from'], mbody=respuesta, mtype='chat')
                print(f"🚨 ALERTA CRÍTICA detectada")
                self.notificar_riesgo(usuario, mensaje)
                return
            
            # Clasificar mensaje
            if re.search(r'\b(hola|buenas|hey|saludos)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['saludo'])
            elif re.search(r'\b(depre|deprimido|triste|vacío)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['depresion'])
            elif re.search(r'\b(ansiedad|nervioso|miedo|pánico)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['ansiedad'])
            elif re.search(r'\b(cita|agendar|psicólogo)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['citas'])
            elif re.search(r'\b(consejo|ayuda|qué hago)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['consejos'])
            elif re.search(r'\b(gracias|chao|adiós)\b', mensaje_lower):
                respuesta = random.choice(self.respuestas['despedida'])
            else:
                respuesta = random.choice(self.respuestas['default'])
            
            self.send_message(mto=msg['from'], mbody=respuesta, mtype='chat')
            print(f"🤖 Respuesta: {respuesta[:80]}...")
    
    def notificar_riesgo(self, usuario, mensaje):
        """Notificar al sistema Flask sobre riesgo detectado"""
        try:
            import threading
            payload = {
                'usuario': usuario,
                'mensaje': mensaje,
                'timestamp': datetime.now().isoformat()
            }
            threading.Thread(target=self._enviar_notificacion, args=(payload,)).start()
        except Exception as e:
            print(f"⚠️ Error al notificar: {e}")
    
    def _enviar_notificacion(self, payload):
        """Enviar notificación a la API de Flask"""
        try:
            requests.post(self.api_url, json=payload, timeout=2)
            print(f"📢 Riesgo notificado al sistema principal")
        except:
            pass


def iniciar_bot():
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # ============================================================
    # ¡CONFIGURA AQUÍ TUS CREDENCIALES!
    # ============================================================
    USUARIO = "botsaludmental"  # El usuario que registraste (sin "mental" si no lo incluiste)
    SERVIDOR = "5222.de"
    CONTRASENA = "Fvj280992*"  # La contraseña que elegiste
    
    XMPP_JID = f"{USUARIO}@{SERVIDOR}"
    
    print("=" * 50)
    print("🚀 INICIANDO CHATBOT DE SALUD MENTAL")
    print("=" * 50)
    print(f"🤖 Bot: {XMPP_JID}")
    print(f"📡 Servidor: {SERVIDOR}")
    print("=" * 50)
    
    bot = MentalHealthBot(XMPP_JID, CONTRASENA)
    bot.register_plugin('xep_0030')
    bot.register_plugin('xep_0004')
    bot.register_plugin('xep_0060')
    bot.register_plugin('xep_0199')
    
    # Conectar y ejecutar - MÉTODO CORREGIDO
    if bot.connect():
        print("✅ Conectado al servidor")
        print("🤖 Bot funcionando...")
        # Usar loop asyncio en lugar de process()
        loop = asyncio.get_event_loop()
        loop.run_forever()
    else:
        print("❌ Error de conexión")


if __name__ == "__main__":
    iniciar_bot()