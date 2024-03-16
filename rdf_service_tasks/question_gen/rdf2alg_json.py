# rdf2alg_json.py


'''
По графу RDF (онтологии) получить json моей собственной структуры algorithm_json
Также, может понадобиться извлекать трассу (список актов) из RDF.

'''

import rdflib
from rdflib import Graph
from rdflib import RDF
from rdflib.term import Literal, URIRef, BNode
from rdflib.paths import Path

from ns4guestions import *
from rdflib_utils import graph_lookup, pretty_rdf

from fix_alg_names import fix_names_in_graph

COLLECTION_TYPES = (list, tuple,
                    set)  # if default param in GView.get(..., default=...) is one of this types (or a type itself) then list of values instead of single value


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
        # rdflib.URIRef('http://vstu.ru/poas/code#algorithm')

        [*w.items()]
        # [(':entry_point', [GView(<graph>, ':sequence__44')]),
        #  (':stmt_name', ['algorithm__45']),
        #  (':global_code', [GView(<graph>, ':sequence__44')]),
        #  (':id', [45]),
        #  (':algorithm_name', ['1__memcpy_s__1639429224']),
        #  ('rdf:type',
        #   [rdflib.URIRef('http://vstu.ru/poas/code#algorithm'),
        #    rdflib.URIRef('http://www.w3.org/2002/07/owl#NamedIndividual')])]

        w.get('global_code', str)  # non-collection type as default (it could have been `int` or even `None`)
        # GView(<graph>, ':sequence__44')   # sub-View returned

        [*w.values()]
        # ['1__memcpy_s__1639429224',
        #  rdflib.URIRef('http://vstu.ru/poas/code#algorithm'),
        #  45,
        #  'algorithm__45',
        #  rdflib.URIRef('http://www.w3.org/2002/07/owl#NamedIndividual'),
        #  GView(<graph>, ':sequence__44')]

        str(w)
        # 'http://vstu.ru/poas/code#algorithm__45'

        GView(g, ':algorithm__45')  # new instance (again) with string as subject (local name)
        # GView(<graph>, ':algorithm__45')

        GView(g, 'http://vstu.ru/poas/code#stmt_name')  # causes AssertionError as `stmt_name` is a property, not a subject.
        # AssertionError  <...>
        # AssertionError: subject must be in graph `g`, but it is not: rdflib.URIRef('http://vstu.ru/poas/code#stmt_name')
    '''

    def __init__(self, g: Graph, subject: URIRef, gl: graph_lookup = None):
        assert g
        assert subject
        self.g = g
        self.gl = gl or graph_lookup(g, dict(g.namespace_manager.namespaces()))
        if not isinstance(subject, (URIRef, BNode)):
            subject = self.gl(subject)
        assert subject
        assert (subject, None, None) in g, 'subject must be in graph `g`, but it is not: %s' % repr(subject)
        self.s = subject

    def __lt__(self, other):
        return self.g < other.g and self.s < other.s

    def __eq__(self, other):
        return self.g == other.g and self.s == other.s

    def __hash__(self):
        return hash(self.g) ^ hash(self.s)

    # proxy methods to underliyng resource
    def n3(self):
        return self.s.n3()

    def toPython(self):
        return self.s.toPython()

    def __str__(self):
        return self.s.__str__()

    def __repr__(self):
        return str(type(self).__name__) + "(<graph>, %s)" % repr(pretty_rdf(self.s))

    def _get_term(self, node, make_proxy=False):
        if isinstance(node, Literal):
            return node.toPython()
        if make_proxy:
            class_ = type(self)  # support consistent creation in sublasses
            try:
                return class_(self.g, node, self.gl)
            except AssertionError:
                pass
        return node

    def _make_prop(self, key):
        if isinstance(key, (URIRef, Path)):
            pass
        elif isinstance(key, str):
            key = self.gl(key)  # or self.gl(':' + key)
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

    def __setitem__(self, prop, val):
        'add a triple to graph'
        val = val.s if isinstance(val, GView) else val
        return self.g.add((self.s, self._make_prop(prop), val))

    def setvalue(self, prop, val):
        'set single value by prop replacing old triple if any'
        val = val.s if isinstance(val, GView) else val
        return self.g.set((self.s, self._make_prop(prop), val))

    def remove(self, prop=None, val=None):
        'Remove all matching triples from Graph. Note: calling without arguments will remove subject itself.'
        val = val.s if isinstance(val, GView) else val
        self.g.remove((self.s, self._make_prop(prop), val))


def remove_ns_prefix(s):
    s = s.lstrip('<').rstrip('>')
    if '//' in s:
        pos = max(s.rfind('#'), s.rfind('/'))
        return s[pos + 1:]
    return s.partition(':')[2] or s  # `or`: if no prefix, partition[2] will be empty


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


# using output of ctrlstrct_run helper
LEAF_ACTION_CLASSES = [s for s in (
            ['algorithm', ] + ['return', 'break', 'continue', ] + ['while_loop', 'else-if', 'for_loop', 'do_while_loop',
                                                                   'stmt', 'else', 'infinite_loop', 'alternative',
                                                                   'foreach_loop', 'ntimes_loop', 'func', 'if',
                                                                   'expr'] + ['sequence', 'boundary'])]


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
            if k in (':next', ':parent_of', ':has_upcoming', ':hasPartTransitive', ':consequent', ':always_consequent',
                     ':on_false_consequent', ':on_true_consequent'):  # skip some properties
                continue
            ### k = remove_ns_prefix(k)
            if k.endswith('_item'):
                values = _sort_linked_list(values)  # sort according to (s)-->:next-->(o) relations
            # it could be also done via 'item_index' values but these do not always exist.
            values = list(dict.fromkeys(values))  # remove possible duplicates, keeping order
            for i, value in enumerate(values):
                if isinstance(value, URIRef):
                    values[i] = value.n3(self.g.namespace_manager)
                    # if k in ('rdf:type', ) and values[i] not in LEAF_ACTION_CLASSES: # handle types
                    ### print('\tDrop OUT type::::', values[i])
                    # values[i] = None
                    ####
                    if values[i] in (
                    'owl:NamedIndividual', 'owl:Thing', 'Concept', ':first_item', ':last_item', ':linked_list',
                            # ':action', ':loop', ':start_with_cond', ':conditional_loop', ':conditional_loop', ':body_then_cond', ':cond_then_body', ':start_with_init', ':pre_update_loop', ':post_update_loop',
                    ):  # hide this nodes as objects
                        values[i] = None
                    elif values[i]:
                        values[i] = remove_ns_prefix(values[i])
                elif isinstance(value, AlgorithmGraphWalker):
                    # check if is a class with annotations
                    if (class_name := remove_ns_prefix(value.s)) in LEAF_ACTION_CLASSES:
                        values[i] = class_name
                    else:
                        values[i] = value.to_algorithm_json(_visited_nodes)
            values = list(filter(lambda x: x is not None, values))
            if k in ('rdf:type',) and len(values) > 1:  # handle types

                ### print("\t", self.n3(), "'s Values of 'rdf:type':", values, end=' ;  ')
                values = [n for n in LEAF_ACTION_CLASSES if n in values][:1]
            ### print("->:", values)

            if not values:
                ### print('Empty values for key:::', k)
                ### print('             subject:::', self)
                continue
            is_collection = len(values) > 1 or k.endswith('_item')
            val = list(values) if is_collection else values[0]
            ### if not k.endswith('stmt_name') and type(val) not in (dict, list): continue
            d[remove_ns_prefix(k).removesuffix(
                '_item')] = val  # removesuffix is new in Py 3.9  - https://stackoverflow.com/a/18723694/12824563
        return d


def remove_node_from_sequence(node: GView, gl):
    # reassign `:next` links & `item_index` numbers
    body_node = node.value(~gl(':body_item'))  # == subj
    prev_node = node.value(~gl(':next'))
    next_node = node.value(gl(':next'))
    node.remove(':next', next_node)
    body_node.remove(':body_item', node)
    node.remove(None, None)  # del this node completely
    if next_node:
        prev_node.setvalue(':next', next_node)
        # renumber the rest of nodes
        i = node.item_index
        while i is not None and next_node:
            next_node.setvalue(':next_node', i)
            next_node = next_node.value(':next')
            i += 1
    else:
        prev_node.remove(gl(':next'), None)


# Ищем последовательные stmt и удаляем лишние, пока не будет максимум 3 штуки подряд

MAX_STMTS = 3


def shrink_linear_stmts(g, gl, max_stmts=MAX_STMTS):
    """Delete (not merge) subsequent statements when more than 3 occured"""
    STMT_class = gl(':stmt')

    for subj in set(g.subjects(gl(':body_item'), None)):
        stmt_count = sum(((obj, RDF.type, STMT_class) in g) for obj in g.objects(subj, gl(':body_item')))
        if stmt_count > max_stmts:
            # print(subj.n3(), '->', stmt_count, '###', w[':body_item'])

            w = GView(g, subj, gl)
            index2stmt = {node.item_index: node for node in w[':body_item']
                          if isinstance(node, GView) and node.exists(RDF.type, STMT_class)}
            # print(index2stmt)
            indices = sorted(index2stmt.keys())
            # print(indices)
            continuous_sequences = []
            begin_i = indices[0]
            for i1, i2 in zip(indices[0:-1], indices[1:]):
                if i1 + 1 < i2:
                    if i1 - begin_i + 1 > MAX_STMTS:
                        continuous_sequences.append(tuple(range(begin_i, i1 + 1)))
                    begin_i = i2
            if i2 - begin_i + 1 > MAX_STMTS:
                continuous_sequences.append(tuple(range(begin_i, i2 + 1)))

            # was here: `def remove_node_from_sequence`

            # print(continuous_sequences)
            for seq in continuous_sequences:
                to_remove = seq[2:-1]  # retain first 2 and last 1
                print('\t- removing linear statements:', len(to_remove))
                for node_i in to_remove:
                    remove_node_from_sequence(index2stmt[node_i], gl)


def flatten_simple_blocks(g: Graph, gl: graph_lookup):
    """Take up statements within ordinal code block (when not a loop body or if/else branch)"""

    for parent, block in set(g.subject_objects(gl(':body_item') / gl(':body_item') / ~gl(':body_item'))):
        # # subject_objects

        # stmt_count = sum( ((obj, RDF.type, STMT_class) in g) for obj in g.objects(subj, gl(':body_item')))
        # if stmt_count > max_stmts:
        # 	# print(subj.n3(), '->', stmt_count, '###', w[':body_item'])

        if (block, RDF.type, gl(':sequence')) in g:

            w = GView(g, block, gl)
            index2stmt = {
                node.item_index: node.s
                for node in w[':body_item']
                if isinstance(node, GView)  # take all: ##  and node.exists(RDF.type, STMT_class)
            }
            # print(index2stmt)
            indices = sorted(index2stmt.keys())
            # print(indices)

            # remove block extra layer, bring inner actions up

            # handle beginning
            inner_first = index2stmt[indices[0]]
            assert (inner_first, RDF.type, gl(':first_item')) in g, indices;
            if (block, RDF.type, gl(':first_item')) in g:
                pass  # no need to change `first_item` mark
                item_index_last = 0 - 1
            else:
                # re-label beginning
                g.remove((inner_first, RDF.type, gl(':first_item')))
                # re-connect beginning
                prev = g.value(None, gl(':next'), block)
                g.remove((prev, gl(':next'), block))
                g.add((prev, gl(':next'), inner_first))
                item_index_last = g.value(prev, gl(':item_index'), None).toPython();
                item_index_last = item_index_last + 1;

            # move every action up
            for index in indices:
                inner = index2stmt[index]
                g.remove((block, gl(':body_item'), inner))
                g.add((parent, gl(':body_item'), inner))
                item_index_last += 1
                g.set((inner, gl(':item_index'), rdflib.Literal(item_index_last)))

            # handle end
            inner_last = index2stmt[indices[-1]]
            assert (inner_last, RDF.type, gl(':last_item')) in g, indices;
            if (block, RDF.type, gl(':last_item')) in g:
                pass  # no need to change `last_item` mark
            else:
                # re-label beginning
                g.remove((inner_last, RDF.type, gl(':last_item')))
                # re-connect beginning
                next_ = g.value(block, gl(':next'), None)
                g.remove((block, gl(':next'), next_))
                g.add((inner_last, gl(':next'), next_))

                # re-index every remaining actions
                while next_:
                    item_index_last += 1
                    g.set((next_, gl(':item_index'), rdflib.Literal(item_index_last)))
                    next_ = g.value(next_, gl(':next'), None)

        # done.


def ensure_body_sequence(g: Graph, gl: graph_lookup):
    """Inject a sequence wrapping a single action as expected by the domain logic, unless it is already a sequence.
    That transformation is usually not required but may arise sometimes.
    """

    for parent, child in g.subject_objects(gl(':body')):

        if (child, RDF.type, gl(':sequence')) not in g:

            parent_stmt_name = g.value(parent, gl(':stmt_name'), None)
            parent_id = g.value(parent, gl(':id'), None)

            body_stmt_name = parent_stmt_name[0] + "B" + parent_stmt_name[1:]  # insert 'B' next to 1st char
            assert body_stmt_name != parent_stmt_name, parent_stmt_name
            body_id = parent_id + 1
            while (None, gl(':id'), body_id) in g:
                body_id += 1

            # remove old link
            g.remove((parent, gl(':body'), child))

            # add new object
            subj = gl(f':{body_stmt_name}')
            g.add((subj, RDF.type, gl(':sequence')))
            g.add((subj, gl(':id'), body_id))
            g.add((subj, gl(':stmt_name'), body_stmt_name))

            # connect using new node as "proxy"
            g.add((parent, gl(':body'), subj))
            g.add((subj, gl(':body_item'), child))

            print(f"Inserted sequence as body for `{parent_stmt_name}`.")

        # done.


def find_subject_of_type(g, class_uri):
    # class_uri = NS_code.get('algorithm')  # -> 'http://vstu.ru/poas/code#algorithm'
    subjects = list(g.subjects(RDF.type, URIRef(class_uri)))

    assert subjects, 'Graph should contain at least one root of rdf:type : "%s"' % class_uri

    subject = subjects[0]
    return subject


def change_ext(filepath, target_ext='.json'):
    return os.path.splitext(filepath)[0] + target_ext


def graph_2_json(g, root_class=NS_code.get('algorithm')):
    algorithm = find_subject_of_type(g, root_class)
    w = AlgorithmGraphWalker(g, algorithm)  # create now to init w.gl used in fix_names_in_graph()

    # 1. FIX names
    fix_algorithm_graph(g, w.gl)  ####, fix_complex_names=False)

    # 2. EXPORT to algorithm_json
    a_json = w.to_algorithm_json()
    return a_json


def fix_algorithm_graph(g, gl):
    # 1. FIX names
    # fix_names_in_graph(g, gl, fix_complex_names=True)
    fix_names_in_graph(g, gl, fix_complex_names=False)

    # 2.1 REMOVE some nesting levels
    flatten_simple_blocks(g, gl)

    # 2.2 Fix missing sequence blocks for body
    ensure_body_sequence(g, gl)

    # 3. REMOVE some statements
    shrink_linear_stmts(g, gl)

    return g


def ttl_2_json_batch(dir_src=r'c:\Temp2\cntrflowoutput_v4', dest_dir=r'c:\Temp2\cntrflowoutput_v4_json',
                     ext_pattern='*.ttl'):
    'convert all .ttl files in DIR_SRC to "algorithm" *.json into DEST_DIR'
    from glob import glob
    import json

    FORMAT_IN = "turtle"

    def read_rdf(*files, rdf_format=None):
        g = rdflib.Graph()
        for file_in in files:
            g.parse(location=file_in, format=rdf_format)
        return g

    root_class = NS_code.get('algorithm')

    for i, fp in enumerate(glob(os.path.join(dir_src, ext_pattern))):
        print(f'[{i + 1}]\t', fp, end='\t')

        g = read_rdf(fp, rdf_format=FORMAT_IN)

        a_json = graph_2_json(g, root_class)
        # algorithm = find_subject_of_type(g, root_class)
        # w = AlgorithmGraphWalker(g, algorithm)  # create now to init w.gl used in fix_names_in_graph()

        # # 1. FIX names
        # fix_names_in_graph(g, w.gl, fix_complex_names=False)

        # # 2. REMOVE some statements
        # shrink_linear_stmts(g, w.gl)

        # # 3. EXPORT to algorithm_json
        # a_json = w.to_algorithm_json()

        out = change_ext(
            os.path.join(
                dest_dir,
                os.path.split(fp)[1]),
            '.json')

        with open(out, mode='w') as f:
            data = json.dump(a_json, f, indent=1)
        print('OK')


if __name__ == '__main__':

    if 0:
        import os.path

        ttl_2_json_batch(dir_src=r'c:/Temp2/cntrflowoutput_v6', dest_dir=r'c:/Temp2/cntrflowoutput_v6_json')
        exit(0)

    # test that it works
    # see also Jupyter notebook at: /owlready/rdflib.Graph wrapper

    # prepare the data

    # qg_path = r'c:\Temp2\cntrflowoutput_v4\1__memcpy_s__1639429224.ttl'
    # qg_path = r'c:\Temp2\cntrflowoutput_v4\2__memmove_s__1639429224.ttl'
    # qg_path = r'c:\Temp2\cntrflowoutput_v4\28__avl_tree_insert__1639429224.ttl'
    qg_path = r'c:\Temp2\cntrflowoutput_v7\nk_style_from_table__4764473337220020718__1643441943.ttl'

    g = Graph().parse(location=qg_path, format='turtle')

    # find root of future json tree

    from rdflib import RDF

    root_class = NS_code.get('algorithm')  # 'http://vstu.ru/poas/code#algorithm'
    algorithm = find_subject_of_type(g, root_class)

    # create GraphView (domain-specific walker)

    w = AlgorithmGraphWalker(g, algorithm)

    # construct dict from Graph

    a_json = w.to_algorithm_json()
    # print(a_json)

    # export as pretty-formatted JSON

    import json

    out = r'../../../c_owl/code_gen/nk_style_from_table.json'
    with open(out, mode='w') as f:
        data = json.dump(a_json, f, indent=2)

    print('done.')
