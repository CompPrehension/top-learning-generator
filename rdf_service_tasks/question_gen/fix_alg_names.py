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

from rdflib_utils import graph_lookup, pretty_rdf



def fix_names_for_graph(g:rdflib.Graph, gl:graph_lookup, quiet=True):
    'try fix names in rdflib.Graph g in-place'
    fix_names_for_leaf_types(g, gl, quiet=quiet)
    fix_names_for_complex_types(g, gl, quiet=quiet)



# look for names in triples with these properties
name_properties = (':stmt_name', ':name', )



#  1. "Смысловые" имена условий и простых действий


max_length_limit = 35

stmt_sep = ';'
noop_replacements = {
    'stmt': ('log.debug(OK)', 'log.info(IN_PROGRESS)', 'log.warn(UNEXPECTED)', 'unlock()', 'lock()', 'wait()',),
    'expr': ('free()', 'busy()', 'ENABLED', ),
}


def fix_name(s, node_type=None):
    if "#define" in s:
        s = s.partition("#define")[0].strip()

    s = s.strip(stmt_sep)

    if not s:
        return choice(noop_replacements.get(node_type) or [n for L in noop_replacements for n in L])

    if len(s) > max_length_limit:
        m = re.search(r'[\w\d]+\([^)]{,25}\)', s)
        if m:
            s = m[0] # replace all command with a smaller inner call
        else:
            # shrink words to first & last letters, except of first word
            flag_it = chain([0], repeat([1]))
            s = re.sub(r'\w[\w\d]+', lambda m: m[0][0] + m[0][-1] if next(flag_it) else m[0], s)


    return s


# fix names of leaf_types

def fix_names_for_leaf_types(g, gl, quiet=False):
    leaf_types = set(map(gl, (':expr', ':stmt')))
    for prop in name_properties:
        for s,p,o in g.triples((None, gl(prop), None)):
            node_types = set(g.objects(s, RDF.type))
            if not (node_types & leaf_types):
                # print([node_type.toPython() for node_type in node_types], '\t', s.toPython())
                continue
            node_type = next(iter(node_types & leaf_types))
            old_name = o.toPython()
            fixed_name = fix_name(old_name, node_type.toPython()[-4:])
            if fixed_name != old_name:
                # set back to graph
                g.set((s, p, Literal(fixed_name)))
                if not quiet:
                    print(old_name, '\t -->')
                    print('\t', fixed_name)




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

    return prefix + suffix


# fix names of leaf_types

def fix_names_for_complex_types(g, gl, quiet=False):
    complex_types = {n for n in g.objects(None, RDF.type)} - set(map(gl, (':expr', ':stmt',    ':linked_list', ':algorithm', ':else', ':if', ':else-if', ':last_item', ':first_item', 'owl:NamedIndividual')))


    for prop in name_properties:
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

    fix_names_for_graph(g, gl, quiet=False)
