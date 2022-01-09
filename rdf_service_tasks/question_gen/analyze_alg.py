# analyze_alg.py

from collections import defaultdict
from functools import reduce
from itertools import product, starmap
from operator import add, eq
from random import shuffle

import networkx as nx
import rdflib
from rdflib import Graph, RDF

from ns4guestions import *
from rdflib_utils import pretty_rdf


LOOP_MAX_ITERATIONS = 3



class jsObj(dict):
    'JS-object-like dict (access to "foo": obj.foo as well as obj["foo"])'
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

# >>> d = jsObj()
# >>> d.ax = '123'
# >>> d
    # {'ax': '123'}

class expr_bool_values:  # `gen`
    def __init__(self, delay=0, active=1, safe_value=False):
        self.safe_value = safe_value
        self.delay = delay
        self.active = active
        self.i = 0 # state for next()
    def get(self, index):
        if index < self.delay or index >= (self.delay + self.active):
            return self.safe_value
        else:
            return not self.safe_value
    def __len__(self): return (self.delay + self.active) + 1
    def __iter__(self): self.i = 0; return self
    def __next__(self):
        self.i += 1
        return self.get(self.i - 1)
    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.start, index.stop, index.step
            if start is None: start = 0
            if stop is None: stop = (self.delay + self.active) # + 1
            elif stop < 0: stop = (self.delay + self.active) + stop # + 1
            if step is None: step = 1
            return [self.get(i) for i in range(start, stop, step)]
        return self.get(index)
    ## def __list__(self): return self[:len(self)]
    def __contains__(self, other): return all(starmap(eq, zip(self, other[:])))
    def __str__(self): return str(self[:])
    def __repr__(self): return f"expr_bool_values(delay={self.delay}, active={self.active}, safe_value={self.safe_value})"

# itvs = expr_bool_values(1, 2)
# [itvs[i] for i in range(10)]
# >>> [False, True, True, False, False, False, False, False, False, False]


class Way(jsObj):
    '''
    {'len': int, 'depth': int,
     'vals': {'cond_name': (bool, bool, ...)},
     'acts': list,
     'reasons': frozenset(),
     'possible_violations': frozenset(),
    }
    '''
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.len  = self.get('len', 0)
        self.depth  = self.get('depth', 0)
        self.vals = self.get('vals', None) or jsObj()
        self.acts = self.get('acts', None) or ()
    @staticmethod
    def join_acts(a1, a2):
        if a1 and a2 and a1[-1] == a2[0]:
            a2 = a2[1:]
        return a1 + a2
    def __add__(self, other):
        return Way({'len': self.len + other.len,
         'depth': max(self.depth, other.depth),  # depth does not sum
         'vals': {cnd: self.vals.get(cnd, ()) + other.vals.get(cnd, ())
                  for cnd in set([*self.vals.keys(), *other.vals.keys()])},
         'acts': self.join_acts(self.acts, other.acts),
         'reasons': self.get('reasons', frozenset()) | other.get('reasons', frozenset()),
         'possible_violations': self.get('possible_violations', frozenset()) | other.get('possible_violations', frozenset()),
        })

# >>> w = Way()
# >>> w += Way()
# >>> w
    # {'len': 0,
    #  'depth': 0,
    #  'vals': {},
    #  'acts': (),
    #  'reasons': frozenset(),
    #  'possible_violations': frozenset()}


def way_from_transition(bound1, value_gen=None, g=None, gl=None) -> (Way, rdflib.term.Identifier):
    way = Way()
    prop_name=':always_consequent'
    bnd2 = g.value(bound1, gl(prop_name), None)
    if not bnd2:
        # handle
        assert value_gen
        value = next(value_gen)
        prop_name = {
            True:  ':on_true_consequent',
            False: ':on_false_consequent',
          }.get(value)
        bnd2 = g.value(bound1, gl(prop_name), None)
        if not bnd2:
            raise NotImplementedError("3 types of '*consequent' transitions supported so far.")

        cond_node = g.value(bound1, gl(':boundary_of'), None)
        assert cond_node
        cond_name = g.value(cond_node, gl(':stmt_name'), None)
        assert cond_name
        cond_name = str(cond_name)
        way.vals[cond_name] = (value, )

    # get reason info
    R = None
    for r_node in g.objects(bound1, gl(':to_reason'), ):
        # print('# r_node =', r_node)
        if (r_node, gl(':from_reason'), bnd2) in g:
            R = r_node
            break
    #### assert R, ('No reason node for boundaries: %s, %s' % (bound1, bnd2))  # return (way, None);
    if R:
        way.reasons = frozenset(
            map(NS_code.localize, g.objects(R, gl(':reason_kind')))
        )
        way.possible_violations = frozenset(
            map(NS_code.localize, g.objects(R, gl(':possible_violation')))
        )
    way.len = 1
    way.depth = 1
    way.acts = (bound1, bnd2)
    return (way, bnd2)


def combine_ways_parts(way_parts: list):
    return [reduce(add, comb) for comb in product(*way_parts)]


def nontrivial_ways(ways: list, max_similar=2, length_ratio=0.34, print_report=True):
    # traces with same violations
    groups = defaultdict(list)

    for way in ways:
        viols = way.possible_violations
        ## print(viols)
        groups[viols].append(way)

    # filter out exessive traces
    selected_trace_configs = []

    for ways in groups.values():
        if len(ways) <= max_similar:
            selected_trace_configs.extend(ways)
            continue
        lengths = [tc.len for tc in ways]
        Lmin = min(lengths)
        Lmax = max(lengths)
        treshold = Lmin + length_ratio * (Lmax - Lmin)   ## wouldn't `Lmin * 1.34` be better ???
        shortest = [tc for tc in ways if tc.len <= treshold]
        if len(shortest) > max_similar:
            shuffle(shortest)
            if print_report: print(f'    ... truncating a group of {len(shortest)} to {max_similar} traces')
            shortest = shortest[:max_similar]
        else:
            if print_report: print(f'    ... selected {len(shortest)} of {len(ways)} traces')
        selected_trace_configs.extend(shortest)

    if print_report and len(selected_trace_configs) > max_similar: print('    ... %d total traces selected' % len(selected_trace_configs))
    return selected_trace_configs


def ways_through(st: rdflib.term.URIRef, g: Graph, gl=None):
    ''' -> [way1, way2, ...]
    '''
    gl = gl or graph_lookup(g)
    ways = list()

    if (st, RDF.type, gl(':algorithm')) in g:
        # bound, not statement (algorithm begin only)
        # handle special case now
        way_step, bound = way_from_transition(st, None, g, gl)

        entry_st = g.value(bound, gl(':begin_of'), None)
        if entry_st:
            deeper_ways = ways_through(entry_st, g, gl)
            ## not here ## for way in deeper_ways: way.depth += 1
            way_parts = [[way_step], deeper_ways]

            ways = combine_ways_parts(way_parts)
            return ways


    if (st, RDF.type, gl(':loop')) in g:
        safe_value = False  # what to use in condition to aviod an infinite loop
        if (st, RDF.type, gl(':inverse_conditional_loop')) in g:  ### TODO: make sure of loop type
            safe_value = True
        is_post_conditional = (st, RDF.type, gl(':start_with_body')) in g
        tactics = [(0, i, safe_value) for i in range(LOOP_MAX_ITERATIONS + 1 - int(is_post_conditional))]

    elif (st, RDF.type, gl(':alternative')) in g:
        branch_count = len([*g.objects(st, gl(':branches_item'))])
        tactics = [(i, 1) for i in range(branch_count + 1)]

    # if (st, RDF.type, gl(':sequence')) in g:
    else:
        tactics = [(0,)]  # just ensure one iteration; value_gen won't be used

    for gen_params in tactics:
        value_gen = expr_bool_values(*gen_params)
        way_parts = [[Way()]]
        bnd_begin = g.value(None, gl(':begin_of'), st)
        bnd_end   = g.value(None, gl(':end_of'), st)
        bound = bnd_begin
        while bound != bnd_end:
            way_step, bound = way_from_transition(bound, value_gen, g, gl)
            way_parts[-1][0] += way_step
            if bound == bnd_end:
                break

            deeper_st = g.value(bound, gl(':begin_of'), None)
            if deeper_st:
                deeper_ways = ways_through(deeper_st, g, gl)
                for way in deeper_ways:
                    way.depth += 1  # bring to current level
                way_parts += [deeper_ways, [Way()]]
                # get end of deeper_st to continue from
                bound  = g.value(None, gl(':end_of'), deeper_st)

        curr_ways_through = combine_ways_parts(way_parts)

        # collapse excessive ways
        ways += nontrivial_ways(curr_ways_through)

    return ways


def makeQuestionGraph(way: Way, g, gl):

    # make a resulting question graph
    qg = Graph()
    # seq of values (to make name suffix later)
    cond_values = []

    # iterators for convenience
    cond_vals = {name:iter(bools) for name, bools in way.vals.items()}

    act_index = 0
    prev_act = None
    prev_phase = None

    for bound in way.acts:
        ## print("> node:", node)
        # boundary & act info
        # is_begin = ( bound, gl(':begin_of'), None ) in g
        is_end   = ( bound, gl(':end_of'  ), None ) in g
        phase_mark = 'e' if is_end else 'b'  # begin is default - for first 'algorithm' node

        if phase_mark == 'e' and prev_phase == 'b':
            pass  # treat expr or stmt as `single act`
        else:
            act_index += 1

        act_class = ':act_end' if is_end else ':act_begin'
        # make act
        act_iri = phase_mark + '_%02d' % act_index
        act = gl(':' + act_iri)
        qg.add((act, RDF.type, gl(act_class)))
        qg.add((act, gl(':executes'), bound))
        # next_act
        if prev_act:
            qg.add((prev_act, gl(':next_act'), act))
        # index
        qg.add((act, gl(':index'), rdflib.term.Literal(act_index)))

        st = g.value( bound, gl(':end_of'), None )
        if st and ( st, RDF.type, gl(':expr') ) in g:
            cond_name = g.value( st, gl(':stmt_name'), None )
            assert cond_name
            cond_name = str(cond_name)  # Literal to str
            cond_value = next(cond_vals[cond_name])
            cond_values.append(cond_value)
            assert cond_value is not None, cond_name

            # expr_value
            qg.add((act, gl(':expr_value'), rdflib.term.Literal(cond_value)))

        prev_act = act
        prev_phase = phase_mark

    return qg, cond_values, act_index


def generate_questions_for_algorithm(g, gl):
    algorithm = g.value(None, RDF.type, gl(':algorithm'))
    assert algorithm

    ways = ways_through(algorithm, g, gl)

    questions = []

    for way in ways:
        graph, cond_values, act_count = makeQuestionGraph(way, g, gl)
        value_seq = ''.join(str(int(v)) for v in cond_values)
        ### print("value_seq:", value_seq)

        questions.append(dict(
            name_suffix=value_seq,
            length=act_count,
            depth=way.depth,
            laws=way.reasons,
            possible_violations=way.possible_violations,
            rdf=graph,
        ))

    return questions

