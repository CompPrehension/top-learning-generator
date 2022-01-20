# rdflib_utils.py

import functools
import re

import rdflib
from rdflib import Graph

# using patched version of SPARQLBurger
from SPARQLBurger.SPARQLQueryBuilder import *

from ns4guestions import *
from chain_utils import builder


# PREFIXES = dict(
#     rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
#     rdfs= "http://www.w3.org/2000/01/rdf-schema#",
#     owl = "http://www.w3.org/2002/07/owl#",
# )



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
            return rdflib.term.URIRef(ns + localname)

class graph_lookup:
    def __init__(self, g, prefixes={}):
        self.g = g
        self.prefixes = prefixes
        self._indexing()
    def _indexing(self):
        self.resources = list(sorted({*self.g.subjects(), *self.g.objects()}))
        self.properties = list(sorted({*self.g.predicates()}))
#     def resourse(self, name):
#         return rdflib.term.URIRef(match_name(name, self.resources, self.prefixes))
#     def property(self, name):
#         return rdflib.term.URIRef(match_name(name, self.properties, self.prefixes))
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
    # rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')

    gl(':reason_kind')
    # rdflib.term.URIRef('http://vstu.ru/poas/code#reason_kind')

    gl('21')
    # rdflib.term.Literal('21', datatype=rdflib.term.URIRef('http://www.w3.org/2001/XMLSchema#integer'))

    gl('ub8bL900C17')
    # rdflib.term.BNode('ub8bL900C17')
    # ^ this Bnode is specific for my graph

    [*qt0.subjects(RDF.type, gl(':expr'))]
    # [rdflib.term.URIRef('http://vstu.ru/poas/code#expr__10'),
    #  rdflib.term.URIRef('http://vstu.ru/poas/code#expr__19'),
    #  rdflib.term.URIRef('http://vstu.ru/poas/code#expr__4')]


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
