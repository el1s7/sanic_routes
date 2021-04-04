# Sanic Routes
Generate routes and validate parameters from a JSON schema.

### Example

> routes.py

```python
from . import controllers, middlewares
from sanic_routes import make_routes
schema = {
	'login': {
		'method': 'POST',
		'path': '/login',
		'controller': 'login' # By default controller is the key name
		'before': ['logged_check'] # Array of middlewares before request
		'params': {
			'username': {
				'required': True,
				'max': 20,
				'min': 1,
				'type': str, # Custom functions supported
				'help': 'The login username',
				# location: Either ('query','path','form','json','headers','cookies') Default is 'form' for post requests
			}
		}
	}
	'register': {
		...another route here
	}
}

routes = make_routes(schema, controllers=controllers, middlewares=middlewares)
```

> controllers.py
```python
async def login(request):
	params = request.ctx.params
	usename = params.username # Parsed from params
```

> app.py
```python
from routes import routes
from sanic import Sanic

def	run():
	app = Sanic(__name__)
	app.blueprint(routes)
	app.run(host="0.0.0.0", port=8001, debug=True)
```