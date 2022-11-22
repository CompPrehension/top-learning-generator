# fix_alg_names.py

'''
Update rdflib.Graph containing algorithm: replace names with shorter / more readable names (update triples in-place)
'''

#  Исправление странных и неудобочитаемых имён действий и условий.


from itertools import repeat, chain
from random import choice, randint
import re

from rdflib.term import Literal
from rdflib import RDF
import rdflib

from rdflib_utils import graph_lookup, pretty_rdf



def fix_names_in_graph(g:rdflib.Graph, gl:graph_lookup, quiet=True, fix_leaf_names=True, fix_complex_names=True):
    'try fix names in rdflib.Graph g in-place'
    if fix_leaf_names:
        fix_names_for_leaf_types(g, gl, quiet=quiet)
    if fix_complex_names:
        fix_names_for_complex_types(g, gl, quiet=quiet)



# look for names in triples with these properties
NAME_PROPERTIES = (':stmt_name', ':name', )

UPDATE_TYPE_4_STMTS = (
        'return',
        # 'break',
        # 'continue',
    )


#  1. "Смысловые" имена условий и простых действий


MAX_LENGTH_LIMIT = 35

STMT_SEP = ';'
# noop_replacements = {
#     'stmt': ('log.debug(OK)', 'log.info(IN_PROGRESS)', 'log.warn(UNEXPECTED)', 'unlock()', 'lock()', 'wait()',),
#     'expr': ('free()', 'busy()', 'ENABLED', ),
# }

VAR_REPLACEMENTS = ("count", "len", "tmp", "stmp", "vdr", "conf", "ptr", "freq", "loc", "per", "bind", "dur", "service", "num", "apid", "copy")
OPERATION_CHARS = set("=+-<>()*/&|")

NO_REPEAT_GUARD_COUNT = 4
_NO_REPEAT_GUARD = []

def randName(*_):
    while True:
        val = choice(VAR_REPLACEMENTS)
        if val not in _NO_REPEAT_GUARD:
            _NO_REPEAT_GUARD.insert(0, val)
            _NO_REPEAT_GUARD[:] = _NO_REPEAT_GUARD[:NO_REPEAT_GUARD_COUNT]
            return val
            # break


def balance_brackets(s, char_open='(', char_close=')'):
    begFind = s.count(char_open)
    endFind = s.count(char_close)
    if begFind > endFind:
        s += char_close * (begFind - endFind)
    elif begFind < endFind:
        s = s.replace(char_close, '', (endFind - begFind))
    return s


def shorten_identifier(s):
    if not isinstance(s, str): s = s[0]  # unpack match_object
    if len(s) <= 12:
        return s
    if '_' in s:
        return "_" + randName()
    else:
        return randName()


def shortenNames(s):
    if len(s) > MAX_LENGTH_LIMIT:
        s = re.sub(r'\b[a-zA-Z_]\w+', shorten_identifier, s)
    return s


def make_call_if_plain_name(s):
    if not (set(s) & OPERATION_CHARS):
        s += "("+ randName() +")"
    return s


def fix_name_v3(s, refine_statements=()):
    '-> (new_str, refined_statement_type or None)'
    refined_statement_type = None

    if "#" in s:
        s = s.partition("#")[0].strip()
        s = make_call_if_plain_name(s)  # ??
    if " //" in s:
        s = s.partition(" //")[0].strip()
    if "// " in s:
        s = s.partition("// ")[0].strip()
    if "/*" in s:
        s = s.partition("/*")[0].strip()
    s = s.strip(STMT_SEP)

    # handle RETURN
    if s.lower() == 'return':
        if 'return' in refine_statements:
            # s = ''
            refined_statement_type = 'return'
            return s, refined_statement_type  # finish now
        else:
            s = 'result = 1'
    elif re.match(r'return\b', s, flags=re.I):
        if 'return' in refine_statements:
            # s = s[len('return'):].strip()  # ! cut 'return' and continue processing
            refined_statement_type = 'return'
        else:
            s = s.replace('return', '', 1)
            if 'result' in s.lower():
                s = 'accept(%s)' % s.strip()
            else:
                s = 'result = ' + s.strip()

    # сокращение строковых литералов
    if len(s) > MAX_LENGTH_LIMIT:
        def handle_literal(m):
            s = m[0]
            if len(s) > 8:
                s = (s[:2].strip() +'…'+ s[-3:].strip())
            return (s.replace("{", '')
                     .replace("}", '')
                     .replace(";", '')
                     .replace(",", '')
                    )
        s = re.sub(r'\".*?(?<!\\)\"|\'.*?(?<!\\)\'', handle_literal, s)
    else:
        # exit early (type refinement should be done before this point)
        return s, refined_statement_type

    s = re.sub(r'\\ *&|\\ *\|', lambda m: m[0].replace("\\", ""), s)
    s = re.sub(r'&?0x\w+', lambda m: "_" + randName(), s)
    s = re.sub(r'\[.+?\]', lambda m: "[" + randName() + "]", s)
    s = re.sub(r'{.+?}', randName, s)

    if "(" in s and len(s) > MAX_LENGTH_LIMIT:
        paren_pos = s.find("(")
        left_part = s[:paren_pos]
        right_part = s[paren_pos + 1 :]
        if "(" in right_part:
            right_part = re.sub(r'\w+?\(.+?\)', randName, right_part)
            right_part = shortenNames(right_part)
        while len(left_part) + 1 + len(right_part) > MAX_LENGTH_LIMIT and "," in right_part:
            right_part = right_part.rpartition(",")[0] + ")"

        s = left_part + "(" + right_part.strip()

    s = shortenNames(s)

    while len(s) > MAX_LENGTH_LIMIT:
        pos = max(s.rfind(" &"),
                  s.rfind(" |"))
        if pos == -1:
            break
        s = s[:pos]

    while len(s) > MAX_LENGTH_LIMIT:
        pos = max(s.rfind("+"),
                  s.rfind("/"),
                  s.rfind("+"),
                  s.rfind("-"),
                  s.rfind(":"),
                  s.rfind("%"))
        if pos == -1:
            break
        s = s[:pos]

    if "(" not in s and ")" not in s and "," in s:
        s = s.partition(",")[0].strip()
        s = s.strip(STMT_SEP)

    curly_open = s.find("{")
    if curly_open != -1:
        s = s[:curly_open] + randName()
    curly_close = s.find("}")
    if curly_close != -1:
        s = s[:curly_close] # + randName()

    if ";" in s:
        s = s.partition(";")[0].strip()
        s = s.strip(STMT_SEP)

    s = balance_brackets(s)

    s = s.replace("static", "")
    s = s.replace("const", "")
    s = s.replace("struct", "")
    s = s.replace("void", "")
    while " )" in s:
        s = s.replace(" )", ")")
    while "( " in s:
        s = s.replace("( ", "(")

    # ((...)) -> (...)
    for _ in range(2):
        s = re.sub(r"\((\(.+?\))\)", lambda m: m[1], s)

    # ()
    s = re.sub(r"^\s*\(\)\s*", '', s)
    # []
    s = re.sub(r"\[\]", lambda m: '[%d]' % randint(1,10), s)

    # remove "type" words
    s = re.sub(r'\b[a-zA-Z_]\w+(?:\s*\*+\s*|\s+)(?=\w)', '', s)

    # remove successive string literals
    s = re.sub(r'("[^"]*")(?:\s*L?"[^"]*")+', lambda m: m[1], s)

    while "  " in s:
        s = s.replace("  ", " ")

    # удалить внешние символы операций, ";" и пробелы
    s = s.strip(STMT_SEP + ' \t' + ''.join(OPERATION_CHARS - set("()")))

    # удалить парные круглые скобки вокруг
    while s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()

    if len(s) < 2 or (-1 < s.find("(") <= 2):
        s = randName() + "(" + randName() + ")"
        return s, refined_statement_type

    s = make_call_if_plain_name(s)
    return s, refined_statement_type



# RE_IDENTIFIER = re.compile(r'\b[a-z_]\w+', flags=re.I)
# def fix_name(s, node_type=None):
    # if "#define" in s:
    #     s = s.partition("#define")[0].strip()

    # s = s.strip(STMT_SEP)

    # # replace RETURN
    # if s.lower() == 'return':
    #     s = 'result = 1'
    # elif re.match(r'return\b', s, flags=re.I):
    #     s = s.replace('return', '', 1)
    #     if 'result' in s.lower():
    #         s = 'accept(%s)' % s.strip()
    #     else:
    #         s = 'result = ' + s.strip()

    # if not s:
    #     return choice(noop_replacements.get(node_type) or [n for L in noop_replacements for n in L])

    # if len(s) > MAX_LENGTH_LIMIT:
    #     m = re.search(r'[\w\d]+\([^)]{,%d}\)' % (MAX_LENGTH_LIMIT - 10), s)
    #     if m:
    #         s = m[0] # replace all command with a smaller inner call
    #     else:
    #         # shrink words to first & last letters, except of first word
    #         flag_it = chain([0], repeat([1]))
    #         s = RE_IDENTIFIER.sub(lambda m: m[0][0]+'…'+m[0][-1] if next(flag_it) and len(m[0]) > 4 else m[0], s)
    # return s


# store fixed strings to be reused
_FIXED_NAMES = {}  # hash_of_original_string -> (new_name, type)
def fix_name_cached(old_name, *args):
    hs = hash(old_name)
    if hs in _FIXED_NAMES:
        return _FIXED_NAMES[hs]
    else:
        result = fix_name_v3(old_name, *args)
        _FIXED_NAMES[hs] = result
        return result


# fix names of leaf_types

def fix_names_for_leaf_types(g, gl, quiet=False):
    changed = False
    new_types_assigned = set()
    leaf_types = set(map(gl, (':expr', ':stmt', ':return', ':break', ':continue')))

    for prop in NAME_PROPERTIES:
        for s,p,o in g.triples((None, gl(prop), None)):
            node_types = set(g.objects(s, RDF.type))
            if not (node_types & leaf_types):
                # print([node_type.toPython() for node_type in node_types], '\t', s.toPython())
                continue
            old_name = o.toPython()
            # node_type = next(iter(node_types & leaf_types))
            # fixed_name = fix_name(old_name, node_type.toPython()[-4:])
            fixed_name, new_type = fix_name_cached(old_name, UPDATE_TYPE_4_STMTS)
            assert len(fixed_name) > 2, (old_name, fixed_name, s)
            assert len(fixed_name) < MAX_LENGTH_LIMIT * 1.5, (old_name, fixed_name, s)
            if fixed_name != old_name:
                # set back to graph
                g.set((s, p, Literal(fixed_name)))
                changed = True
                if not quiet:
                    # print(old_name, '\t -->')
                    print('\t-->', fixed_name)
            if new_type:
                new_type_uri = gl(':' + new_type)
                if new_type_uri not in node_types:
                    new_types_assigned.add(new_type)
                    # set new type to graph
                    g.set((s, RDF.type, new_type_uri))
                    changed = True
    return changed, new_types_assigned




#  2. Имена составных действий

def shortname_for_type(type_name, **kw):
    '''Нужно для независимых действий;  подчинённые действия не нуждаются в отбражаемом имени.
    kw: `id` или g, gl, node'''
    if 'g' in kw and  'gl' in kw and 'node' in kw:
        g, gl, node = kw['g'], kw['gl'], kw['node']
    else:
        g = None
    prefix = None
    if type_name.endswith('_loop'):
        prefix = 'L'
    elif type_name == 'sequence':
        # if g:
        #     loop = g.value(None, gl(':body'), node)
        #     if loop: pass
        prefix = 'B' # "block"
    else:  # if not prefix: # default
        prefix = type_name[0].upper() # 1st letter

    suffix = None
    if 'id' in kw:
        suffix = str(kw['id'])
    elif g:
        suffix = str(g.value(node, gl(':id'), None))
    else:
        suffix = '%02d' % randint(1, 99)

    return prefix + '_' + suffix


# fix names of leaf_types

def fix_names_for_complex_types(g, gl, quiet=False):
    complex_types = {n for n in g.objects(None, RDF.type)} - set(map(gl, (':expr', ':stmt',    ':linked_list', ':algorithm', ':else', ':if', ':else-if', ':last_item', ':first_item', 'owl:NamedIndividual', ':return', ':break', ':continue')))


    for prop in NAME_PROPERTIES:
        for s,p,o in g.triples((None, gl(prop), None)):
            node_types = set(g.objects(s, RDF.type))
            if not (node_types & complex_types):
                # print([node_type.toPython() for node_type in node_types], '\t', s.toPython())
                continue
            node_type = next(iter(node_types & complex_types))
            old_name = o.toPython()
            fixed_name = shortname_for_type(pretty_rdf(node_type).strip(':'), g=g, gl=gl, node=s)
            if fixed_name != old_name:
                # set back to graph
                g.set((s, p, Literal(fixed_name)))
                if not quiet:
                    print(old_name, '\t -->')
                    print('\t', fixed_name)





if __name__ == '__main__':
    'Usage example'
    from rdflib import Graph

    qg_path = r'c:\Temp2\cntrflowoutput_v4\76__bloom_filter_intersection__1639429225.ttl'

    g = Graph().parse(location=qg_path, format='turtle')

    gl = graph_lookup(g, dict(g.namespace_manager.namespaces()))

    fix_names_in_graph(g, gl, quiet=False)
