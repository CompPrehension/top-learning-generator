# rdflib_utils.py

import functools
import itertools
import re

import rdflib
from rdflib import Graph, RDF
from rdflib.term import URIRef, Literal

# using patched version of SPARQLBurger
from SPARQLBurger.SPARQLQueryBuilder import *

from ns4guestions import *
from chain_utils import builder


# PREFIXES = dict(
#     rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
#     rdfs= "http://www.w3.org/2000/01/rdf-schema#",
#     owl = "http://www.w3.org/2002/07/owl#",
# )


class TripleOverrider:
	def __init__(self, triple:tuple, s=None, p=None, o=None, self_node=None):
		self.triple = triple
		self.s = s
		self.p = p
		self.o = o
		self.self_node = self_node
	def __str__(self): return f'<TripleOverrider {repr(self.triple)}, ==>> ({self.s}, {self.p}, {self.o})>'
	__repr__ = __str__
	@staticmethod
	def rdf_class_uri(ns:NamespaceUtil=NS_oop):
		return ns.get('TripleOverrider')
	@classmethod
	def rdf_class_UriRef(cls, ns:NamespaceUtil=NS_oop):
		return URIRef(cls.rdf_class_uri(ns))
	def adds(self) -> bool:
		'otherwise removes old triple only'
		return any([self.s, self.p, self.o])
	def new_triple(self):
		return ((
					self.s or self.triple[0],
					self.p or self.triple[1],
					self.o or self.triple[2],
				)
				if self.adds() else None)
	def __eq__(self, other):
		return (isinstance(other, TripleOverrider)
			and self.triple == other.triple
			and self.s == other.s
			and self.p == other.p
			and self.o == other.o)
	def __ne__(self, other): return not self.__eq__(other)
	def incompatible_with(self, other):
		return (isinstance(other, TripleOverrider)
			and self.triple == other.triple
			and (	self.s != other.s
				 or self.p != other.p
				 or self.o != other.o))
	def write_as_triples(self, g:Graph):
		g.bind('oop', NS_oop.get())
		for i in itertools.count():
			subj = URIRef(self.rdf_class_uri() + '#%d' % i)
			if (subj, None, None) not in g:
				break
		g.add((subj, RDF.type,  self.rdf_class_UriRef()))
		g.add((subj, URIRef(NS_oop.get('old_subject')),   self.triple[0]))
		g.add((subj, URIRef(NS_oop.get('old_predicate')), self.triple[1]))
		g.add((subj, URIRef(NS_oop.get('old_object')),    self.triple[2]))
		if self.s:
			g.add((subj, URIRef(NS_oop.get('new_subject')),   self.s))
		if self.p:
			g.add((subj, URIRef(NS_oop.get('new_predicate')), self.p))
		if self.o:
			g.add((subj, URIRef(NS_oop.get('new_object')),    self.o))
	@classmethod
	def create_from_graph(cls, tor_node:URIRef, g:Graph):
		return TripleOverrider(
			triple=(
				g.value(tor_node, URIRef(NS_oop.get('old_subject')), None),
				g.value(tor_node, URIRef(NS_oop.get('old_predicate')), None),
				g.value(tor_node, URIRef(NS_oop.get('old_object')), None),
			),
			s=g.value(tor_node, URIRef(NS_oop.get('new_subject')), None),
			p=g.value(tor_node, URIRef(NS_oop.get('new_predicate')), None),
			o=g.value(tor_node, URIRef(NS_oop.get('new_object')), None),
			self_node=tor_node,
		)

	def apply_on_graph(self, g:Graph, remove_self=True):
		if not self.s and not self.p and self.o:
			g.set((*self.triple[:2], self.o))
		else:
			if all(self.triple):  # avoid deleting patterns with 'None's
				g.remove(self.triple)
			new_triple = self.new_triple()
			if new_triple and all(new_triple):
				g.add(new_triple)
		if remove_self and self.self_node:
			# remove all triples about this TripleOverrider
			g.remove((self.self_node, None, None))





def match_name(localname, uris: list, prefix2ns={}):
    uri = expand_prefix(localname, prefix2ns) or find_uri(localname, uris)
    assert uri, "cannot match localname '%s'" % localname
    return uri

def find_uri(localname, uris: list):
    sep_pos = (len(localname) + 1)
    for uri in uris:
        if str(uri) == localname:
            return uri
        if uri.endswith(localname) and len(uri) >= sep_pos:
            if uri[-sep_pos] in "/#":
                return uri

def expand_prefix(name, prefix2ns={}):
    if ':' in name:
        pfx, localname = name.partition(':')[0:3:2]  # get [0] & [2]
        ns = prefix2ns.get(pfx, None) or prefix2ns.get(pfx + ':', None)
        if ns:
            return rdflib.URIRef(ns + localname)

class graph_lookup:
    def __init__(self, g, prefixes={}):
        self.g = g
        self.prefixes = prefixes
        self._indexing()
    def _indexing(self):
        self.resources = list(sorted({*self.g.subjects(), *self.g.objects()}))
        self.properties = list(sorted({*self.g.predicates()}))
#     def resourse(self, name):
#         return rdflib.URIRef(match_name(name, self.resources, self.prefixes))
#     def property(self, name):
#         return rdflib.URIRef(match_name(name, self.properties, self.prefixes))
    @functools.lru_cache(maxsize=None)
    def __call__(self, name):
        return (match_name(name, self.properties + self.resources, self.prefixes))


### pretty_rdf ###

def pretty_rdf(s, prefixes:dict=PREFIXES):
    'Simple-replace approach to make rdflib.*.n3() serializations look better'
    s = str(s)
    for p, ns in prefixes.items():
        s = s.replace(ns, p.rstrip(':') + ':')
    s = re.sub(r'rdflib\.term\.URIRef\(([\'"])([^)]+)\1\)', lambda m: m[2], s)
    s = re.sub(r'rdflib\.term\.BNode\(([\'"])([^)]+)\1\)', lambda m: '_:' + m[2], s)
    s = re.sub(r'rdflib\.term\.Literal\(([^)]+)\)', lambda m: m[1], s)
    return s




def graph_as_insert_query(g: Graph, named_graph=None, additional_namespaces={}):
    # named_graph='<ng/555>'
    update_query = SPARQLUpdateQuery()

    for p, ns in dict(additional_namespaces).items():
        g.namespace_manager.bind(p, ns, override=False)

    for pfx, url in g.namespaces():
        # Add a prefix
        update_query.add_prefix(
            prefix=Prefix(prefix=pfx, namespace=str(url))
        )

    triples = g.triples((None, None, None))
    ### triples = [*g.triples((None, None, None))][:10]

    # Create a graph pattern for the INSERT part and add a triple
    update_query.set_insert_pattern(
            builder(SPARQLGraphPattern(graph_name=named_graph)).add_triples(
                triples=[Triple(*(e.n3(g.namespace_manager) for e in t)) for t in triples]
            ).builder
    )
    # patch keyword
    text = update_query.get_text()
    text = text.replace('INSERT ', 'INSERT DATA ', 1)

    # print(text)
    return text

# print(graph_as_insert_query(qg, URI('n.g/555')))


def uploadGraph(gUri, g, fuseki_update):
    clearGraphSparql = "CLEAR SILENT GRAPH <" + gUri + ">"
    insertGraphQuery = graph_as_insert_query(g, "<" + gUri + ">", PREFIXES)
    #### fuseki_update.insert_graph < no 'named graph' option ...
    print(clearGraphSparql)
    res = fuseki_update.run_sparql(clearGraphSparql)
    print('SPARQL: clear  graph response code:', res.response.code)
    res = fuseki_update.run_sparql(insertGraphQuery)
    print('SPARQL: create graph response code:', res.response.code)
    # return res

# uploadGraph('http://n.g/555', qg, fuseki_update)


if __name__ == '__main__':
    PREFIXES[''] = 'http://vstu.ru/poas/code#'

    gl = graph_lookup(some_rdflib_Graph, PREFIXES)

    gl("rdf:type")
    # rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')

    gl(':reason_kind')
    # rdflib.URIRef('http://vstu.ru/poas/code#reason_kind')

    gl('21')
    # rdflib.Literal('21', datatype=rdflib.URIRef('http://www.w3.org/2001/XMLSchema#integer'))

    gl('ub8bL900C17')
    # rdflib.BNode('ub8bL900C17')
    # ^ this Bnode is specific for my graph

    [*qt0.subjects(RDF.type, gl(':expr'))]
    # [rdflib.URIRef('http://vstu.ru/poas/code#expr__10'),
    #  rdflib.URIRef('http://vstu.ru/poas/code#expr__19'),
    #  rdflib.URIRef('http://vstu.ru/poas/code#expr__4')]


    # str -> URI/BNode -> str
    pretty_rdf(gl('ub8bL900C17'))
    # 'ub8bL900C17'

    # using pretty_rdf() for printing out BNodes, URIRefs and Literals (example)
    from itertools import chain
    for s in qt0.subjects(None, gl(':AltEndAfterBranch')):
        print(*(pretty_rdf(t) for t in
                chain(qt0.triples((s, None, None)), qt0.triples((None, None, s)))
               ), sep='\n')
    # >>>
    '''
    (_:ub8bL900C17, :reason_kind, :AltEndAfterBranch)
    (_:ub8bL900C17, :string_placeholder, 'alternative__21')
    (_:ub8bL900C17, rdf:type, owl:Thing)
    (_:ub8bL900C17, :from_reason, _:f151d8eff5fb741be804e3dc02463446eb18)
    (_:ub8bL900C17, :field_ALT, 'alternative__21')
    (_:ub8bL900C17, rdf:type, :boundary)
    (_:f151d8eff5fb741be804e3dc02463446eb23, :to_reason, _:ub8bL900C17)
    (_:ub8bL1199C17, :reason_kind, :AltEndAfterBranch)
    (_:ub8bL1199C17, rdf:type, :boundary)
    (_:ub8bL1199C17, rdf:type, owl:Thing)
    (_:ub8bL1199C17, :string_placeholder, 'alternative__12')
    (_:ub8bL1199C17, :field_ALT, 'alternative__12')
    (_:ub8bL1199C17, :from_reason, _:f151d8eff5fb741be804e3dc02463446eb12)
    (_:f151d8eff5fb741be804e3dc02463446eb36, :to_reason, _:ub8bL1199C17)
    (_:ub8bL411C17, rdf:type, owl:Thing)
    (_:ub8bL411C17, :string_placeholder, 'alternative__6')
    (_:ub8bL411C17, rdf:type, :boundary)
    (_:ub8bL411C17, :field_ALT, 'alternative__6')
    (_:ub8bL411C17, :from_reason, _:f151d8eff5fb741be804e3dc02463446eb28)
    (_:ub8bL411C17, :reason_kind, :AltEndAfterBranch)
    (_:f151d8eff5fb741be804e3dc02463446eb29, :to_reason, _:ub8bL411C17)
    '''
