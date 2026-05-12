from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import bcrypt
from datetime import datetime
import mysql.connector
import config
import os

app = Flask(__name__)
app.config.from_object(config.Config)

# Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Socket
socketio = SocketIO(app, cors_allowed_origins="*")

# CONEXIÓN BD
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

# USER MODEL
class User(UserMixin):
    def __init__(self, id, nombre, email, tipo_usuario):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.tipo_usuario = tipo_usuario

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return User(user['id'], user['nombre'], user['email'], user['tipo_usuario'])
    return None

# FORMULARIOS
class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar', validators=[EqualTo('password')])
    telefono = StringField('Teléfono')
    tipo_usuario = SelectField('Tipo', choices=[('usuario','Usuario'),('psicologo','Psicólogo'),('familiar','Familiar')])

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])

#  RUTAS
@app.route('/')
def index():
    return render_template('index.html')

# REGISTRO
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()

    if form.validate_on_submit():
        conn = get_db_connection()
        cur = conn.cursor()

        # Encriptar contraseña
        hashed = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())

        try:
            # 1. Insertar usuario
            cur.execute("""
                INSERT INTO usuarios (nombre, email, password_hash, telefono, tipo_usuario)
                VALUES (%s, %s, %s, %s, %s)
            """, (form.nombre.data, form.email.data, hashed, form.telefono.data, form.tipo_usuario.data))

            # 2. Obtener ID del usuario recién creado
            usuario_id = cur.lastrowid

            # 3. Si es psicólogo → insertarlo en tabla psicologos
            if form.tipo_usuario.data == 'psicologo':
                cur.execute("""
                    INSERT INTO psicologos (usuario_id, especialidad, disponibilidad)
                    VALUES (%s, %s, %s)
                """, (usuario_id, 'General', 'online'))

            # 4. Guardar todo
            conn.commit()

            flash('Registro exitoso', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            print("ERROR EN REGISTRO:", e)  # útil para debug
            flash('Error en registro', 'danger')

        finally:
            cur.close()
            conn.close()

    return render_template('registro.html', form=form)

#LOGIN (CORREGIDO)
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM usuarios WHERE email=%s", (form.email.data,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            stored_password = user['password_hash']

            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')

            if bcrypt.checkpw(form.password.data.encode('utf-8'), stored_password):
                login_user(User(user['id'], user['nombre'], user['email'], user['tipo_usuario']))
                return redirect(url_for('dashboard'))

        flash('Credenciales incorrectas', 'danger')

    return render_template('login.html', form=form)

# DASHBOARD

# Agregar después de @app.route('/dashboard') ---------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # Redirigir según el tipo de usuario
    if current_user.tipo_usuario == 'psicologo':
        return render_template('dashboard_psicologo.html')
    elif current_user.tipo_usuario == 'familiar':
        return render_template('dashboard_familiar.html')
    else:
        return render_template('dashboard.html')  # Usuario normal

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# DIRECTORIO
@app.route('/directorio_psicologos')
def directorio_psicologos():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT u.nombre, p.especialidad, p.descripcion, p.calificacion_promedio, 
               d.direccion_consulta, d.ciudad, d.modalidad
        FROM psicologos p
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN directorio_psicologos d ON p.id = d.psicologo_id
        WHERE u.tipo_usuario = 'psicologo'
    """)
    psicologos = cur.fetchall()
    cur.close()
    
    return render_template('directoriopsicologos.html', psicologos=psicologos)

# CHAT
@app.route('/chat')
@login_required
def chat():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT p.id, u.nombre, p.especialidad
            FROM psicologos p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.disponibilidad IS NOT NULL
        """)

        psicologos = cur.fetchall()

    except Exception as e:
        print("ERROR EN CHAT:", e)
        psicologos = []

    finally:
        cur.close()
        conn.close()

    return render_template('chat.html', psicologos=psicologos)


# ==================== CHAT - FUNCIONES CORREGIDAS ====================

# INICIAR CHAT (Usuario normal inicia chat con psicólogo)
@app.route('/iniciar_chat/<int:psicologo_id>')
@login_required
def iniciar_chat(psicologo_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Crear nueva conversación
        cur.execute("""
            INSERT INTO conversaciones_chat (usuario_id, psicologo_id, estado) 
            VALUES (%s, %s, 'pendiente')
        """, (current_user.id, psicologo_id))

        conn.commit()
        conversacion_id = cur.lastrowid

    except Exception as e:
        conn.rollback()
        print("ERROR AL INICIAR CHAT:", e)
        flash('Error al iniciar el chat', 'danger')
        return redirect(url_for('chat'))

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('conversacion', conversacion_id=conversacion_id))


# VER CONVERSACIÓN (Tanto para usuario como para psicólogo)
@app.route('/conversacion/<int:conversacion_id>')
@login_required
def conversacion(conversacion_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Validar acceso a la conversación (usuario O psicólogo)
        cur.execute("""
            SELECT * FROM conversaciones_chat 
            WHERE id = %s AND (
                usuario_id = %s OR 
                psicologo_id IN (
                    SELECT id FROM psicologos WHERE usuario_id = %s
                )
            )
        """, (conversacion_id, current_user.id, current_user.id))

        conversacion = cur.fetchone()

        if not conversacion:
            flash('No tienes acceso a esta conversación', 'danger')
            # Redirigir según el rol
            if current_user.tipo_usuario == 'psicologo':
                return redirect(url_for('psicologo_chats'))
            else:
                return redirect(url_for('chat'))

        # Obtener mensajes
        cur.execute("""
            SELECT m.*, u.nombre as remitente_nombre 
            FROM mensajes_chat m 
            JOIN usuarios u ON m.remitente_id = u.id 
            WHERE m.conversacion_id = %s 
            ORDER BY m.fecha_envio ASC
        """, (conversacion_id,))

        mensajes = cur.fetchall()
        
        # Actualizar estado de la conversación a 'activa' si es la primera vez
        if conversacion['estado'] == 'pendiente':
            cur.execute("""
                UPDATE conversaciones_chat SET estado = 'activa' WHERE id = %s
            """, (conversacion_id,))
            conn.commit()

    except Exception as e:
        print("ERROR EN CONVERSACION:", e)
        flash('Error al cargar la conversación', 'danger')
        if current_user.tipo_usuario == 'psicologo':
            return redirect(url_for('psicologo_chats'))
        else:
            return redirect(url_for('chat'))

    finally:
        cur.close()
        conn.close()

    return render_template(
        'conversacion.html',
        conversacion_id=conversacion_id,
        mensajes=mensajes
    )


# CHATS DEL PSICÓLOGO (Lista de todas sus conversaciones)
@app.route('/psicologo/chats')
@login_required
def psicologo_chats():
    # Verificar que el usuario sea psicólogo
    if current_user.tipo_usuario != 'psicologo':
        flash('No tienes acceso a esta página', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute("""
            SELECT 
                c.id, 
                u.nombre as usuario_nombre, 
                c.estado, 
                DATE_FORMAT(c.fecha_inicio, '%d/%m/%Y %H:%i') as fecha_inicio,
                (SELECT mensaje FROM mensajes_chat 
                 WHERE conversacion_id = c.id 
                 ORDER BY fecha_envio DESC LIMIT 1) as ultimo_mensaje,
                (SELECT DATE_FORMAT(fecha_envio, '%d/%m/%Y %H:%i') FROM mensajes_chat 
                 WHERE conversacion_id = c.id 
                 ORDER BY fecha_envio DESC LIMIT 1) as ultimo_mensaje_fecha,
                (SELECT COUNT(*) FROM mensajes_chat 
                 WHERE conversacion_id = c.id AND leido = FALSE AND remitente_id != %s) as no_leidos
            FROM conversaciones_chat c
            JOIN usuarios u ON c.usuario_id = u.id
            WHERE c.psicologo_id = (SELECT id FROM psicologos WHERE usuario_id = %s)
            ORDER BY 
                CASE c.estado 
                    WHEN 'activa' THEN 1 
                    ELSE 2 
                END,
                c.fecha_inicio DESC
        """, (current_user.id, current_user.id))
        
        conversaciones = cur.fetchall()
        
    except Exception as e:
        print("ERROR EN PSICOLOGO_CHATS:", e)
        conversaciones = []
        flash('Error al cargar las conversaciones', 'danger')
        
    finally:
        cur.close()
        conn.close()
    
    return render_template('psicologo_chats.html', conversaciones=conversaciones)

# __________________________________WebSocket para chat en tiempo real________________________________________________
@socketio.on('join')
def on_join(data):
    room = data['conversacion_id']
    join_room(room)
    emit('status', {'msg': f'{current_user.nombre} se ha unido al chat'}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['conversacion_id']
    leave_room(room)
    emit('status', {'msg': f'{current_user.nombre} ha abandonado el chat'}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['conversacion_id']
    mensaje = data['message']
    
    # Guardar mensaje en base de datos
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        INSERT INTO mensajes_chat (conversacion_id, remitente_id, mensaje) 
        VALUES (%s, %s, %s)
    """, (room, current_user.id, mensaje))
    conn.commit()
    cur.close()
    
    # ________________________________________Verificar palabras clave para alertas______________________________________
    verificar_palabras_clave(current_user.id, mensaje)
    
    # Emitir mensaje
    emit('message', {
        'user': current_user.nombre,
        'message': mensaje,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=room)

def verificar_palabras_clave(usuario_id, mensaje):
    palabras_alerta = ['suicidio', 'matarme', 'morir', 'lastimarme', 'adiós', 'acabar con todo']
    mensaje_lower = mensaje.lower()
    
    for palabra in palabras_alerta:
        if palabra in mensaje_lower:
            # ______________________________Generar alerta para familiares_________________________________________________________-
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                INSERT INTO alertas (usuario_id, tipo_alerta, nivel_alerta, mensaje, estado)
                VALUES (%s, 'palabras_clave', 'urgente', %s, 'activa')
            """, (usuario_id, f'Se detectó la palabra clave: {palabra}'))
            conn.commit()
            cur.close()
            break
    
@app.route('/perfil')
@login_required
def perfil():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (current_user.id,))
    usuario = cur.fetchone()
    
    # Si es psicólogo, obtener información adicional
    if current_user.tipo_usuario == 'psicologo':
        cur.execute("""
            SELECT p.*, d.* 
            FROM psicologos p
            LEFT JOIN directorio_psicologos d ON p.id = d.psicologo_id
            WHERE p.usuario_id = %s
        """, (current_user.id,))
        info_psicologo = cur.fetchone()
    else:
        info_psicologo = None
    
    cur.close()
    
    return render_template('perfil.html', usuario=usuario, info_psicologo=info_psicologo)
@app.route('/contactos_emergencia')
@login_required
def contactos_emergencia():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM contactos_emergencia 
        WHERE usuario_id = %s 
        ORDER BY orden_prioridad
    """, (current_user.id,))
    contactos = cur.fetchall()
    cur.close()
    
    return render_template('contactos_emergencia.html', contactos=contactos)

@app.route('/api/psicologos_disponibles')
def api_psicologos_disponibles():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, u.nombre, p.especialidad 
        FROM psicologos p 
        JOIN usuarios u ON p.usuario_id = u.id 
        WHERE p.disponibilidad IS NOT NULL
    """)
    psicologos = cur.fetchall()
    cur.close()
    
    return jsonify(psicologos)

@app.route('/alertas')
@login_required
def alertas():
    # Solo familiares y psicólogos pueden ver alertas
    if current_user.tipo_usuario not in ['familiar', 'psicologo']:
        flash('No tienes permiso para ver esta página', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    if current_user.tipo_usuario == 'familiar':
        cur.execute("""
            SELECT a.*, u.nombre as usuario_nombre 
            FROM alertas a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.familiar_id = %s OR a.familiar_id IS NULL
            ORDER BY a.fecha_generacion DESC
        """, (current_user.id,))
    else:  # psicologo
        cur.execute("""
            SELECT a.*, u.nombre as usuario_nombre 
            FROM alertas a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.estado = 'activa'
            ORDER BY 
                CASE a.nivel_alerta
                    WHEN 'urgente' THEN 1
                    WHEN 'precaucion' THEN 2
                    ELSE 3
                END,
                a.fecha_generacion DESC
        """)
    
    alertas_list = cur.fetchall()
    cur.close()
    
    return render_template('alertas.html', alertas=alertas_list)

@app.route('/atender_alerta/<int:alerta_id>', methods=['POST'])
@login_required
def atender_alerta(alerta_id):
    if current_user.tipo_usuario not in ['familiar', 'psicologo']:
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        UPDATE alertas 
        SET estado = 'atendida', fecha_atencion = NOW() 
        WHERE id = %s
    """, (alerta_id,))
    conn.commit()
    cur.close()
    
    return jsonify({'success': True})

# TEST
@app.route('/test')
@login_required
def test():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tests_salud")
    tests = cur.fetchall()
    cur.close()
    
    return render_template('test.html', tests=tests)

@app.route('/realizar_test/<int:test_id>')
@login_required
def realizar_test(test_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    # Obtener información del test
    cur.execute("SELECT * FROM tests_salud WHERE id = %s", (test_id,))
    test = cur.fetchone()
    
    # Obtener preguntas del test
    cur.execute("SELECT * FROM preguntas_test WHERE test_id = %s ORDER BY id", (test_id,))
    preguntas = cur.fetchall()
    
    cur.close()
    
    return render_template('realizar_test.html', test=test, preguntas=preguntas)

@app.route('/enviar_test', methods=['POST'])
@login_required
def enviar_test():
    test_id = request.form.get('test_id')
    respuestas = {}
    puntuacion_total = 0
    
    # Calcular puntuación (simplificado)
    for key, value in request.form.items():
        if key.startswith('pregunta_'):
            puntuacion_total += int(value)
            respuestas[key] = value
    
    # Determinar nivel de riesgo
    if puntuacion_total < 10:
        nivel_riesgo = 'bajo'
        recomendaciones = 'Tu puntuación indica un nivel bajo de síntomas. Mantén hábitos saludables.'
    elif puntuacion_total < 20:
        nivel_riesgo = 'moderado'
        recomendaciones = 'Considera hablar con un profesional de salud mental para una evaluación más detallada.'
    else:
        nivel_riesgo = 'alto'
        recomendaciones = 'Te recomendamos buscar ayuda profesional inmediatamente. Hay personas dispuestas a ayudarte.'
        
        # Generar alerta para familiares si el riesgo es alto
        generar_alerta_alto_riesgo(current_user.id)
    
    # Guardar resultado
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        INSERT INTO resultados_test (usuario_id, test_id, puntuacion_total, nivel_riesgo, recomendaciones)
        VALUES (%s, %s, %s, %s, %s)
    """, (current_user.id, test_id, puntuacion_total, nivel_riesgo, recomendaciones))
    conn.commit()
    cur.close()
    
    flash('Test completado. Revisa los resultados.', 'success')
    return redirect(url_for('resultados_test'))

def generar_alerta_alto_riesgo(usuario_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        INSERT INTO alertas (usuario_id, tipo_alerta, nivel_alerta, mensaje, estado)
        VALUES (%s, 'test_alto_riesgo', 'urgente', 
                'El usuario ha obtenido un resultado de alto riesgo en un test de salud mental', 
                'activa')
    """, (usuario_id,))
    conn.commit()
    cur.close()

@app.route('/resultados_test')
@login_required
def resultados_test():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.*, t.nombre_test 
        FROM resultados_test r 
        JOIN tests_salud t ON r.test_id = t.id 
        WHERE r.usuario_id = %s 
        ORDER BY r.fecha_realizacion DESC
    """, (current_user.id,))
    resultados = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('resultados_test.html', resultados=resultados)

#Nuevas rutas para Dasboard Psicólogo_________________________________

# ============ APIs PARA PSICÓLOGO ============

@app.route('/api/psicologo/conversaciones')
@login_required
def api_psicologo_conversaciones():
    if current_user.tipo_usuario != 'psicologo':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, c.estado, u.nombre as usuario_nombre,
               (SELECT mensaje FROM mensajes_chat 
                WHERE conversacion_id = c.id 
                ORDER BY fecha_envio DESC LIMIT 1) as ultimo_mensaje
        FROM conversaciones_chat c
        JOIN usuarios u ON c.usuario_id = u.id
        WHERE c.psicologo_id = (SELECT id FROM psicologos WHERE usuario_id = %s)
        ORDER BY c.fecha_inicio DESC
    """, (current_user.id,))
    conversaciones = cur.fetchall()
    cur.close()
    
    return jsonify({'conversaciones': conversaciones})

@app.route('/api/psicologo/estadisticas')
@login_required
def api_psicologo_estadisticas():
    if current_user.tipo_usuario != 'psicologo':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    
    # Total conversaciones
    cur.execute("""
        SELECT COUNT(*) as total FROM conversaciones_chat c
        JOIN psicologos p ON c.psicologo_id = p.id
        WHERE p.usuario_id = %s
    """, (current_user.id,))
    total_conv = cur.fetchone()['total']
    
    # Total pacientes únicos
    cur.execute("""
        SELECT COUNT(DISTINCT c.usuario_id) as total FROM conversaciones_chat c
        JOIN psicologos p ON c.psicologo_id = p.id
        WHERE p.usuario_id = %s
    """, (current_user.id,))
    total_pacientes = cur.fetchone()['total']
    
    # Calificación promedio
    cur.execute("""
        SELECT AVG(calificacion) as promedio FROM valoraciones_psicologos vp
        JOIN psicologos p ON vp.psicologo_id = p.id
        WHERE p.usuario_id = %s
    """, (current_user.id,))
    calif = cur.fetchone()
    
    cur.close()
    
    return jsonify({
        'total_conversaciones': total_conv,
        'total_pacientes': total_pacientes,
        'calificacion_promedio': round(calif['promedio'] or 0, 1)
    })

@app.route('/api/psicologo/alertas')
@login_required
def api_psicologo_alertas():
    if current_user.tipo_usuario != 'psicologo':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.*, u.nombre as usuario_nombre, 
               DATE_FORMAT(a.fecha_generacion, '%%d/%%m/%%Y %%H:%%i') as fecha_generacion
        FROM alertas a
        JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.estado = 'activa'
        ORDER BY FIELD(a.nivel_alerta, 'urgente', 'precaucion', 'informativo')
    """)
    alertas = cur.fetchall()
    cur.close()
    
    return jsonify({'alertas': alertas})

@app.route('/api/psicologo/disponibilidad', methods=['POST'])
@login_required
def api_psicologo_disponibilidad():
    if current_user.tipo_usuario != 'psicologo':
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.get_json()
    disponible = data.get('disponible', False)
    horario = data.get('horario', '')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE psicologos 
        SET disponibilidad = %s 
        WHERE usuario_id = %s
    """, (horario if disponible else None, current_user.id))
    mysql.connection.commit()
    cur.close()
    
    return jsonify({'success': True})


# ============ APIs PARA FAMILIAR ============

@app.route('/api/familiar/alertas')
@login_required
def api_familiar_alertas():
    if current_user.tipo_usuario != 'familiar':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.*, u.nombre as usuario_nombre, u.telefono as usuario_telefono,
               DATE_FORMAT(a.fecha_generacion, '%%d/%%m/%%Y %%H:%%i') as fecha_generacion
        FROM alertas a
        JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.familiar_id = %s OR (a.familiar_id IS NULL AND a.usuario_id IN 
            (SELECT usuario_id FROM contactos_emergencia WHERE familiar_id = %s))
        ORDER BY FIELD(a.nivel_alerta, 'urgente', 'precaucion', 'informativo'), a.fecha_generacion DESC
    """, (current_user.id, current_user.id))
    alertas = cur.fetchall()
    cur.close()
    
    return jsonify({'alertas': alertas})

@app.route('/api/familiar/seguimiento')
@login_required
def api_familiar_seguimiento():
    if current_user.tipo_usuario != 'familiar':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.id, u.nombre, 
               (SELECT nivel_riesgo FROM resultados_test 
                WHERE usuario_id = u.id 
                ORDER BY fecha_realizacion DESC LIMIT 1) as nivel_riesgo,
               (SELECT DATE_FORMAT(fecha_realizacion, '%%d/%%m/%%Y') FROM resultados_test 
                WHERE usuario_id = u.id 
                ORDER BY fecha_realizacion DESC LIMIT 1) as ultimo_test
        FROM contactos_emergencia ce
        JOIN usuarios u ON ce.usuario_id = u.id
        WHERE ce.familiar_id = %s
        ORDER BY ce.orden_prioridad
    """, (current_user.id,))
    familiares = cur.fetchall()
    cur.close()
    
    return jsonify({'familiares': familiares})

@app.route('/api/familiar/agregar', methods=['POST'])
@login_required
def api_familiar_agregar():
    if current_user.tipo_usuario != 'familiar':
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.get_json()
    email = data.get('email')
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    usuario = cur.fetchone()
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    # Verificar si ya existe
    cur.execute("""
        SELECT id FROM contactos_emergencia 
        WHERE familiar_id = %s AND usuario_id = %s
    """, (current_user.id, usuario['id']))
    existe = cur.fetchone()
    
    if existe:
        return jsonify({'error': 'Ya sigues a esta persona'}), 400
    
    cur.execute("""
        INSERT INTO contactos_emergencia (familiar_id, usuario_id, nombre_contacto, telefono, parentesco, orden_prioridad)
        VALUES (%s, %s, (SELECT nombre FROM usuarios WHERE id = %s), (SELECT telefono FROM usuarios WHERE id = %s), 'Familiar', 99)
    """, (current_user.id, usuario['id'], usuario['id'], usuario['id']))
    mysql.connection.commit()
    cur.close()
    
    return jsonify({'success': True})

@app.route('/api/familiar/atender_alerta/<int:alerta_id>', methods=['POST'])
@login_required
def api_familiar_atender_alerta(alerta_id):
    if current_user.tipo_usuario != 'familiar':
        return jsonify({'error': 'No autorizado'}), 403
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE alertas 
        SET estado = 'atendida', fecha_atencion = NOW() 
        WHERE id = %s AND (familiar_id = %s OR familiar_id IS NULL)
    """, (alerta_id, current_user.id))
    mysql.connection.commit()
    cur.close()
    
    return jsonify({'success': True})

# RUN

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)