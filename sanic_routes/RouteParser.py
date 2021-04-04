from sanic import Blueprint, Sanic, request as sanicRequest
from .exceptions import InvalidParam, InvalidRoute
import typing, sys
from functools import reduce
from sanic.router import Router
from .objectify import objectify

class RouteParser:

	def __init__(self, routes: typing.Optional[dict], controllers=None, middlewares=None, app=None):
		self.routes = routes
		self.controllers = controllers
		self.middlewares = middlewares
		self.app = app if app and (isinstance(app, Blueprint) or isinstance(app, Sanic)) else Blueprint('routes')

	def parse(self, routes=None):
		self.routes = routes if routes else self.routes
		if not self.routes:
			raise InvalidRoute("Routes config is required")
		
		self.app.middleware('request')(self._parse_params)

		for route in self.routes:
			name, path, method = self._route(route, self.routes[route])
			self.app.add_route(self.rgetattr(self.controllers, name),path, methods=[method], name=name)
		
		return self.app
		
	def _route(self, name: str, opts: typing.Dict[str, typing.Union[str, list, dict]]):
		controller_name = opts["controller"] if "controller" in opts else name
		mwares = []
		allowed_methods = ["get","post","put","delete","patch"]

		if "before" in opts:
			mwares.extend(opts["before"])
		
		if "after" in opts:
			mwares.extend(opts["after"])
		
		if not self.rhasattr(self.controllers, controller_name):
			# Controller not found
			raise InvalidRoute("Controller not found: %s" % controller_name)
		
		for mware in mwares:
			if not self.rhasattr(self.middlewares, mware):
				# Middleware not found
				raise InvalidRoute("Middleware not found: %s" % mware)
		
		if not "path" in opts:
			# Path not specified
			raise InvalidRoute("Path not specified")

		if not "method" in opts or opts["method"].lower() not in allowed_methods:
			raise InvalidRoute("Invalid request method")
		
		return [controller_name, opts["path"], opts["method"]]

	def _param(self, name: str, opts: dict, route: dict, request: sanicRequest.Request):
		locations = {
			'path': 'match_info',
			'query': 'args',
			'form': 'form',
			'cookies': 'cookies',
			'headers': 'headers',
			'json': 'json'
		}

		default_locations = {
			'get': 'query',
			'post': 'form',
			'delete': 'query',
			'patch': 'form',
			'put': 'form'
		}

		param_location = default_locations[route["method"].lower()]

		param_name = opts["name"] if name in "opts" else name
		error_msg = "Invalid parameter '%s'" % param_name if "help" not in opts else opts["help"]

		if "location" in opts:
			param_location = opts["location"]
		
		if param_location not in locations:
			raise InvalidParam(param_name, "Invalid param location.")

		param_values = getattr(request, locations[param_location])

		if param_name not in param_values:
			if "required" in opts and opts["required"]:
				raise InvalidParam(param_name, error_msg) # Required and not included

			if "default" not in opts:
				return None
			
		param_value = param_values[param_name] if param_name in param_values else opts["default"]

		if isinstance(param_value, list) and param_location != "json" and len(param_value) == 1:
			param_value = param_value[0]

		if "type" in opts and callable(opts["type"]):
			try:
				param_value = opts["type"](param_value)
			except:
				raise InvalidParam(param_name, error_msg)
		
		param_value_length = len(param_value) if isinstance(param_value, str) or isinstance(param_value, list) else param_value

		if "in" in opts and (isinstance(opts["in"], list) or isinstance(opts["in"], dict)) and param_value not in opts["in"]:
			raise InvalidParam(param_name, error_msg)
		
		if "min" in opts and param_value_length < opts["min"]:
			raise InvalidParam(param_name,"The minimum value is {}".format(opts["min"]))
		
		if "max" in opts and param_value_length > opts["max"]:
			raise InvalidParam(param_name,"The maximum value is {}".format(opts["max"]))
		
		if "multiple" in opts and (param_value_length % opts["multiple"]) != 0:
			raise InvalidParam(param_name, "The value must be a multiple of {}".format(opts["multiple"]))
		
		return param_value

	async def _parse_params(self, request: sanicRequest.Request):
		
		request_name = request.name.split(".")[-1]
		if request_name not in self.routes:
			raise InvalidRoute("Request not matching any route.")
		
		opts = self.routes[request_name]

		# Parse Params
		params = {}
		if "params" in opts:
			for param in opts["params"]:
				params[param] = self._param(param, opts["params"][param], opts, request)

		request.ctx.params = objectify(params)

		# Call Middlewares
		if "before" in opts:
			mwares = opts["before"] if isinstance(opts["before"],list) else [opts["before"]]
			for mware in mwares:
				middleware = self.rgetattr(self.middlewares,mware)
				if callable(middleware):
					middleware(request)


	# Recursive attribute getter
	def rgetattr(self,obj, attr, *args):
		def _getattr(obj, attr):
			return getattr(obj, attr, *args)
		return reduce(_getattr, [obj] + attr.split('.'))

	def rhasattr(self,obj, attr, *args):
		def _getattr(obj, attr):
			if not obj:
				return False
			return hasattr(obj, attr, *args)
		return reduce(_getattr, [obj] + attr.split('.'))
		

def make_routes(routes, controllers=None, middlewares=None, app=None):
	parser = RouteParser(routes, controllers, middlewares, app)
	return parser.parse()