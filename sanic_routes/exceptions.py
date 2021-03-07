from sanic.exceptions import InvalidUsage

class InvalidParam(InvalidUsage):
	def __init__(self, field, message="Invalid value for this field."):
		self.field = field
		self.message = message
		self.status = 400
		super().__init__(self.message)
	
	def __str__(self):
	    return '"{}": {}'.format(self.field,self.message)


class InvalidRoute(Exception):
	pass