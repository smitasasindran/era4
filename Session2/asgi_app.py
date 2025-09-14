from asgiref.wsgi import WsgiToAsgi
from mangum import Mangum
from flask_app import app

# Flask is a WSGI application. Magnum is for ASGI apps like FastAPI
# Wrap the Flask (WSGI) app with the adapter
asgi_app = WsgiToAsgi(app)

# Mangum to run on AWS Lambda. # Disable lifespan to avoid Flask 2.3+ TypeError
handler = Mangum(asgi_app, lifespan="off") # Important: This is the Lambda handler