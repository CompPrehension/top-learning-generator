# rdf2alg_json.py


'''
По графу RDF (онтологии) получить json моей собственной структуры algorithm_json
Также, может понадобиться извлекать трассу (список актов) из RDF.

'''


import rdflib
from rdflib import Graph
from rdflib.term import Literal, URIRef, BNode
from rdflib.paths import Path

from ns4guestions import *
from rdflib_utils import graph_lookup, pretty_rdf


COLLECTION_TYPES = (list, tuple, set)  # if default param in GView.get(..., default=...) is one of this types (or a type itself) then list of values instead of single value


class GView:
	'''GraphView: Proxy to resource in a rdflib.Graph. Mimics `dict` type and provides "dict-of-lists"-like access to Graph data

		# Usage examples:

		g = rdflib.Graph().parse(location="some_file", format='turtle')

		w = GView(g, URIRef('http://vstu.ru/poas/code#algorithm__45'), gl)  # subject must be in g; gl is optional.

		w
		# GView(<graph>, ':algorithm__45')

		w['algorithm_name']   # returns collection by default
		# ['1__memcpy_s__1639429224']

		w.algorithm_name    # returns single value by default
		# '1__memcpy_s__1639429224'

		[*w.keys()]
		# [':entry_point', ':stmt_name', ':global_code', ':id', ':algorithm_name', 'rdf:type']

		w.value('rdf:type')
		# rdflib.term.URIRef('http://vstu.ru/poas/code#algorithm')

		[*w.items()]
		# [(':entry_point', [GView(<graph>, ':sequence__44')]),
		#  (':stmt_name', ['algorithm__45']),
		#  (':global_code', [GView(<graph>, ':sequence__44')]),
		#  (':id', [45]),
		#  (':algorithm_name', ['1__memcpy_s__1639429224']),
		#  ('rdf:type',
		#   [rdflib.term.URIRef('http://vstu.ru/poas/code#algorithm'),
		#    rdflib.term.URIRef('http://www.w3.org/2002/07/owl#NamedIndividual')])]

		w.get('global_code', str)  # non-collection type as default (it could have been `int` or even `None`)
		# GView(<graph>, ':sequence__44')   # sub-View returned

		[*w.values()]
		# ['1__memcpy_s__1639429224',
		#  rdflib.term.URIRef('http://vstu.ru/poas/code#algorithm'),
		#  45,
		#  'algorithm__45',
		#  rdflib.term.URIRef('http://www.w3.org/2002/07/owl#NamedIndividual'),
		#  GView(<graph>, ':sequence__44')]

		str(w)
		# 'http://vstu.ru/poas/code#algorithm__45'

		GView(g, ':algorithm__45')  # new instance (again) with string as subject (local name)
		# GView(<graph>, ':algorithm__45')

		GView(g, 'http://vstu.ru/poas/code#stmt_name')  # causes AssertionError as `stmt_name` is a property, not a subject.
		# AssertionError  <...>
		# AssertionError: subject must be in graph `g`, but it is not: rdflib.term.URIRef('http://vstu.ru/poas/code#stmt_name')
	'''
	def __init__(self, g: Graph, subject: URIRef, gl: graph_lookup=None):
		assert g
		assert subject
		self.g = g
		self.gl = gl or graph_lookup(g, dict(g.namespace_manager.namespaces()))
		if not isinstance(subject, (URIRef, BNode)):
			subject = self.gl(subject)
		assert subject
		assert (subject, None, None) in g, 'subject must be in graph `g`, but it is not: %s' % repr(subject)
		self.s = subject
	def __lt__(self, other): return self.g < other.g and self.s < other.s
	def __eq__(self, other): return self.g == other.g and self.s == other.s
	def __hash__(self): return hash(self.g) ^ hash(self.s)
	# proxy methods to underliyng resource
	def n3(self): return self.s.n3()
	def toPython(self): return self.s.toPython()
	def __str__(self): return self.s.__str__()
	def __repr__(self): return str(type(self).__name__) + "(<graph>, %s)" % repr(pretty_rdf(self.s))
	def _get_term(self, node, make_proxy=False):
		if isinstance(node, Literal):
			return node.toPython()
		if make_proxy:
			class_ = type(self)  # support consistent creation in sublasses
			try: return class_(self.g, node, self.gl)
			except AssertionError: pass
		return node
	def _make_prop(self, key):
		if isinstance(key, (URIRef, Path)):
			pass
		elif isinstance(key, str):
			key = self.gl(key) # or self.gl(':' + key)
		return key
	def __getitem__(self, prop):
		return self.get(prop)
	def __getattr__(self, prop):
		'get single value by prop'
		return self.value(prop)
	def value(self, prop, proxy_for_resource=True):
		'get first value or first subject reachable through property `prop`'
		## assert prop  # << allow None ??
		for r in self.g.objects(self.s, self._make_prop(prop)):
			return self._get_term(r, proxy_for_resource)
		return None
		# raise IndexError('Inconsistent multiple objects to assess via single-value getter')
	def exists(self, prop, value=None):
		return (self.s, self._make_prop(prop), value) in self.g
	def get(self, prop, default=(), proxy_for_resource=True):
		'get single value or all values as list, depending on `default` type (scalar value or built-in collection)'
		need_all = (isinstance(default, COLLECTION_TYPES) or default in COLLECTION_TYPES)
		if not need_all:
			return self.value(prop, proxy_for_resource) or default
		results = [
			self._get_term(r, proxy_for_resource)
			for r in self.g.objects(self.s, self._make_prop(prop))
		]
		return results
	def keys(self, with_value=None):
		return {pretty_rdf(p) for p in self.g.predicates(self.s, with_value)}
	def items(self):
		for key in self.keys():
			yield (key, self.get(key))
	def values(self):
		res_set = set()
		for key in self.keys():
			res_set.update(self.get(key))
		return res_set



def remove_ns_prefix(s):
	return s.partition(':')[2] or s  # if no prefix, partition[2] will be empty

def _sort_linked_list(array, next_prop=URIRef(NS_code.get('next'))):
	"Sort an arrays of AlgorithmGraphWalker instances according to (s)-->:next-->(o) relations"
	def cmp_to_key(prop_name):
		'Convert a cmp= function into a key= function'
		class K:
			def __init__(self, obj, *_):
				self.obj = obj
			def __lt__(self, other):
				return self.obj.exists(prop_name, other.obj.s)
			def __gt__(self, other):
				return other.obj.exists(prop_name, self.obj.s)
			def __eq__(self, other):
				return self.obj == other.obj
			__le__ = __lt__
			__ge__ = __gt__
			def __ne__(self, other):
				return self.obj != other.obj
		return K

	array.sort(key=cmp_to_key(next_prop * '+'))  # transitive property Path
	return array


class AlgorithmGraphWalker(GView):
	# def __init__(self, g: Graph, subject: URIRef, gl: graph_lookup=None):
	# 	super().__init__(g, subject, gl)
	def to_algorithm_json(self, _visited_nodes=()):
		'convert to domain-specific dict-list structure'
		_visited_nodes = _visited_nodes or {}  # AlgorithmGraphWalker -> dict
		if self in _visited_nodes:
			return _visited_nodes[self]
		d = {}
		_visited_nodes[self] = d  # assign a reference
		for k, values in self.items():
			if k in (':next', ):  # skip some properties
				continue
			### k = remove_ns_prefix(k)
			if k.endswith('_item'):
				values = _sort_linked_list(values)  # sort according to (s)-->:next-->(o) relations
						# it could be also done via 'item_index' values but these do not always exist.
			for i, value in enumerate(values):
				if isinstance(value, URIRef):
                    values[i] = value.n3(g.namespace_manager)
                    if values[i] in ('owl:NamedIndividual', ':first_item', ':last_item', ':linked_list'):  # hide this nodes as objects
                        values[i] = None
                    else:
                        values[i] = remove_ns_prefix(values[i])
				if isinstance(value, AlgorithmGraphWalker):
					values[i] = value.to_algorithm_json(_visited_nodes)
			values = list(filter(lambda x: x is not None, values))
			is_collection = len(values) > 1 or k.endswith('_item')
			val = list(values) if is_collection else values[0]
			### if not k.endswith('stmt_name') and type(val) not in (dict, list): continue
			d[remove_ns_prefix(k).removesuffix('_item')] = val  # removesuffix is new in Py 3.9  - https://stackoverflow.com/a/18723694/12824563
		return d




if __name__ == '__main__':
	# test that it works
	# see also Jupyter notebook at: /owlready/rdflib.Graph wrapper


	# prepare the data

	# qg_path = r'c:\Temp2\cntrflowoutput_v4\1__memcpy_s__1639429224.ttl'
	# qg_path = r'c:\Temp2\cntrflowoutput_v4\2__memmove_s__1639429224.ttl'
	qg_path = r'c:\Temp2\cntrflowoutput_v4\28__avl_tree_insert__1639429224.ttl'

	g = Graph().parse(location=qg_path, format='turtle')


	# find root of future json tree

	from rdflib import RDF
	root_class = NS_code.get('algorithm')  # 'http://vstu.ru/poas/code#algorithm'
	algorithms = list(g.subjects(RDF.type, URIRef(root_class)))

	assert algorithms, 'Graph should contain at least one root of rdf:type : "%s"' % root_class

	algorithm = algorithms[0]


	# create GraphView (domain-specific walker)

	w = AlgorithmGraphWalker(g, algorithm)


	# construct dict from Graph

	a_json = w.to_algorithm_json()
	# print(a_json)


	# export as pretty-formatted JSON

	import json
	out = r'../../../c_owl/code_gen/ctrlflow_v4_28-alg.json'
	with open(out, mode='w') as f:
		data = json.dump(a_json, f, indent=2)

	print('done.')
