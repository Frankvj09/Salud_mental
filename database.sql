CREATE DATABASE IF NOT EXISTS salud_mental_db;
USE salud_mental_db;

-- Tabla de usuarios
CREATE TABLE usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    tipo_usuario ENUM('usuario', 'psicologo', 'familiar') DEFAULT 'usuario',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP NULL
);

-- Tabla de psicólogos
CREATE TABLE psicologos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT UNIQUE,
    especialidad VARCHAR(100),
    cedula_profesional VARCHAR(50),
    experiencia_anos INT,
    descripcion TEXT,
    tarifa DECIMAL(10,2),
    disponibilidad TEXT,
    calificacion_promedio DECIMAL(3,2) DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de tests de salud mental
CREATE TABLE tests_salud (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre_test VARCHAR(100) NOT NULL,
    descripcion TEXT,
    instrucciones TEXT
);

-- Tabla de preguntas para tests
CREATE TABLE preguntas_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    test_id INT,
    pregunta TEXT NOT NULL,
    opciones JSON,
    puntuacion_max INT,
    FOREIGN KEY (test_id) REFERENCES tests_salud(id) ON DELETE CASCADE
);

-- Tabla de resultados de tests
CREATE TABLE resultados_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT,
    test_id INT,
    puntuacion_total INT,
    nivel_riesgo ENUM('bajo', 'moderado', 'alto') NOT NULL,
    recomendaciones TEXT,
    fecha_realizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests_salud(id) ON DELETE CASCADE
);

-- Tabla de conversaciones del chat
CREATE TABLE conversaciones_chat (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT,
    psicologo_id INT,
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP NULL,
    estado ENUM('activa', 'finalizada', 'pendiente') DEFAULT 'pendiente',
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (psicologo_id) REFERENCES psicologos(id) ON DELETE SET NULL
);

-- Tabla de mensajes del chat
CREATE TABLE mensajes_chat (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversacion_id INT,
    remitente_id INT,
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (conversacion_id) REFERENCES conversaciones_chat(id) ON DELETE CASCADE,
    FOREIGN KEY (remitente_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de alertas para familiares
CREATE TABLE alertas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT,
    familiar_id INT,
    tipo_alerta ENUM('test_alto_riesgo', 'inactividad', 'palabras_clave') NOT NULL,
    nivel_alerta ENUM('informativo', 'precaucion', 'urgente') NOT NULL,
    mensaje TEXT,
    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_atencion TIMESTAMP NULL,
    estado ENUM('activa', 'atendida', 'cancelada') DEFAULT 'activa',
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (familiar_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de contactos de emergencia
CREATE TABLE contactos_emergencia (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT,
    nombre_contacto VARCHAR(100) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    parentesco VARCHAR(50),
    orden_prioridad INT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de directorio de psicólogos (adicional a la tabla psicologos)
CREATE TABLE directorio_psicologos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    psicologo_id INT UNIQUE,
    direccion_consulta VARCHAR(255),
    ciudad VARCHAR(100),
    estado VARCHAR(50),
    codigo_postal VARCHAR(10),
    horario_atencion TEXT,
    modalidad ENUM('presencial', 'online', 'ambas') DEFAULT 'ambas',
    FOREIGN KEY (psicologo_id) REFERENCES psicologos(id) ON DELETE CASCADE
);

-- Tabla de valoraciones de psicólogos
CREATE TABLE valoraciones_psicologos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    psicologo_id INT,
    usuario_id INT,
    calificacion INT CHECK (calificacion BETWEEN 1 AND 5),
    comentario TEXT,
    fecha_valoracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (psicologo_id) REFERENCES psicologos(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Insertar datos de prueba
INSERT INTO tests_salud (nombre_test, descripcion, instrucciones) VALUES
('Test de Depresión (PHQ-9)', 'Evalúa la presencia y severidad de síntomas depresivos', 'Responda cada pregunta considerando cómo se ha sentido en las últimas 2 semanas'),
('Test de Ansiedad (GAD-7)', 'Evalúa la severidad de síntomas de ansiedad generalizada', 'Responda cada pregunta considerando cómo se ha sentido en las últimas 2 semanas'),
('Test de Bienestar Emocional', 'Evaluación general del estado emocional', 'Responda honestamente para obtener una evaluación precisa');