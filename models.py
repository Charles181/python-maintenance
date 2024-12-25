from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nombre_completo = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'tecnico', 'producccion', 'admin'
    departamento = db.Column(db.String(50), nullable=False)  # 'linea1', 'linea2', 'mantenimiento', etc.
    activo = db.Column(db.Boolean, default=True)
    creado = db.Column(db.DateTime, default=datetime.now())
    
    reportes_serviccio = db.relationship('ReporteServicio', backref='tecnico', lazy=True)
    llamadas_servicio = db.relationship('LlamadaServicio', backref='reporta', lazy=True)

class LineaProduccion(db.Model):
    __tablename__ = 'lineas_produccion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    
    equipo = db.relationship('Equipo', backref='linea_produccion', lazy=True)

class Equipo(db.Model):
    __tablename__ = 'equipo'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    id_linea = db.Column(db.Integer, db.ForeignKey('lineas_produccion.id'), nullable=False)
    
    llamadas_servicio = db.relationship('LlamadaServicio', backref='equipo', lazy=True)

class LlamadaServicio(db.Model):
    __tablename__ = 'llamadas_servicio'
    id = db.Column(db.Integer, primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    id_reporta = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    fecha = db.Column(db.Date, nullable=False)
    turno = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    hora_paro = db.Column(db.DateTime, nullable=False)
    hora_aviso = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pendiente')  # pending, in_progress, completed
    
    reporte_servicio = db.relationship('ReporteServicio', backref='llamada_servicio', lazy=True, uselist=False)

class ReporteServicio(db.Model):
    __tablename__ = 'reportes_servicio'
    id = db.Column(db.Integer, primary_key=True)
    id_llamada_servicio = db.Column(db.Integer, db.ForeignKey('llamadas_servicio.id'), nullable=False)
    id_tecnico = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    equipo_detenido = db.Column(db.Boolean, nullable=False)
    tipo_mantenimiento = db.Column(db.String(50), nullable=False)  # 'corrective' or custom
    tipo_mantenimiento_otro = db.Column(db.String(100))
    tipo_falla = db.Column(db.String(20), nullable=False)  # electrical, mechanical, electronic, plc
    descripcion_falla = db.Column(db.Text, nullable=False)
    descripcion_trabajo = db.Column(db.Text, nullable=False)
    descripcion_partes = db.Column(db.Text)
    comentarios = db.Column(db.Text)
    causa_raiz = db.Column(db.String(100), nullable=False)
    hora_llegada = db.Column(db.DateTime, nullable=False)
    hora_entrega = db.Column(db.DateTime, nullable=False)
    total_tiempo_perdido = db.Column(db.Integer)  # in minutes
    creado = db.Column(db.DateTime, default=datetime.now())
    actualizado = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())