# full_questions.py

"""
    Скачивание готовых вопросов из хранилища и отрисовка их формулировки в (json,) (html,) jpg
"""

import sys

from service import *

from rdf2alg_json import graph_2_json
from rdflib_utils import TripleOverrider


sys.path.insert(1, '../../../c_owl/code_gen')
from render_code import render_code

sys.path.insert(1, '../ctrl_flow_tools')
from html2img import html_string2jpg



RDF_DIR = 'c:/Temp2/cntrflowoutput_v7_rdf/'
JSON_DIR = 'c:/Temp2/cntrflowoutput_v7_json/'
HTML_DIR = 'c:/Temp2/cntrflowoutput_v7_html/'
FORMAT_OUT = "turtle"
EXT_OUT = ".ttl"
# FORMAT_OUT = "xml"
# EXT_OUT = ".rdf"
LOCALE = 'en'

def download_questions(offset=None, stop=None, step=None):

    print('Starting ....')

    unsolved_qs = unsolvedQuestions(GraphRole.QUESTION_SOLVED)

    print('Questions found: %d' % len(unsolved_qs))

    for qtname in unsolved_qs[offset:stop:step]:
        print()
        print("Processing question: ", qtname)
        print("========")

        g = getQuestionModel(qtname, GraphRole.QUESTION)

        # gl = graph_lookup(g, PREFIXES)

        process_question(g, qtname)

        # file_out = RDF_DIR + qtname + EXT_OUT
        # g.serialize(file_out, format=FORMAT_OUT)


def make_values_hint(values, is_loop=False, is_postcond=False):
    if not values:
        return ""
    map_bool = {True: 'истина', False: 'ложь'}.get
    prefix = ''
    if not is_loop:
        prefix = '&#8594; '
        r = (', '.join(map(map_bool, values)))
    else:
        successes = len(values) - 1  ### sum(values) <= will fail for do-until loop
        count = successes + is_postcond
        if count == 1:
            r = '1 итерация'
        elif count in (2,3,4):
            r = '%d итерации' % count
        else:
            r = '%d итераций' % count
    return prefix + ('<span class="value">%s</span>' % r)


def patch_graph(g):
    'apply changes defined by TripleOverrider instances (if any)'
    rdf_class = TripleOverrider.rdf_class_UriRef()
    for tor_node in g.subjects(RDF.type, rdf_class):
        tor = TripleOverrider.create_from_graph(tor_node, g)
        tor.apply_on_graph(g, remove_self=True)
        print('\t [INFO]  TripleOverrider changes were applied.')


def process_question(g, qtname):
    patch_graph(g)

    if 0: ###
        file_out = RDF_DIR + qtname + EXT_OUT
        g.serialize(file_out, format=FORMAT_OUT)

    gl = graph_lookup(g, PREFIXES)

    for expr in g.subjects(RDF.type, gl(':expr')):
        acts = []
        for act in g.subjects(gl(':executes') / gl(':boundary_of'), expr):
            value = g.value(act, gl(':expr_value'), None)
            if value is None:
                continue  # no value at `begin` acts
            index = g.value(act, gl(':index'), None)
            acts += [(index, value)]

        acts.sort()
        # print('\nacts:', *acts, sep='\n\t')
        values = [v if v is None else v.toPython()
                  for i,v in acts]

        parent = g.value(None, gl(':cond'), expr)

        is_loop = (parent, RDF.type, gl(':loop')) in g
        is_postcond = is_loop and (parent, RDF.type, gl(':do_while_loop')) in g

        # print(expr.n3(), values, ' is in loop: ', is_loop)


        # write back to graph (for rendering code later)
        g.set((parent,
               gl(':cond_values_hint'),
               rdflib.term.Literal(make_values_hint(values, is_loop, is_postcond))))

    # remove all act & boundary
    for s in [
            *g.subjects(gl(':executes'), None),
            *g.subjects(gl(':boundary_of'), None),
            # *g.subjects(RDF.type, gl(':act_begin')),
            # *g.subjects(RDF.type, gl(':act_end')),
            # *g.subjects(RDF.type, gl(':boundary')),
    ]:
        if (s, RDF.type, gl(':algorithm')) in g:
            continue
        g.remove((s, None, None))
        # g.remove((None, None, s))

    g.bind('', NS_code.get()) # set namespace for gl

    a_json = graph_2_json(g)

    # print()
    # print()
    # print(*a_json.keys())
    # print()
    # print()
    import json
    out = JSON_DIR + qtname + '.json'
    with open(out, mode='w') as f:
        data = json.dump(a_json, f, indent=1)


    rendered_html = render_code(a_json, text_mode='html', locale=LOCALE, show_buttons=True, raise_on_error=True)

    file_out = HTML_DIR + qtname + '.html'
    with open(file_out, 'w') as f:
        f.write(rendered_html)

    file_out = HTML_DIR + qtname + '.jpg'
    html_string2jpg(rendered_html, file_out)





if __name__ == '__main__':
    if 1:
        # qtname = 'cJSON_ParseWithOpts_v1111111011'
        # qtname = 'cJSON_CreateNumber_v0'
        # qtname = 'android_render_rgb_on_rgb_v0'
        # qtname = 'android_render_yv12_on_yv12_v10110'
        # qtname = 'android_render_yv12_on_yv12_v1111110'
        # for qtname in ['cookie_list_v010100', 'cookie_list_v0100', 'cookie_list_v00', 'cookie_list_v01110000', 'cookie_list_v11110000', 'cookie_list_v110100', 'cookie_list_v1100', 'cookie_list_v10',]:
        # qtname = 'dup_cookie'
        # qtname = 'SDL_CondWaitTimeout'
        qtname = 'cJSON_GetArraySize'
        g = getQuestionModel(qtname, GraphRole.QUESTION)
        process_question(g, qtname)

        exit(0)


    download_questions(0, None, 1)


