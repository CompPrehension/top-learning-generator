# analyze_alg.py

from collections import defaultdict
from functools import reduce, lru_cache
from itertools import repeat, product, starmap
from operator import add, eq, or_
from random import shuffle, random

import rdflib
from rdflib import Graph, RDF

from ns4guestions import *
from rdflib_utils import graph_lookup, pretty_rdf, TripleOverrider

LOOP_MAX_ITERATIONS = 3

# global var can be set from outside the thread to interrupt it
_INTERRUPT_BY_TIMEOUT = False


def set_interrupt_flag(value: bool = False):
    global _INTERRUPT_BY_TIMEOUT
    if _INTERRUPT_BY_TIMEOUT != value:
        print('setting INTERRUPT_BY_TIMEOUT to', value)
    _INTERRUPT_BY_TIMEOUT = value


def check_interrupt():
    if _INTERRUPT_BY_TIMEOUT:
        print('Stopping by timeout ...')
        raise StopIteration("Interrupted by timeout")


class jsObj(dict):
    'JS-object-like dict (access to "foo": obj.foo as well as obj["foo"])'
    # def __init__(self, *args, **kw):
    #     super().__init__(*args, **kw)
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
        self.i = 0  # state for next()

    def get(self, index):
        if index < self.delay or index >= (self.delay + self.active):
            return self.safe_value
        else:
            return not self.safe_value

    def copy(self, copy_index=True):
        copy = type(self)(delay=self.delay, active=self.active, safe_value=self.safe_value)
        if copy_index:
            copy.i = self.i
        return copy

    def __len__(self):
        return (self.delay + self.active) + 1

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        self.i += 1
        return self.get(self.i - 1)

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.start, index.stop, index.step
            if start is None: start = 0
            if stop is None:
                stop = (self.delay + self.active)  # + 1
            elif stop < 0:
                stop = (self.delay + self.active) + stop  # + 1
            if step is None: step = 1
            return [self.get(i) for i in range(start, stop, step)]
        return self.get(index)

    ## def __list__(self): return self[:len(self)]
    def __contains__(self, other):
        return all(starmap(eq, zip(self, other[:])))

    def __str__(self):
        return str(self[:])

    def __repr__(self):
        return f"expr_bool_values(delay={self.delay}, active={self.active}, safe_value={self.safe_value})"


# itvs = expr_bool_values(1, 2)
# [itvs[i] for i in range(10)]
# >>> [False, True, True, False, False, False, False, False, False, False]

def logical_or(a, b):
    return a or b


# def bitwise_or(a, b):
# # return a | b
# ###
# print('About to OR:', a, "|", b)
# r = a | b
# print('Result of OR:', r)
# return r


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
        check_interrupt()
        super().__init__(*args, **kw)
        self.len = self.get('len', 0)
        self.depth = self.get('depth', 0)
        self.vals = self.get('vals', None) or jsObj()
        self.acts = self.get('acts', None) or ()
        self.reasons = self.get('reasons', None)  # frozenset()
        self.possible_violations = self.get('possible_violations', None)  # frozenset()
        self.invalid = self.get('invalid', False)
        self.updates = self.get('updates', None)  # : dict(action_id -> update_dict)
        self.key2join = dict(self._key2join)  # copy from static declaration
        self.key2join['updates'].func = self.join_updates

    # not a @staticmethod - just a function declared here :)
    def join_acts(a1, a2):
        if a1 and a2 and a1[-1] == a2[0]:
            a2 = a2[1:]
        return a1 + a2

    # not a @staticmethod - just a function declared here :)
    def join_vals(v1, v2):
        return {cnd: v1.get(cnd, ()) + v2.get(cnd, ())
                for cnd in {*v1.keys(), *v2.keys()}}

    def join_updates(self, u1: dict, u2: dict):
        if not u1 and not u2: return None
        if not u1 and u2: return u2
        if u1 and not u2: return u1
        k1 = set(u1.keys())
        k2 = set(u2.keys())
        common_k = k1 & k2
        for ck in common_k:
            if u1[ck].incompatible_with(u2[ck]):
                print('\tincompatible ways found.')
                # print('incompatible_with way:')
                # print('\t1.:', u1)
                # print('\t2.:', u2)
                self.invalid = True
                return None

        return {**u1, **u2}

    # static var
    _key2join = {
        'len': jsObj(func=add, new=int),
        'depth': jsObj(func=max, new=int),
        'vals': jsObj(func=join_vals, new=jsObj),
        'acts': jsObj(func=join_acts, new=tuple),
        'reasons': jsObj(func=or_, new=frozenset),
        'possible_violations': jsObj(func=or_, new=frozenset),
        'updates': jsObj(func=None or join_updates, new=dict),
        # 'invalid' should be after 'updates'
        'invalid': jsObj(func=logical_or, new=bool),  # or_ is "|" and can be used instead of "_ or _" for bools
    }

    def __add__(self, other):
        if random() < 0.05:  # try to fix infinite looping
            check_interrupt()
        r = Way()  # {}
        for key, join in self.key2join.items():
            r[key] = join.func(
                # self .get(key, join.new()),
                # other.get(key, join.new())
                self.get(key) or join.new(),
                other.get(key) or join.new()
            )
        ### print('joined ways data:'); print(r)
        return r  # Way(r)

    # def old__add__(self, other):
    #     return Way({'len': self.len + other.len,
    #      'depth': max(self.depth, other.depth),  # depth does not sum
    #      'vals': {cnd: self.vals.get(cnd, ()) + other.vals.get(cnd, ())
    #               for cnd in set([*self.vals.keys(), *other.vals.keys()])},
    #      'acts': self.join_acts(self.acts, other.acts),
    #      'reasons': self.get('reasons', frozenset()) | other.get('reasons', frozenset()),
    #      'possible_violations': self.get('possible_violations', frozenset()) | other.get('possible_violations', frozenset()),
    #     })


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
    check_interrupt()
    way = Way()
    prop_name = ':always_consequent'
    bnd2 = g.value(bound1, gl(prop_name), None)
    if not bnd2:
        # handle
        assert value_gen
        value = next(value_gen)
        prop_name = {
            True: ':on_true_consequent',
            False: ':on_false_consequent',
        }.get(value)
        assert prop_name, 'generated value (bool expected): "%s"' % repr(value)
        bnd2 = g.value(bound1, gl(prop_name), None)
        if not bnd2:
            print('No outgoing ', prop_name, ' found from node:', bound1)
            raise NotImplementedError(
                "No known outgoing '*consequent' transitions found."
                "\n\t\t 3 types of '*consequent' transitions supported so far.")

        cond_node = g.value(bound1, gl(':boundary_of'), None)
        assert cond_node, bound1
        cond_name = g.value(cond_node, gl(':stmt_name'), None)
        assert cond_name
        cond_name = str(cond_name)
        way.vals[cond_name] = (value,)

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
    # else:
    #     print('No reason node for boundaries: %s, %s' % (bound1, bnd2))
    way.len = 1 if R else 0  # do not count hidden transitions
    way.depth = 1
    way.acts = (bound1, bnd2)
    return (way, bnd2)


def combine_ways_parts(way_parts: list):
    return [reduce(add, comb) for comb in product(*way_parts)]


def nontrivial_ways(ways: list, max_similar=2, length_ratio=0.34, print_report=True):
    check_interrupt()
    # traces with same violations
    groups = defaultdict(list)

    for way in ways:
        if way.invalid:
            continue
        viols = way.possible_violations
        ## print(viols)
        groups[viols].append(way)

    # filter out excessive traces
    selected_trace_configs = []

    for ways in groups.values():
        if len(ways) <= max_similar:
            selected_trace_configs.extend(ways)
            continue
        lengths = [tc.len for tc in ways]
        Lmin = min(lengths)
        Lmax = max(lengths)
        threshold = Lmin + length_ratio * (Lmax - Lmin)  ## wouldn't `Lmin * 1.34` be better ???
        shortest = [tc for tc in ways if tc.len <= threshold]
        if len(shortest) > max_similar:
            shuffle(shortest)
            if print_report: print(f'    ... truncating a group of {len(shortest)} to {max_similar} traces')
            shortest = shortest[:max_similar]
        else:
            if print_report: print(f'    ... selected {len(shortest)} of {len(ways)} traces')
        selected_trace_configs.extend(shortest)

    if print_report and len(selected_trace_configs) > max_similar: print(
        '    ... %d total traces selected' % len(selected_trace_configs))
    return selected_trace_configs


def _make_updates_for_FOR_loop(st: rdflib.URIRef, lower_bound: int, upper_bound: int, g, gl) -> dict:
    # describe what to replace in Graph's triples to obtain specified bounds:
    # update loop header by inserting appropriate values into init and cond clauses
    # updates to Way properties
    updates = {}

    # deal with `init`
    init_node = g.value(st, gl(':init'), None)
    if not init_node:
        print('[WARN] Cannon change `init` clause as it doesn`t exist in FOR loop (%s)' % pretty_rdf(
            st))  # raise ValueError
        return updates
    init = g.value(init_node, gl(':stmt_name'), None).toPython()
    assert init
    lvalue = init.partition('=')[0]
    new_init = '%s = %d' % (lvalue.strip(), lower_bound)
    tor = TripleOverrider((init_node, gl(':stmt_name'), rdflib.Literal(init)),
                          o=rdflib.Literal(new_init))
    node_id = g.value(init_node, gl(':id'), None).toPython()
    updates[node_id] = tor

    # deal with `cond`
    cond_node = g.value(st, gl(':cond'), None)
    if not cond_node:
        print('[WARN] Cannon change `cond` clause as it doesn`t exist in FOR loop (%s)' % pretty_rdf(
            st))  # raise ValueError
        return updates
    cond = g.value(cond_node, gl(':stmt_name'), None).toPython()
    assert cond
    op = '<=' if '<=' in cond else '<'  # !!! only two cmp operations supported so far!
    lvalue = cond.partition(op)[0]
    new_cond = '%s %s %d' % (lvalue.strip(), op, upper_bound)
    tor = TripleOverrider((cond_node, gl(':stmt_name'), rdflib.Literal(cond)),
                          o=rdflib.Literal(new_cond))
    node_id = g.value(cond_node, gl(':id'), None).toPython()
    updates[node_id] = tor

    return updates


@lru_cache()
def ways_through(st: rdflib.URIRef, g: Graph, gl=None):
    """ -> [way1, way2, ...]
    """
    check_interrupt()
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
        else:
            print('Cannot begin algorithm properly: ', st, ' having entry bound:', bound)
            raise ValueError("Invalid entry point of algorithm.")

    if (st, RDF.type, gl(':loop')) in g:
        additional_way_params = repeat(None)  # nothing by default (can be something with FOR loops)
        safe_value = False  # what to use in condition to avoid an infinite loop
        if (st, RDF.type, gl(':inverse_conditional_loop')) in g:  ### TODO: make sure of loop type
            safe_value = True
        is_post_conditional = (st, RDF.type, gl(':start_with_body')) in g  # -> bool
        is_post_conditional = int(is_post_conditional)
        loop_complexity = g.value(st, gl(':loop_complexity'), None)
        # default unlimited count of iterations:
        min_iterations = 0
        max_iterations = LOOP_MAX_ITERATIONS - is_post_conditional
        if loop_complexity:
            loop_complexity = loop_complexity.toPython()
            assert type(loop_complexity) is str, '`loop_complexity`: `str` type expected'
            if loop_complexity == "InfiniteTimes":
                # we cannot control number of iterations
                print(
                    '[WARN] Cannot trace loop with loop_complexity: "%s": we cannot control number of iterations' % loop_complexity)
                return ways  # empty fo far
            elif loop_complexity == "ZeroTimes":
                max_iterations = 0
            elif loop_complexity == "NonZeroTimes":
                min_iterations = 1
            elif loop_complexity.startswith("NTimes"):
                s = loop_complexity[len("NTimes"):].strip().lstrip('[')
                not_inclusive = s.endswith(')')  # otherwise ']'
                s = s.rstrip(']').rstrip(')')
                numbers = [int(n.strip()) for n in s.split(',')]
                assert len(numbers) == 2, '"%s" -> %s' % (s, numbers)
                a, b = numbers
                print('NTimes: ', a, b, ' not_inclusive:', not_inclusive)
                number_of_iterations = b - a + 1 - not_inclusive  # defined by Ntimes loop setting
                if number_of_iterations <= max_iterations:
                    # fixed variant according to code given
                    min_iterations = number_of_iterations
                    max_iterations = number_of_iterations
                    print('NTimes: use count as provided: ', number_of_iterations)
                else:
                    # update loop header by inserting appropriate values:
                    additional_way_params = [
                        _make_updates_for_FOR_loop(st, a, a + i - 1 + not_inclusive, g, gl)
                        for i in range(min_iterations, max_iterations + 1)
                    ]
                    print('NTimes: change count as we need: ', additional_way_params)
                    pass

            elif loop_complexity == "OneTime":
                # condition of 'do-while' loop should always evaluate to False
                min_iterations = 1 - is_post_conditional
                max_iterations = 1 - is_post_conditional

            elif loop_complexity == "Undefined":
                pass  # anything possible
            else:
                raise ValueError('Unknown value of `loop_complexity`: "%s"' % loop_complexity)

        # (delay=0, active=i, )
        tactics = [(0, i, safe_value, a_w_par)
                   for i, a_w_par in zip(
                range(min_iterations, max_iterations + 1),
                additional_way_params)]

    elif (st, RDF.type, gl(':alternative')) in g:
        branch_count = len([*g.objects(st, gl(':branches_item'))])
        tactics = [(i, 1, False, None) for i in
                   range(branch_count + 1)]  # possible overhead for `else` will be optimized by nontrivial_ways()

    # if (st, RDF.type, gl(':sequence')) in g:
    else:
        tactics = [(0, 0, False, None)]  # just ensure one iteration; value_generator won't be used

    for gen_params in tactics:
        value_gen = expr_bool_values(*gen_params[:3])
        additional_way_updates = gen_params[3]
        if additional_way_updates: print('````` additional_way_updates =`', additional_way_updates)
        r"""      w       w           w
                /   \   /   \       /   \
         [ [w] [--w--] [--w--] ... [--w--] [w] ]  # way_parts: schematic structure
                \   /   \   /       \   /
                  w       w           w
        """
        way_parts = [[Way(
            updates=additional_way_updates
        )]]
        inner_parts = ways_through_inner(st, value_gen.copy(), g, gl)
        way_parts += [inner_parts]
        curr_ways_through = combine_ways_parts(way_parts)  # -> plain list of full-length ways
        # collapse excessive ways ...
        ways += nontrivial_ways(curr_ways_through, length_ratio=0.9)
        # ways += curr_ways_through

    ### if not ways: print('\t!! No ways through ', st)
    return ways


def ways_through_inner(st, value_gen, g, gl, bound_from=None, finish_bounds=()):
    ways = []
    way_parts = [[Way()]]
    if st:
        bnd_begin = g.value(None, gl(':begin_of'), st)
        # possible ending bounds
        bnd_end = g.value(None, gl(':end_of'), st)
        bnd_halts = set(g.subjects(gl(':halt_of'), st))
        finish_bounds = {bnd_end, *bnd_halts}
        bound = bnd_begin
    else:
        assert bound_from
        assert finish_bounds
        bound = bound_from

    while bound not in finish_bounds:
        # one step
        way_step, bound = way_from_transition(bound, value_gen, g, gl)
        way_parts[-1][0] += way_step
        if  not bound or  bound in finish_bounds:
            break

        deeper_st = g.value(bound, gl(':begin_of'), None)
        if deeper_st:
            deeper_ways = ways_through(deeper_st, g, gl)
            deeper_finish_bounds = set()  # bounds inner ways finished with
            for way in deeper_ways:
                way.depth += 1  # bring to current level
                deeper_finish_bounds.add(way.acts[-1])
            way_parts += [deeper_ways, [Way()]]
            if len(deeper_finish_bounds) > 1:
                # several alternative outgoing directions
                bound, *more_bounds = deeper_finish_bounds  # take one to continue with
                for alt_bound in more_bounds:
                    # recurse in controlled fashion
                    trailing_ways = ways_through_inner(None, value_gen, g, gl, alt_bound, finish_bounds)
                    # use current parts plus alternative trailing parts
                    curr_ways_through = combine_ways_parts(way_parts + [trailing_ways])
                    ways += nontrivial_ways(curr_ways_through)  # collapse excessive ways
            else:
                # get end of deeper_st to continue from
                bound = next(iter(deeper_finish_bounds))
                # ### bound = g.value(None, gl(':end_of'), deeper_st)

    curr_ways_through = combine_ways_parts(way_parts)  # -> plain list of full-length ways
    # collapse excessive ways
    ways += nontrivial_ways(curr_ways_through)
    return ways


def makeQuestionGraph(way: Way, g, gl):
    assert not way.invalid, way.invalid

    # make a resulting question graph
    qg = Graph()
    # seq of values (to make name suffix later)
    cond_values = []

    # iterators for convenience
    cond_vals = {name: iter(bools) for name, bools in way.vals.items()}

    act_index = 0
    prev_act = None
    prev_phase = None

    for bound in way.acts:
        # check_interrupt()
        ## print("> node:", node)
        # boundary & act info
        # is_begin = ( bound, gl(':begin_of'), None ) in g
        is_end = (bound, gl(':end_of'), None) in g
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
        qg.add((act, gl(':index'), rdflib.Literal(act_index)))

        st = g.value(bound, gl(':end_of'), None)
        if st and (st, RDF.type, gl(':expr')) in g:
            cond_name = g.value(st, gl(':stmt_name'), None)
            assert cond_name
            cond_name = str(cond_name)  # Literal to str
            cond_value = next(cond_vals[cond_name])
            cond_values.append(cond_value)
            assert cond_value is not None, cond_name

            # expr_value
            qg.add((act, gl(':expr_value'), rdflib.Literal(cond_value)))

        prev_act = act
        prev_phase = phase_mark

    if way.updates:
        for trov in way.updates.values():
            print('\t\tWriting updates ...')
            print('\t\t', trov)
            print()
            trov.write_as_triples(qg)

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

    ### print('### generate_questions_for_algorithm() ->', len(questions), 'questions.')

    return questions
