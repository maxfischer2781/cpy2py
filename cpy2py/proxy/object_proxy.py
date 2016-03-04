import cpy2py.twinterpreter.kernel


class TwinProxy(object):
	"""
	Proxy for instances existing in the twinterpreter
	"""
	def __init__(self, instance_id, kernel_id, members, methods):
		self.kernel_id = kernel_id
		self.instance_id = instance_id
		self.members = members
		self.methods = methods

	# value member access
	def __getattr__(self, item):
		pass


class TwinMeta(type):
	"""
	Metaclass for Twin objects

	This meta-class allows using regular class definitions. In the native
	interpreter, the class is accessible directly. In any other, a proxy is
	created with all class members transformed to appropriate calls to the
	twinterpeter master.
	"""
	def __new__(mcs, name, bases, class_dict):
		# find out which interpeter scope is appropriate for us
		try:
			twin_id = class_dict['__twin_id__']
		except KeyError:
			for base_class in bases:
				try:
					twin_id = base_class.__twin_id__
				except AttributeError:
					pass
				else:
					break
			else:
				twin_id = cpy2py.twinterpreter.kernel.TWIN_MASTER
			class_dict['__twin_id__'] = twin_id
		# if we are in the appropriate interpeter, proceed as normal
		if cpy2py.twinterpreter.kernel.is_twinterpreter(twin_id):
			return type.__new__(mcs, name, bases, class_dict)
		# if we are in any other interpeter, create a proxy object

