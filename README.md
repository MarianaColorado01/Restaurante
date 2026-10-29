# Sistema Web para Restaurante

Aplicación web para un restaurante con registro e inicio de sesión de usuarios, inventario de comidas y bebidas, y gestión de pedidos.

## Funcionalidades

- Registro e inicio de sesión con contraseñas cifradas (SHA-256).
- Rutas protegidas por sesión.
- Inventario de comidas y bebidas.
- Registro y seguimiento de pedidos con su estado y precio total.

## Tecnologías

- Python y Flask
- MySQL (Flask-MySQLdb)
- HTML, Tailwind CSS y JavaScript

## Cómo ejecutarlo

1. Instala las dependencias:

   ```bash
   pip install flask flask-mysqldb
   ```

2. Crea la base de datos `restaurante` en MySQL.
3. Define las variables de entorno de la conexión:

   ```bash
   export MYSQL_HOST=localhost
   export MYSQL_USER=tu_usuario
   export MYSQL_PASSWORD=tu_contraseña
   export MYSQL_DB=restaurante
   export SECRET_KEY=una_clave_segura
   ```

4. Inicia la aplicación:

   ```bash
   python funciones.py
   ```

## Autora

Lizet Mariana Colorado Esguerra · [GitHub](https://github.com/MarianaColorado01) · [LinkedIn](https://www.linkedin.com/in/lizet-colorado-92a71b1a0/)
