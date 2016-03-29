import cpy2py.utility.exceptions


class TwinterpeterException(cpy2py.utility.exceptions.CPy2PyException):
	"""Exception in Twinterpeter internals"""
	pass


class TwinterpeterUnavailable(TwinterpeterException, RuntimeError):
	"""A requested Twinterpeter is not available, e.g. because it has not bee started"""
	def __init__(self, twin_id):
		super(TwinterpeterException, self).__init__("Twinterpeter '%s' not available" % twin_id)
		self.twin_id = twin_id
