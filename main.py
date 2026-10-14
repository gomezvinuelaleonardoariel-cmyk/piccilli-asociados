from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
)
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import random
from datetime import datetime

app = Flask(__name__)
# Clave secreta obligatoria para el manejo de sesiones en Flask
app.secret_key = "clave_secreta_super_segura_piccilli_2026"

MONGO_URI = "mongodb+srv://gomezvinuelaleonardoariel_db_user:cXIe9PtVYBxdOO4V@dbproyectofinal.kwksir2.mongodb.net/?appName=DBProyectoFinal"

cliente = MongoClient(MONGO_URI)
base_de_datos = cliente["piccilli_asociados"]
coleccion_usuarios = base_de_datos["usuarios"]
coleccion_expedientes = base_de_datos["expedientes"]


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/profesionales")
def profesionales():
    return render_template("profesionales.html")


@app.route("/prueba-bd")
def prueba_bd():
    usuario_prueba = {
        "dni": "33333333",
        "password": "123456",
        "nombre": "Prueba",
        "apellido": "Sistema",
        "rol": "cliente",
    }
    coleccion_usuarios.update_one(
        {"dni": "33333333"}, {"$set": usuario_prueba}, upsert=True
    )
    return "¡Éxito! El cliente de prueba se guardó/actualizó en MongoDB Atlas con su contraseña."


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login-cliente")
def login_cliente():
    return render_template("login_cliente.html")


@app.route("/logo.jpg")
def mostrar_logo():
    return send_from_directory(os.getcwd(), "logopiccilli.jpg")


@app.route("/abogados.jpg")
def mostrar_abogados():
    return send_from_directory(os.getcwd(), "Abogados.jpeg")


# ACTUALIZAR ESTADO DE UN CASO
@app.route("/actualizar-estado/<id>", methods=["POST"])
def actualizar_estado(id):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    nuevo_estado = request.form.get("estado")

    coleccion_expedientes.update_one(
        {"_id": ObjectId(id)}, {"$set": {"estado": nuevo_estado}}
    )
    return redirect(url_for("panel_personal"))


# RUTA PARA CERRAR SESIÓN
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))


# PANEL PERSONAL
@app.route("/panel-personal")
def panel_personal():
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    orden_param = request.args.get("orden", "urgente")
    busqueda = request.args.get("q", "").strip()

    filtro = {}
    if busqueda:
        filtro = {
            "$or": [
                {"nro_legajo": {"$regex": busqueda, "$options": "i"}},
                {"caratula": {"$regex": busqueda, "$options": "i"}},
                {"cliente_nombre": {"$regex": busqueda, "$options": "i"}},
            ]
        }

    # Definimos el criterio de ordenamiento
    if orden_param == "urgente":
        expedientes = list(coleccion_expedientes.find(filtro).sort("vencimiento", 1))
    else:
        direccion = -1 if orden_param == "desc" else 1
        expedientes = list(coleccion_expedientes.find(filtro).sort("_id", direccion))

    return render_template(
        "panel_personal.html",
        expedientes=expedientes,
        orden_actual=orden_param,
        busqueda_actual=busqueda,
        usuario_nombre=session.get("user_nombre"),
    )


# VISTA EXCLUSIVA PARA REGISTRAR CLIENTE
@app.route("/registro-cliente", methods=["GET", "POST"])
def registro_cliente():
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    if request.method == "POST":
        dni = request.form.get("dni")
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        password = request.form.get("password")

        if dni and nombre and apellido and password:
            coleccion_usuarios.update_one(
                {"dni": dni},
                {
                    "$set": {
                        "dni": dni,
                        "nombre": nombre,
                        "apellido": apellido,
                        "password": password,
                        "rol": "cliente",
                    }
                },
                upsert=True,
            )
            return redirect(url_for("panel_personal"))

    return render_template(
        "registro_cliente.html", usuario_nombre=session.get("user_nombre")
    )


# VISTA EXCLUSIVA PARA REGISTRAR NUEVO CASO ASOCIADO A UN CLIENTE
@app.route("/registro-caso/<dni_cliente>", methods=["GET", "POST"])
def registro_caso(dni_cliente):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    cliente_db = coleccion_usuarios.find_one({"dni": dni_cliente, "rol": "cliente"})
    if not cliente_db:
        return redirect(url_for("panel_personal"))

    if request.method == "POST":
        caratula = request.form.get("caratula")
        nro_juzgado = request.form.get("nro_juzgado")
        nro_expediente_judicial = request.form.get(
            "nro_expediente_judicial", "En trámite previo"
        )
        vencimiento = request.form.get("vencimiento")
        estado = request.form.get("estado", "En trámite")

        nro_legajo = f"LEG-2026-{random.randint(1000, 9999)}"

        if caratula and nro_juzgado:
            coleccion_expedientes.insert_one(
                {
                    "nro_legajo": nro_legajo,
                    "caratula": caratula,
                    "nro_juzgado": nro_juzgado,
                    "nro_expediente_judicial": nro_expediente_judicial,
                    "cliente_dni": dni_cliente,
                    "cliente_nombre": f"{cliente_db.get('nombre')} {cliente_db.get('apellido')}",
                    "estado": estado,
                    "vencimiento": vencimiento,
                    "movimientos": [],
                }
            )
            return redirect(url_for("perfil_cliente", dni=dni_cliente))

    return render_template(
        "registro_caso.html",
        cliente=cliente_db,
        usuario_nombre=session.get("user_nombre"),
    )


# LISTADO Y BUSCADOR DE CLIENTES PARA EL PERSONAL
@app.route("/clientes")
def listar_clientes():
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    busqueda = request.args.get("q", "").strip()

    filtro = {"rol": "cliente"}
    if busqueda:
        filtro = {
            "rol": "cliente",
            "$or": [
                {"dni": {"$regex": busqueda, "$options": "i"}},
                {"nombre": {"$regex": busqueda, "$options": "i"}},
                {"apellido": {"$regex": busqueda, "$options": "i"}},
            ],
        }

    clientes = list(coleccion_usuarios.find(filtro))
    return render_template(
        "clientes.html",
        clientes=clientes,
        busqueda_actual=busqueda,
        usuario_nombre=session.get("user_nombre"),
    )


# ACTUALIZAR FECHA DE VENCIMIENTO DE UN CASO
@app.route("/actualizar-vencimiento/<id>", methods=["POST"])
def actualizar_vencimiento(id):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    nuevo_vencimiento = request.form.get("vencimiento")
    caso = coleccion_expedientes.find_one({"_id": ObjectId(id)})

    if nuevo_vencimiento and caso:
        coleccion_expedientes.update_one(
            {"_id": ObjectId(id)}, {"$set": {"vencimiento": nuevo_vencimiento}}
        )

        dni_cliente = caso.get("cliente_dni")
        if dni_cliente:
            return redirect(
                url_for("perfil_cliente", dni=dni_cliente, alerta="vencimiento_ok")
            )

    return redirect(url_for("panel_personal"))


# PERFIL INDIVIDUAL DEL CLIENTE (Muestra sus datos y sus casos)
@app.route("/perfil-cliente/<dni>")
def perfil_cliente(dni):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    cliente_db = coleccion_usuarios.find_one({"dni": dni, "rol": "cliente"})
    if not cliente_db:
        return redirect(url_for("listar_clientes"))

    casos_cliente = list(coleccion_expedientes.find({"cliente_dni": dni}))

    return render_template(
        "perfil_cliente.html",
        cliente=cliente_db,
        expedientes=casos_cliente,
        usuario_nombre=session.get("user_nombre"),
    )


# PANEL DEL CLIENTE
@app.route("/panel-cliente")
def panel_cliente():
    if "user_rol" not in session or session["user_rol"] != "cliente":
        return redirect(url_for("login_cliente"))

    dni_cliente = session.get("user_dni")
    expedientes_cliente = list(coleccion_expedientes.find({"cliente_dni": dni_cliente}))

    return render_template(
        "panel_cliente.html",
        expedientes=expedientes_cliente,
        cliente_nombre=session.get("user_nombre"),
    )


# ELIMINAR: Borrar un expediente por su ID de MongoDB (Solo personal)
@app.route("/eliminar-expediente/<id>", methods=["POST"])
def eliminar_expediente(id):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    coleccion_expedientes.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("panel_personal"))


# ELIMINAR CLIENTE Y SUS CASOS ASOCIADOS
@app.route("/eliminar-cliente/<dni>", methods=["POST"])
def eliminar_cliente(dni):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    coleccion_usuarios.delete_one({"dni": dni, "rol": "cliente"})
    coleccion_expedientes.delete_many({"cliente_dni": dni})

    return redirect(url_for("listar_clientes"))


# RUTA ÚNICA DE LOGIN PARA EL PERSONAL INTERNO (Secretaria o Abogados)
@app.route("/login-personal", methods=["GET", "POST"])
def login_personal():
    error = None
    if request.method == "POST":
        identificador = request.form.get("usuario")
        password = request.form.get("password")

        # Validamos contra usuario (secretaria) o matrícula (abogados)
        usuario = coleccion_usuarios.find_one(
            {
                "$and": [
                    {"password": password},
                    {
                        "$or": [
                            {"usuario": identificador},
                            {"matricula": identificador},
                        ]
                    },
                ]
            }
        )

        if usuario and usuario.get("rol") == "personal":
            session["user_rol"] = "personal"
            session["user_nombre"] = (
                f"{usuario.get('nombre')} {usuario.get('apellido')}"
            )
            return redirect(url_for("panel_personal"))
        else:
            error = "Error en usuario y/o contraseña"

    return render_template("login_personal.html", error=error)


# PROCESAR LOGIN DE CLIENTE
@app.route("/login-cliente", methods=["POST"])
def procesar_login_cliente():
    dni = request.form.get("usuario")
    password_ingresado = request.form.get("password")

    cliente_db = coleccion_usuarios.find_one(
        {"dni": dni, "password": password_ingresado, "rol": "cliente"}
    )

    if cliente_db:
        session["user_rol"] = "cliente"
        session["user_dni"] = dni
        session["user_nombre"] = (
            f"{cliente_db.get('nombre', '')} {cliente_db.get('apellido', '')}"
        )
        return redirect(url_for("panel_cliente"))
    else:
        return redirect(url_for("login_cliente"))


# REGISTRAR UN MOVIMIENTO / NOTA EN UN EXPEDIENTE
@app.route("/agregar-movimiento/<id>", methods=["POST"])
def agregar_movimiento(id):
    if "user_rol" not in session or session["user_rol"] != "personal":
        return redirect(url_for("login_personal"))

    descripcion = request.form.get("descripcion")

    if descripcion:
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        nuevo_movimiento = {"fecha": fecha_actual, "texto": descripcion}

        coleccion_expedientes.update_one(
            {"_id": ObjectId(id)}, {"$push": {"movimientos": nuevo_movimiento}}
        )

    return redirect(url_for("panel_personal"))


# RUTA PARA DAR DE ALTA AL STAFF
@app.route("/crear-staff-inicial")
def crear_staff_inicial():
    personal_inicial = [
        {
            "usuario": "secretaria",
            "password": "xp5535",
            "nombre": "Patricia",
            "apellido": "Secretaria",
            "rol": "personal",
        },
        {
            "matricula": "MP-1025",
            "password": "xp5535",
            "nombre": "Atilio",
            "apellido": "Piccilli",
            "rol": "personal",
        },
        {
            "matricula": "MP-1026",
            "password": "xp5535",
            "nombre": "Ricardo",
            "apellido": "Asociados",
            "rol": "personal",
        },
    ]

    for persona in personal_inicial:
        filtro = {}
        if "usuario" in persona:
            filtro = {"usuario": persona["usuario"]}
        else:
            filtro = {"matricula": persona["matricula"]}

        coleccion_usuarios.update_one(filtro, {"$set": persona}, upsert=True)

    return "¡Listo! Perfiles de staff y contraseñas configurados correctamente en MongoDB Atlas."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
