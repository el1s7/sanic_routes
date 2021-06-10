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
		self.route_wares = {}
		
		if not self.routes:
			raise InvalidRoute("Routes config is required")
		
		self.app.middleware('request')(self._parse_params)

		for route in self.routes:
			name, path, method = self._route(route, self.routes[route])
			self.app.add_route(self.rgetattr(self.controllers, name),path, methods=[method], name=name)
		
		return self.app
		
	def _route(self, name: str, opts: typing.Dict[str, typing.Union[str, list, dict]]):
		controller_name = opts["controller"] if "controller" in opts else name
		
		allowed_methods = ["get","post","put","delete","patch"]
		method = "get" if not "method" in opts or not opts["method"] else opts["method"].lower()
		
		before_wares = []
		
		before_wares_key = "request" if "request" in "opts" else "before"
		
		after_wares = []
		after_wares_key = "response" if "response" in "opts" else "after"
		
		if method not in allowed_methods:
			raise InvalidRoute("Invalid route request method: %s" % method)
		
		if not "path" in opts:
			# Path not specified
			raise InvalidRoute("Path not specified")
			
		if not self.rhasattr(self.controllers, controller_name):
			# Controller not found
			raise InvalidRoute("Route controller not found: %s" % controller_name)
		
		if before_wares_key in opts:
			before_wares.extend(opts[before_wares_key] if isinstance(opts[before_wares_key],list) else [opts[before_wares_key]])
		
		if after_wares_key in opts:
			after_wares.extend(opts[after_wares_key] if isinstance(opts[after_wares_key],list) else [opts[after_wares_key]])
		
		for before_ware in before_wares:
			if not self.rhasattr(self.middlewares, before_ware):
				# Middleware not found
				raise InvalidRoute("Route before middleware not found: %s" % before_ware)
				
		for after_ware in after_wares:
			if not self.rhasattr(self.middlewares, after_ware):
				# Middleware not found
				raise InvalidRoute("Route after middleware not found: %s" % after_ware)
			callable_ware = self.rgetattr(self.middlewares, after_ware)
			if not callable(callable_ware):
				raise InvalidRoute("Route after middleware is not a function: %s" % callable_ware)

			self.app.middleware('response')(callable_ware)
		
		self.route_wares[name] = {
			'before': before_wares,
			'after': after_wares
		}
		
		return [controller_name, opts["path"], method]

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
		
		name = request.name.split(".")[-1]
		if name not in self.routes:
			raise InvalidRoute("Request not matching any route.")
		
		opts = self.routes[name]

		# Parse Params
		params = {}
		if "params" in opts:
			for param in opts["params"]:
				params[param] = self._param(param, opts["params"][param], opts, request)

		request.ctx.params = objectify(params, False)

		# Call Middlewares
		if name in self.route_wares:
			for before_ware in self.route_wares[name]['before']:
				middleware = self.rgetattr(self.middlewares,before_ware)
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