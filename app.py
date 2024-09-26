from flask import Flask, jsonify, render_template
from flask_cors import CORS
import paho.mqtt.client as mqtt
import psycopg2

# Configuración del broker (Cluster HiveMQ)
broker_url = "fee7a60180ef4e41a8186ff373e7ff32.s1.eu.hivemq.cloud"
broker_port = 8883
username = "Receptor-99"
password = "Receptor-99"

# Configuración de la base de datos PostgreSQL
db_config = {
    'host': 'dpg-crq9kqij1k6c738de76g-a.ohio-postgres.render.com',
    'port': 5432,
    'database': 'mqtt_rr94',
    'user': 'root',
    'password': '8OEMNb7jDnLGwGA0JBiWkTkH94OQClRT'
}

# Crear la aplicación Flask
app = Flask(__name__, static_folder='static')  # Definir carpeta de archivos estáticos
CORS(app)  # Habilitar CORS en toda la aplicación

# Contador para la suscripción (para asegurar suscripción única)
subscription_done = False

# Conectar a la base de datos
def connect_db():
    return psycopg2.connect(**db_config)

# Crear tabla si no existe
def crear_tabla():
    db = connect_db()
    cursor = db.cursor()
    crear_tabla_query = """
    CREATE TABLE IF NOT EXISTS mensajes (
        id SERIAL PRIMARY KEY,
        mensaje TEXT NOT NULL
    );
    """
    cursor.execute(crear_tabla_query)
    db.commit()
    cursor.close()
    db.close()
    print("Tabla 'mensajes' creada (si no existía).")

# Función que se ejecuta cuando se conecta al broker
def on_connect(client, userdata, flags, rc):
    global subscription_done
    if rc == 0:
        print("Conectado al broker MQTT con éxito")
        # Evitar suscripciones múltiples
        if not subscription_done:
            client.subscribe("test/topic")
            subscription_done = True
            print("Suscrito al topic: test/topic")
        else:
            print("Ya se realizó la suscripción, evitando duplicados.")
    else:
        print(f"Error al conectarse, código de resultado: {rc}")

# Función que se ejecuta cuando se recibe un mensaje
def on_message(client, userdata, message):
    print("on_message called")  # Confirmar cuántas veces se llama a esta función
    msg = message.payload.decode()
    print(f"Mensaje recibido en el topic {message.topic}: {msg}")
    
    # Guardar mensaje en la base de datos
    db = connect_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO mensajes (mensaje) VALUES (%s)", (msg,))
        db.commit()
        print("Mensaje almacenado en la base de datos con éxito.")  # Confirmación en consola
    except psycopg2.Error as err:
        print(f"Error al almacenar el mensaje en la base de datos: {err}")
    finally:
        cursor.close()
        db.close()

# Configuración del cliente MQTT
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(username, password)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Conectar usando SSL/TLS
mqtt_client.tls_set()
mqtt_client.connect(broker_url, broker_port)

# Mantener el cliente en espera de mensajes
mqtt_client.loop_start()

# Endpoint para servir la página HTML
@app.route('/')
def index():
    return render_template('index.html')  # Sirve el archivo HTML principal

# Endpoint de la API para obtener mensajes
@app.route('/mensajes', methods=['GET'])
def obtener_mensajes():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM mensajes")
    registros = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify([{"id": registro[0], "mensaje": registro[1]} for registro in registros])

# Evitar reinicios múltiples al activar Flask en modo debug
if __name__ == "__main__":
    # Crear la tabla si no existe
    crear_tabla()

    app.run(debug=True, use_reloader=False)
