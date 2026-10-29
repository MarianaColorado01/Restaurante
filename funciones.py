from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from functools import wraps
import os
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambia_esta_clave')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Config MySQL
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'restaurante')
mysql = MySQL(app)

def encriptar_contraseña(contraseña):
    return hashlib.sha256(contraseña.encode()).hexdigest()

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html', form_type='index')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        contraseña = encriptar_contraseña(request.form['contraseña'])
        
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuario (nombre, apellido, correo, contraseña) VALUES (%s, %s, %s, %s)",
                (nombre, apellido, correo, contraseña)
            )
            mysql.connection.commit()
            flash('Registro exitoso. Inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Error: Correo ya registrado', 'danger')
        finally:
            cursor.close()
    
    return render_template('index.html', form_type='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = encriptar_contraseña(request.form['contraseña'])
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuario WHERE correo = %s", (correo,))
        usuario = cursor.fetchone()
        cursor.close()
        
        if usuario and usuario[4] == contraseña:
            session['usuario'] = {
                'id': usuario[0],
                'nombre': usuario[1],
                'apellido': usuario[2],
                'correo': usuario[3]
            }
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
    
    return render_template('index.html', form_type='login')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', form_type='dashboard')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Ruta para buscar cliente (solo POST)
@app.route('/buscar_cliente', methods=['POST'])
def buscar_cliente():
    if 'usuario' not in session:
        return jsonify({"mensaje": "No autorizado"}), 401

    cedula = request.json.get("cedula")
    if not cedula:
        return jsonify({"mensaje": "Cédula no proporcionada"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT nombre, apellido, cedula FROM clientes WHERE cedula = %s", (cedula,))
    resultado = cursor.fetchone()
    cursor.close()

    if resultado:
        columnas = ['nombre', 'apellido', 'cedula']
        cliente_dict = dict(zip(columnas, resultado))
        return jsonify({"mensaje": "Cliente encontrado", "cliente": cliente_dict})
    else:
        return jsonify({"mensaje": "Cliente no encontrado"})


# Ruta para registrar cliente (solo POST)
@app.route('/registrar_cliente', methods=['POST'])
def registrar_cliente():
    if 'usuario' not in session:
        return jsonify({"mensaje": "No autorizado"}), 401

    nombre = request.json.get("nombre")
    apellido = request.json.get("apellido")
    cedula = request.json.get("cedula")

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM clientes WHERE cedula = %s", (cedula,))
        if cursor.fetchone():
            return jsonify({"mensaje": "El cliente ya está registrado"})

        cursor.execute(
            "INSERT INTO clientes (nombre, apellido, cedula, activo) VALUES (%s, %s, %s, 1)",
            (nombre, apellido, cedula)
        )
        mysql.connection.commit()
        return jsonify({"mensaje": "Cliente registrado exitosamente"})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"mensaje": "Error al registrar el cliente"}), 500
    finally:
        cursor.close()


def obtener_clientes(pagina=1, por_pagina=10):
    try:
        cursor = mysql.connection.cursor()
        
        # Obtener total de clientes
        cursor.execute("SELECT COUNT(*) FROM clientes")
        total = cursor.fetchone()[0]
        
        # Calcular offset
        offset = (pagina - 1) * por_pagina
        
        # Obtener clientes paginados
        cursor.execute("""
            SELECT id, nombre, apellido, cedula, activo
            FROM clientes 
            ORDER BY id DESC 
            LIMIT %s OFFSET %s
        """, (por_pagina, offset))
        
        clientes = []
        columnas = [col[0] for col in cursor.description]
        for cliente in cursor.fetchall():
            clientes.append(dict(zip(columnas, cliente)))
            
        return clientes, total
        
    except Exception as e:
        print(f"Error obteniendo clientes: {str(e)}")
        return [], 0
    finally:
        cursor.close()

# Ruta para obtener datos de un cliente (GET)
@app.route('/clientes/<int:id>')
@login_required
def obtener_cliente(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, nombre, apellido, cedula, activo 
            FROM clientes WHERE id = %s
        """, (id,))
        cliente = cursor.fetchone()
        
        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404
            
        columnas = ['id', 'nombre', 'apellido', 'cedula', 'activo']
        return jsonify(dict(zip(columnas, cliente)))
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()


# Ruta de administración
@app.route('/admin')
@login_required
def admin():
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 10
    
    clientes, total = obtener_clientes(pagina, por_pagina)
    
    return render_template('index.html',
                         form_type='admin',
                         clientes=clientes,
                         total_clientes=total,
                         pagina=pagina,
                         por_pagina=por_pagina)
# Ruta para editar cliente
# Ruta para guardar cambios (PUT)
@app.route('/editar_cliente/<int:id>', methods=['PUT'])
@login_required
def editar_cliente(id):
    try:
        data = request.get_json()
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET nombre = %s, apellido = %s, cedula = %s, activo = %s 
            WHERE id = %s
        """, (data['nombre'], data['apellido'], data['cedula'], data['activo'], id))
        mysql.connection.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

# Ruta para eliminar cliente
@app.route('/eliminar_cliente/<int:id>', methods=['DELETE'])
@login_required
def eliminar_cliente(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE clientes SET activo = 0 WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Cliente desactivado', 'id': id})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()

@app.route('/reactivar_cliente/<int:id>', methods=['POST'])
@login_required
def reactivar_cliente(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE clientes SET activo = 1 WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Cliente reactivado', 'id': id})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()


# Ruta de inventario
@app.route('/inventario', methods=['GET', 'POST'])
def inventario():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        stock = int(request.form['stock'])
        precio = request.form['precio']

        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO inventario (nombre, categoria, stock, fecha_ingreso, precio) VALUES (%s, %s, %s, NOW(), %s)",
                (nombre, categoria, stock, precio)
            )
            mysql.connection.commit()
            flash('Producto agregado al inventario correctamente.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar el producto: {str(e)}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('inventario'))

    # Obtener la lista de productos en el inventario
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id, nombre, categoria, stock, fecha_ingreso, precio FROM inventario")
        inventario = cursor.fetchall()
    except Exception as e:
        flash(f'Error al obtener el inventario: {str(e)}', 'danger')
        inventario = []
    finally:
        cursor.close()

    print("Datos del inventario:", inventario)  # Depuración
    return render_template('index.html', form_type='inventario', inventario=inventario)

@app.route('/editar_stock', methods=['POST'])
def editar_stock():
    if 'usuario' not in session:
        return jsonify({"success": False, "error": "No autorizado"}), 401

    producto_id = request.form['productoId']
    nuevo_stock = int(request.form['nuevoStock'])

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "UPDATE inventario SET stock = %s WHERE id = %s",
            (nuevo_stock, producto_id)
        )
        mysql.connection.commit()
        return jsonify({"success": True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()


@app.route('/pedidos')
def pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    clientes = []
    bebidas = []
    comidas = []
    pedidos = []  # Inicializa todas las variables al principio

    try:
        # Obtener clientes
        cursor.execute("SELECT id, nombre, apellido FROM clientes")
        clientes = cursor.fetchall()

        # Obtener bebidas
        cursor.execute("SELECT id, nombre, stock FROM inventario WHERE categoria = 'bebida'")
        bebidas = cursor.fetchall()

        # Obtener comidas
        cursor.execute("SELECT id, nombre, stock FROM inventario WHERE categoria = 'comida'")
        comidas = cursor.fetchall()

        # Obtener pedidos
        cursor.execute("""
            SELECT p.id, c.nombre, c.apellido, 
                   COALESCE(b.nombre, 'N/A'), 
                   COALESCE(com.nombre, 'N/A'), 
                   p.cantidad_bebida, p.cantidad_comida,
                   p.fecha, p.estado,
                   COALESCE(b.precio, 0), 
                   COALESCE(com.precio, 0),
                   (COALESCE(b.precio * p.cantidad_bebida, 0) + COALESCE(com.precio * p.cantidad_comida, 0)) AS total
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN inventario b ON p.bebida_id = b.id AND b.categoria = 'bebida'
            LEFT JOIN inventario com ON p.comida_id = com.id AND com.categoria = 'comida'
            ORDER BY p.fecha DESC
        """)
        pedidos = cursor.fetchall()

    except Exception as e:
        print(f"Error: {str(e)}")
        flash("Error al cargar los datos", "danger")
    finally:
        cursor.close()

    return render_template('index.html',
                         form_type='pedidos',
                         clientes=clientes,
                         bebidas=bebidas,
                         comidas=comidas,
                         pedidos=pedidos)  # Ahora siempre está definida


# Ruta para procesar el formulario de pedidos
@app.route('/crear_pedido', methods=['POST'])
def crear_pedido():
    if 'usuario' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    # Obtener datos del formulario
    cliente_id = request.form['cliente_id']
    bebida_id = request.form.get('bebida_id', None)
    comida_id = request.form.get('comida_id', None)
    cantidad_bebida = int(request.form.get('cantidad_bebida', 0))
    cantidad_comida = int(request.form.get('cantidad_comida', 0))

    cursor = mysql.connection.cursor()

    try:
        precio_total = 0

        # Verificar y calcular bebida
        if bebida_id and cantidad_bebida > 0:
            cursor.execute("SELECT stock, precio FROM inventario WHERE id = %s", (bebida_id,))
            stock, precio = cursor.fetchone()
            if stock < cantidad_bebida:
                flash(f'Stock insuficiente en bebida: {stock} unidades', 'danger')
                return redirect(url_for('pedidos'))
            precio_total += precio * cantidad_bebida

        # Verificar y calcular comida
        if comida_id and cantidad_comida > 0:
            cursor.execute("SELECT stock, precio FROM inventario WHERE id = %s", (comida_id,))
            stock, precio = cursor.fetchone()
            if stock < cantidad_comida:
                flash(f'Stock insuficiente en comida: {stock} unidades', 'danger')
                return redirect(url_for('pedidos'))
            precio_total += precio * cantidad_comida

        # Insertar pedido
        cursor.execute(
            "INSERT INTO pedidos (cliente_id, bebida_id, comida_id, cantidad_bebida, cantidad_comida, precio_total, estado) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'pendiente')",
            (cliente_id, bebida_id, comida_id, cantidad_bebida, cantidad_comida, precio_total)
        )

        # Actualizar stocks
        if bebida_id:
            cursor.execute("UPDATE inventario SET stock = stock - %s WHERE id = %s", (cantidad_bebida, bebida_id))
        if comida_id:
            cursor.execute("UPDATE inventario SET stock = stock - %s WHERE id = %s", (cantidad_comida, comida_id))

        mysql.connection.commit()
        flash('Pedido registrado exitosamente', 'success')

    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('pedidos'))

@app.route('/actualizar_estado/<int:pedido_id>', methods=['POST'])
def actualizar_estado(pedido_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE pedidos SET estado = 'completado' WHERE id = %s",
            (pedido_id,))
        mysql.connection.commit()
        flash('Estado actualizado correctamente', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al actualizar estado: {str(e)}', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('pedidos'))



# Ruta para listar los pedidos
@app.route('/pedidos')
def listar_pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    try:
        # Asegúrate de que esta consulta coincida con la estructura de tu base de datos
        cursor.execute("""
            SELECT p.id, 
                   c.nombre, 
                   c.apellido, 
                   b.nombre AS bebida, 
                   co.nombre AS comida, 
                   p.cantidad_bebida, 
                   p.cantidad_comida, 
                   p.fecha, 
                   p.estado,
                   b.precio AS precio_bebida,
                   co.precio AS precio_comida,
                   (IFNULL(b.precio * p.cantidad_bebida, 0) + 
                   (IFNULL(co.precio * p.cantidad_comida, 0)) AS total
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN bebidas b ON p.bebida_id = b.id
            LEFT JOIN comidas co ON p.comida_id = co.id
            ORDER BY p.fecha DESC
        """)
        pedidos = cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener pedidos: {str(e)}")
        pedidos = []
    finally:
        cursor.close()

    return render_template('pedidos.html', pedidos=pedidos)

@app.route('/pedidos/pendientes')
def pedidos_pendientes():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    try:
        # Consulta modificada con filtro de estado
        cursor.execute("""
            SELECT p.id, 
                   c.nombre, 
                   c.apellido, 
                   COALESCE(b.nombre, 'N/A') AS bebida,
                   COALESCE(com.nombre, 'N/A') AS comida,
                   p.cantidad_bebida,
                   p.cantidad_comida,
                   p.fecha,
                   p.estado,
                   p.precio_total
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN inventario b ON p.bebida_id = b.id AND b.categoria = 'bebida'
            LEFT JOIN inventario com ON p.comida_id = com.id AND com.categoria = 'comida'
            WHERE p.estado = 'pendiente'
            ORDER BY p.fecha DESC
        """)
        pedidos = cursor.fetchall()
    except Exception as e:
        print(f"Error: {str(e)}")
        pedidos = []
    finally:
        cursor.close()

    return render_template('pedidos.html', 
                         pedidos=pedidos,
                         titulo_pagina="Pedidos Pendientes")

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(port=3000, debug=True)
