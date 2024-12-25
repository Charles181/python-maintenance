from flask import Flask, redirect, render_template, request, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
import seaborn as sns
from werkzeug.security import check_password_hash, generate_password_hash
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import db, Usuario, LineaProduccion, Equipo, LlamadaServicio, ReporteServicio
from helpers import login_required, is_password_confirmed, user_already_exists, admin_required
from datetime import datetime, date
import pandas as pd
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = "filesystem"
app.config['SECRET_KEY'] = os.urandom(24)

db.init_app(app)

@app.before_request
def create_tables():
    app.before_request_funcs[None].remove(create_tables)
    db.create_all()

@app.before_request
def create_admin():
    admin_user = Usuario.query.filter_by(rol='admin').first()
    if not admin_user:
        # Create a default admin user
        hashed_password = generate_password_hash("defaultadminpassword", method='pbkdf2:sha256')
        new_admin = Usuario(usuario="admin", password_hash=hashed_password, nombre_completo='Administrador de sistema', email='admin@lear.com', departamento='mantenimiento' , rol='admin')
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created with username 'admin' and password 'defaultadminpassword'")


class EquipoModelView(ModelView):
    form_columns = ['numero', 'nombre', 'descripcion', 'linea_produccion']
    form_args = {
        'linea_produccion': {
            'query_factory': lambda: LineaProduccion.query,
            'get_label': 'nombre'
        }
    }

admin = Admin(app, name='Mantenimiento', template_mode='bootstrap4')
admin.add_view(ModelView(Usuario, db.session))
admin.add_view(ModelView(LineaProduccion, db.session))
admin.add_view(ModelView(Equipo, db.session))
admin.add_view(ModelView(LlamadaServicio, db.session))
admin.add_view(ModelView(ReporteServicio, db.session))

@app.route("/registro", methods=["GET", "POST"])
@admin_required
def registro():
    if request.method == "POST":
        username = request.form.get("username")
        name = request.form.get("nombre")
        email = request.form.get("email")
        departamento = request.form.get("departamento")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        hashed_password = generate_password_hash(password,method='pbkdf2:sha256')
        if not is_password_confirmed(password, confirmation) or not (username or email):
            flash("Error en confirmación de contraseña o existe algún campo faltante")
            return redirect("/registro")
        elif user_already_exists(username):
            flash(f"El usuario {username} ya existe en la base de datos!")
            return redirect("/registro")
        new_user = Usuario(usuario=username, password_hash=hashed_password, nombre_completo=name, email=email, departamento=departamento, rol='usuario')
        db.session.add(new_user)
        db.session.commit()
        flash(f"El usuario {name} ha sido creado con éxito.")
        return redirect("/registro")
    return render_template("registro.html")

@app.route("/graficos", methods=["GET", "POST"])
def graficos():
    try:
        reportes = db.session.query(ReporteServicio).all()
        for reporte in reportes:
            print(f"ID: {reporte.id_llamada_servicio}, Tipo de Falla: {reporte.tipo_falla}, Tiempo perdido: {reporte.total_tiempo_perdido} minutos, Causa Raíz: {reporte.causa_raiz}")
    except Exception as e:
        print(f"Error fetching data: {e}")
    query = db.session.query(ReporteServicio).with_entities(ReporteServicio.id_llamada_servicio, ReporteServicio.tipo_falla, ReporteServicio.total_tiempo_perdido, ReporteServicio.causa_raiz)
    q1 = query.all()
    df = pd.DataFrame.from_records(q1, index='id__reporte', columns=['id__reporte', 'tipo_falla', 'total_tiempo_perdido', 'causa_raiz'])
    # print(df)
    # Conteo de causas raíces
    root_cause_counts = df['causa_raiz'].value_counts()

    fig, ax = plt.subplots(figsize=(14,8), subplot_kw=dict(aspect="equal"))
    wedges, texts, autotexts = ax.pie(root_cause_counts.values, labels=root_cause_counts.index, autopct='%1.1f%%', textprops=dict(color="w"))
    ax.legend(wedges, root_cause_counts.index, title="Causas raíz", loc="lower right", bbox_to_anchor=(1, 0, 0.5, 1))
    plt.setp(autotexts, size=15, weight="bold")
    plt.title('Distribución de causa raíz')
    plt.savefig('static/root_cause_distribution.png')

    # conteo de tipo de fallas
    failure_counts = df['tipo_falla'].value_counts()

    plt.figure(figsize=(10,6))
    sns.barplot(x=failure_counts.index, y=failure_counts.values)
    plt.title('Frecuencia de tipo de fallas')
    plt.xlabel('Tipo de fallas')
    plt.ylabel('Conteo')
    plt.savefig('static/failure_types.png')
    return render_template("graficos.html")

@app.route("/", methods=["GET"])
@login_required
def index():
    query = db.session.query(LlamadaServicio,Equipo, LineaProduccion).join(Equipo, LlamadaServicio.id_equipo == Equipo.id).join(LineaProduccion, Equipo.id_linea == LineaProduccion.id).order_by(db.desc(LlamadaServicio.fecha)).all()
    # df = pd.read_sql_query(query, con=engine)
    # print(df)
    return render_template("index.html", query=query)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Must provide username")
            return redirect("/login")
        elif not password:
            flash("Must provide password")
            return redirect("/login")

        user = Usuario.query.filter_by(usuario=username).first()
        if user == None or not check_password_hash(user.password_hash, password):
            flash("Nombre de usuario o contraseña invalidos")
            return redirect("/login")

        session["user_id"] = user.id
        session["user_type"] = user.rol
        session["user_full_name"] = user.nombre_completo
        flash(f"Sesión iniciada como {user.usuario}")
        if user.rol != 'admin':
            return redirect("/")
        else:
            return redirect("/admin")
    else:
        return render_template("login.html")

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.")
    return redirect("/")
@app.route("/form", methods=["GET"])
def show_form():
    return render_template("form.html")


@app.route("/generar_llamada_servicio", methods=["GET", "POST"])
@login_required
def generar_llamada_servicio():
    if request.method == "GET":
        equipos = Equipo.query.all()
        
        # Get today's date formatted for the date input
        today_date = date.today().strftime("%d-%m-%Y")
        print(today_date)
        
        # Get current time formatted for the time input
        current_time = datetime.now().strftime("%H:%M")
        
        return render_template("generar_llamada_servicio.html",
                             equipos=equipos,
                             today_date=today_date,
                             current_time=current_time)
    
    if request.method == "POST":
        try:
            fecha_str = request.form.get("fecha")
            id_equipo = request.form.get("equipment")
            turno = request.form.get("turno")
            hora_paro = request.form.get("hora_paro")
            hora_aviso = request.form.get("hora_aviso")
            
            if not all([fecha_str, id_equipo, turno, hora_paro, hora_aviso]):
                flash("Por favor complete todos los campos", "error")
                return redirect(url_for("generar_llamada_servicio"))
            
            # Convertir entradas string a objetos datetime correctos           <--------------------!!!!!!!!!!!!!!!!!!!
            fecha = datetime.strptime(fecha_str, "%d-%m-%Y").date()
            
            stop_time = datetime.combine(
                fecha, 
                datetime.strptime(hora_paro, "%H:%M").time()
            )
            report_time = datetime.combine(
                fecha, 
                datetime.strptime(hora_aviso, "%H:%M").time()
            )
            
            new_service_call = LlamadaServicio(
                id_equipo=id_equipo,
                id_reporta=session["user_id"],
                fecha=fecha,
                turno=int(turno),
                hora_paro=stop_time,
                hora_aviso=report_time,
                status="pendiente"
            )
            
            db.session.add(new_service_call)
            db.session.commit()
            
            flash("Llamada de servicio generada exitosamente", "success")
            return redirect("/generar_llamada_servicio")
            
        except Exception as e:
            print(f"Error generating service call: {str(e)}")
            db.session.rollback()
            flash("Error al generar la llamada de servicio", "error")
            return redirect("/generar_llamada_servicio")
        
@app.route("/llamadas_servicio", methods=["GET"])
@login_required
def llamadas_servicio():
    hoy = date.today()
    llamadas = LlamadaServicio.query.all()
    llamadas_lista = []

    for llamada in llamadas:
        equipo = Equipo.query.get(llamada.id_equipo)
        reporta = Usuario.query.get(llamada.id_reporta)
        llamadas_lista.append({
            'id': llamada.id,
            'fecha': llamada.fecha.strftime('%d/%m/%Y'),
            'turno': llamada.turno,
            'equipo': f"{equipo.nombre} - No. {equipo.numero}",
            'hora_paro': llamada.hora_paro.strftime('%H:%M'),
            'hora_aviso': llamada.hora_aviso.strftime('%H:%M'),
            'reporta': reporta.nombre_completo,
            'status': llamada.status
        })
    
    return render_template("llamadas_servicio.html", llamadas=llamadas_lista)

@app.route("/api/llamadas_servicio", methods=["GET"])
@login_required
def api_llamadas_servicio():
    fecha = request.args.get('fecha')
    status = request.args.get('status')
    
    query = LlamadaServicio.query
    
    if fecha:
        query = query.filter(LlamadaServicio.fecha == datetime.strptime(fecha, '%Y-%m-%d').date())
    if status:
        query = query.filter(LlamadaServicio.status == status)
    
    llamadas = query.all()
    
    llamadas_lista = []
    for llamada in llamadas:
        equipo = Equipo.query.get(llamada.id_equipo)
        reporta = Usuario.query.get(llamada.id_reporta)
        llamadas_lista.append({
            'id': llamada.id,
            'fecha': llamada.fecha.strftime('%d/%m/%Y'),
            'turno': llamada.turno,
            'equipo': f"{equipo.nombre} - No. {equipo.numero}",
            'hora_paro': llamada.hora_paro.strftime('%H:%M'),
            'hora_aviso': llamada.hora_aviso.strftime('%H:%M'),
            'reporta': reporta.nombre_completo,
            'status': llamada.status
        })
    
    return jsonify(llamadas_lista)

@app.route("/reporte_servicio/<int:llamada_id>", methods=["GET", "POST"])
@login_required
def reporte_servicio(llamada_id):
    llamada = LlamadaServicio.query.get_or_404(llamada_id)
    current_user = Usuario.query.filter_by(id=session["user_id"]).first()
    
    causas_raiz = [
        "Causas relacionadas con las instalaciones",
        "Condiciones severas del medio ambiente",
        "Empleo de repuestos no adecuados o de mala calidad",
        "Falla natural de partes por uso o envejecimiento",
        "Falla o desgaste prematuro de partes (calidad de partes)",
        "Falta de mtto preventivo o predictivo",
        "Mala instalación de repuestos",
        "Operación o uso inadecuado",
        "Problema de diseño o adaptaciones del equipo"
    ]

    if request.method == "GET":
        return render_template("reporte_servicio.html", llamada=llamada, causas_raiz=causas_raiz, current_user=current_user)

    if request.method == "POST":
        try:
            equipo_detenido = request.form.get("equipo_detenido") == "True"
            tipo_mantenimiento = request.form.get("tipo_mantenimiento")
            tipo_mantenimiento_otro = request.form.get("tipo_mantenimiento_otro")
            tipo_falla = request.form.get("tipo_falla")
            descripcion_falla = request.form.get("descripcion_falla")
            descripcion_trabajo = request.form.get("descripcion_trabajo")
            descripcion_partes = request.form.get("descripcion_partes")
            comentarios = request.form.get("comentarios")
            causa_raiz = request.form.get("causa_raiz")
            hora_llegada = datetime.strptime(request.form.get("hora_llegada"), "%H:%M").time()
            hora_entrega = datetime.strptime(request.form.get("hora_entrega"), "%H:%M").time()
            total_tiempo_perdido = int(request.form.get("total_tiempo_perdido"))

            nuevo_reporte = ReporteServicio(
                id_llamada_servicio=llamada_id,
                id_tecnico=session["user_id"],
                equipo_detenido=equipo_detenido,
                tipo_mantenimiento=tipo_mantenimiento,
                tipo_mantenimiento_otro=tipo_mantenimiento_otro if tipo_mantenimiento == "Otro" else None,
                tipo_falla=tipo_falla,
                descripcion_falla=descripcion_falla,
                descripcion_trabajo=descripcion_trabajo,
                descripcion_partes=descripcion_partes,
                comentarios=comentarios,
                causa_raiz=causa_raiz,
                hora_llegada=datetime.combine(llamada.fecha, hora_llegada),
                hora_entrega=datetime.combine(llamada.fecha, hora_entrega),
                total_tiempo_perdido=total_tiempo_perdido
            )

            db.session.add(nuevo_reporte)
            llamada.status = "completado"
            db.session.commit()

            flash("Reporte de servicio guardado exitosamente", "success")
            return redirect(url_for("llamadas_servicio"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar el reporte: {str(e)}", "error")
            return render_template("reporte_servicio.html", llamada=llamada, causas_raiz=causas_raiz, current_user=current_user)
