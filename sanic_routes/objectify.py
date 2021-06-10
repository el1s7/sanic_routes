# Turn Dicts to objects

class objectify(object):
	def __init__(self, d, recurisve=True):
		for a, b in d.items():
			if isinstance(b, (list, tuple)):
				setattr(self, a, [objectify(x) if isinstance(x, dict) and recurisve else x for x in b])
			else:
				setattr(self, a, (objectify(b) if isinstance(b, dict) and recurisve else b))