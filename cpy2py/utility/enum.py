

__all__ = ['Unique']


class Unique(object):
	"""
	Collectionless unique element

	This is a beautification of using :py:class:`object` as unique identifiers.
	It offers configurable str and repr for verbosity. In addition, it supports
	equality comparisons.
	"""
	def __init__(self, name="UniqueObj", representation=None):
		self.name = name
		self.representation = representation or name

	def __str__(self):
		return self.name

	def __repr__(self):
		return "<%s@%d>"%(self.representation, id(self))

	def __eq__(self, other):
		return self is other
	def __ne__(self, other):
		return not self is other
	def __gt__(self, other):
		return NotImplemented
	def __lt__(self, other):
		return NotImplemented
	def __ge__(self, other):
		return NotImplemented
	def __le__(self, other):
		return NotImplemented
