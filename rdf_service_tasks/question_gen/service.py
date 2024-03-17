# service.py

"""
    Entry point (main module) for question-creation service, a part of CompPrehension project.
    @ 2023
"""

import json
import math
import random  # using random.seed
import re
import sys
from math import exp
from statistics import fmean as avg

import fs
import rdflib
import yaml
from rdflib import Graph, RDF

import sqlite_questions_metadata as dbmeta
from GraphRole import GraphRole
from RemoteFileService import RemoteFileService
from analyze_alg import generate_questions_for_algorithm, set_interrupt_flag
from analyze_alg import jsObj
from chain_utils import builder
# from NamespaceUtil import NamespaceUtil
from ns4guestions import *
from rdflib_utils import graph_lookup, get_class_descendants_rdf
from sparql_wrapper import Sparql

# from sqlite_questions_metadata import findQuestionOrTemplateByNameDB, findQuestionsOnStageDB, findTemplatesOnStageDB, \
#     createQuestionTemplateDB, createQuestionDB

sys.path.insert(1, '../../../c_owl/')  # dev location
sys.path.insert(2, 'c_owl/')  # desired deploy location
if 0:
    # just for debugger to see the code in different directory
    from ....c_owl.ctrlstrct_test import make_question_dict_for_alg_json
    from ....c_owl.ctrlstrct_run import run_jenaService_with_rdfxml
from ctrlstrct_test import make_question_dict_for_alg_json
from ctrlstrct_run import run_jenaService_with_rdfxml
### inspecting loading of qG
from common_helpers import Checkpointer

# using patched version of SPARQLBurger
from SPARQLBurger.SPARQLQueryBuilder import *

# print('imports completed.')

# Global variables
CONFIG = None
INIT_GLOBALS = True
# INIT_GLOBALS = False

# qG_URI = 'http://vstu.ru/poas/questions'  # required for question generation
qG_URI = 'http://vstu.ru/poas/selected_questions'

PREFETCH_QUESTIONS = False
# PREFETCH_QUESTIONS = True  # uri of graph to fetch can be changed below
DUMP_QUESTION_GRAPH_TO_FILE = False
# DUMP_QUESTION_GRAPH_TO_FILE = True  # and exit immediately!
REMOVE_TRIPLES_FOR_PRODUCTION = True  # only when saving graph to file

GATHER_DB_SIZE_INFO = False

qG = None  # questions graph (pre-fetched)
fileService = None
sparql_endpoint = None


def read_access_config(file_path='./access_urls.yml'):
    global CONFIG
    if CONFIG:
        return CONFIG

    try:
        # read config
        with open(file_path) as f:
            data = yaml.load(f, yaml.Loader)
    except OSError as e:
        print("Error: cannot read configuration from", file_path)
        print(e)
        exit(1)

    CONFIG = jsObj(data)
    global fuseki_host
    global rdf_db_name
    global FTP_BASE
    global FTP_DOWNLOAD_BASE
    fuseki_host = data["fuseki_host"]
    rdf_db_name = data["rdf_db_name"]
    FTP_BASE = data["ftp_base"]
    FTP_DOWNLOAD_BASE = data["ftp_download_base"] or FTP_BASE
    return CONFIG


def _get_rdfdb_stats_collectors():
    """init StateWatcher to watch dataset size on disk as well as number of triples in th dataset."""

    if not GATHER_DB_SIZE_INFO:
        return ()

    from misc.watch_rdf_db import StateWatcher
    from misc.dir_stat import dir_size

    target_dir = CONFIG.db_dir

    def watch_dir():
        return {'dir_size': dir_size(target_dir)}

    def watch_triples():
        if sparql_endpoint:
            # Число триплетов в датасете
            query_results = sparql_endpoint.query("select (count(*) as ?count) {graph ?g {?s ?p ?o}} ",
                                                  return_format="json")
            row = query_results['results']['bindings'][0]
            count = row['count']['value']
            # del query_results
        else:
            count = -1
        return {'triples': count}

    sw = StateWatcher(
        [watch_dir, watch_triples],
        add_params={'software': CONFIG.software, "db": rdf_db_name}
    )
    CONFIG.rdfdb_watcher = sw
    return [
        # reference to bound method `take_snapshot`:
        sw.take_snapshot
    ]


def get_file_service() -> RemoteFileService:
    global fileService
    if fileService:
        return fileService

    read_access_config()
    fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
    return fileService


def get_endpoint():
    global sparql_endpoint
    if sparql_endpoint:
        return sparql_endpoint

    read_access_config()
    sparql_endpoint = Sparql(
        fuseki_host, rdf_db_name,
        query_url=CONFIG.query_url,
        update_url=CONFIG.update_url,
        credentials=CONFIG.get('credentials'),
        post_update_hooks=_get_rdfdb_stats_collectors()
    )
    return sparql_endpoint


# if INIT_GLOBALS:
#     read_access_config()
#     get_file_service()
#     get_endpoint()

# See below:
# qG = fetchGraph(qG_URI)


def makeUpdateTripleQuery(ng, s, p, o, prefixes=()):
    # Create a SPARQLUpdateQuery object
    update_query = SPARQLUpdateQuery()

    for pfx, url in dict(prefixes).items():
        # Add a prefix
        update_query.add_prefix(
            prefix=Prefix(prefix=pfx, namespace=url)
        )

    # Create a graph pattern for the DELETE part and add a triple
    delete_pattern = SPARQLGraphPattern(graph_name=ng)
    delete_pattern.add_triples(
        triples=[Triple(s, p, "?obj")]
    )

    # Create a graph pattern for the INSERT part and add a triple
    update_query.set_insert_pattern(
        builder(SPARQLGraphPattern(graph_name=ng)).add_triples(
            triples=[Triple(s, p, o)]
        ).builder
    )
    update_query.set_delete_pattern(graph_pattern=delete_pattern)

    # Create a graph pattern for the WHERE part and add some triples
    update_query.set_where_pattern(
        builder(SPARQLGraphPattern(graph_name=ng)).add_nested_graph_pattern(
            builder(SPARQLGraphPattern(optional=True)).add_triples(
                triples=[Triple(s, p, "?obj")]
            ).builder
        ).builder
    )

    return update_query.get_text()


# >>>
# makeUpdateTripleQuery('<ng>', '?s', '?p', '?o')
# DELETE { GRAPH <ng> {
#    ?s ?p ?obj .
# } }
# INSERT { GRAPH <ng> {
#    ?s ?p ?o .
# } }
# WHERE { GRAPH <ng> {
#    OPTIONAL {
#       ?s ?p ?obj .
#    }
# } }


def makeInsertTriplesQuery(named_graph, triples, prefixes=()):
    update_query = SPARQLUpdateQuery()

    for pfx, url in dict(prefixes).items():
        # Add a prefix
        update_query.add_prefix(
            prefix=Prefix(prefix=pfx, namespace=str(url))
        )

    # Create a graph pattern for the INSERT part and add a triple
    update_query.set_insert_pattern(
        builder(SPARQLGraphPattern(graph_name=named_graph)).add_triples(
            triples=[Triple(*t) for t in triples]
        ).builder
    )
    # patch keyword
    text = update_query.get_text()
    text = text.replace('INSERT ', 'INSERT DATA ', 1)

    return text


def URI(uri):
    return "<%s>" % uri


def questionSubgraphPropertyFor(role: GraphRole) -> str:
    return NS_questions.get("has_graph_" + role.ns().base());


def tableFieldForRoleDB(role: GraphRole) -> str:
    return NamespaceUtil.make_base(role.prefix) + "_graph";


def unsolvedQuestions(unsolvedSubgraph: GraphRole) -> list:
    """get names of questions with `rdf:nil` set for specified graph"""
    ng = URI(qG_URI);

    unsolvedTemplates = builder(SPARQLSelectQuery()
                                ).add_prefix(
        Prefix('rdf', PREFIXES['rdf'])
    ).add_variables(
        ["?name"]
    ).set_where_pattern(
        builder(SPARQLGraphPattern(graph_name=ng)
                ).add_triples([
            Triple("?node", URI(NS_questions.get("name")), "?name"),
            Triple("?node", URI(questionSubgraphPropertyFor(unsolvedSubgraph)), 'rdf:nil'),
        ]).builder
    ).get_text().result

    query_results = sparql_endpoint.query(unsolvedTemplates, return_format="json")
    names = [b['name']['value'] for b in query_results['results']['bindings']]
    # del query_results
    return names


# unsolved_qs = unsolvedQuestions(GraphRole.QUESTION_SOLVED)


def templatesWithoutQuestions(limit=None) -> list:
    """get names of question templates without questions"""
    ng = URI(qG_URI);

    lonelyTemplates = builder(SPARQLSelectQuery()
                              ).add_prefix(
        Prefix('rdf', PREFIXES['rdf'])
    ).add_variables(
        ["?name"]
    ).set_where_pattern(
        builder(SPARQLGraphPattern(graph_name=ng)
                ).add_triples([
            Triple("?node", 'rdf:type', URI(NS_questions.get("QuestionTemplate"))),
            Triple("?node", URI(NS_questions.get("name")), "?name"),
        ]).add_nested_graph_pattern(
            builder(SPARQLGraphPattern(keyword="FILTER NOT EXISTS")
                    ).add_triples([
                Triple("?absent_q", URI(NS_questions.get("has_template")), '?node'),
            ]).builder
        ).add_nested_graph_pattern(
            builder(SPARQLGraphPattern(keyword="FILTER NOT EXISTS")
                    ).add_triples([
                Triple("?node",
                       URI(questionSubgraphPropertyFor(GraphRole.QUESTION_TEMPLATE_SOLVED)),
                       "rdf:nil"),
            ]).builder
        ).builder
    ).builder.get_text()

    if limit and limit > 0:
        lonelyTemplates += '\nLIMIT %d' % limit

    query_results = sparql_endpoint.query(lonelyTemplates, return_format="json")
    names = [b['name']['value'] for b in query_results['results']['bindings']]
    # del query_results
    return names


# templates_to_create_questions = templatesWithoutQuestions()


CONSTRUCT_PATTERN = '''CONSTRUCT {
   ?s ?p ?o .
}
WHERE { GRAPH <%s> {
   ?s ?p ?o .
} }
'''


def fetchGraph(gUri: str, verbose=False):
    raise PendingDeprecationWarning('Do not use storage for RDF graphs any more !')

    format_request, format_parse = "turtle", 'n3'
    # format_request, format_parse = "rdfxml", None  # , 'application/rdf+xml'
    q = CONSTRUCT_PATTERN % gUri
    ch = Checkpointer()
    if verbose: print('   fetchGraph: requesting data ...')
    query_result = sparql_endpoint.query(q, return_format=format_request)
    if verbose: ch.hit('fetchGraph: data requested')
    if format_parse:
        query_results = b''.join(list(query_result))
        if verbose: ch.hit('fetchGraph: collected query results')
        g = Graph().parse(format=format_parse, data=query_results)
        if verbose: ch.hit('parsed n3')
        # g = Graph(store="Oxigraph").parse(format='application/rdf+xml', data=query_results)
    else:
        g = query_result
    if verbose: ch.since_start('fetchGraph: done in:')
    return g

    # # q_graph = fetchGraph(qG_URI)
    # if INIT_GLOBALS and PREFETCH_QUESTIONS and not qG:
    #     ### empty graph:
    #     # qG = Graph().parse(format='n3', data='@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n[] a rdf:Class .')
    #     # pre-download whole questions graph
    #     print('Pre-download whole questions graph ...')
    #     if False:
    #         pass;  # qUri = qG_URI
    #     else:
    #         ## qUri = 'http://vstu.ru/poas/questions_only'
    #         # qUri = 'http://vstu.ru/poas/selected_questions'
    #         # ! qG_URI !
    #         print('Fetching graph as specified:', qG_URI)
    #     qG = fetchGraph(qG_URI, verbose=True)
    #
    #     if DUMP_QUESTION_GRAPH_TO_FILE:
    #         ###
    #         # dump_qG_to = CONFIG.ftp_base + CONFIG.rdf_db_name + '.ttl'
    #         dump_qG_to = CONFIG.ftp_base + '../' + CONFIG.rdf_db_name + '.ttl'
    #
    #         if REMOVE_TRIPLES_FOR_PRODUCTION:
    #             # just remove unused properties (has_graph_*) from question nodes
    #             # before exporting to production env
    #             nsQ = 'http://vstu.ru/poas/questions/'
    #             prop_names = '''
    #             has_graph_q_s
    #             has_graph_q
    #             has_graph_qt
    #             has_graph_qt_s'''.split()
    #
    #             i = 0
    #             for pn in prop_names:
    #                 p = rdflib.URIRef(pn, nsQ)
    #                 for s, o in qG.subject_objects(p):
    #                     qG.remove((s, p, o))
    #                     i += 1
    #             print("Removed %d triples from graph (for production)." % i)
    #
    #         # shorten length of serialized data
    #         qG.bind('Q', 'http://vstu.ru/poas/questions/Question#')
    #         qG.bind('QT', 'http://vstu.ru/poas/questions/QuestionTemplate#')
    #         qG.bind('qs', 'http://vstu.ru/poas/questions/')
    #         qG.serialize(dump_qG_to, format='turtle')
    #         print(len(qG), f"triples saved to file: {dump_qG_to}")
    #         print('Bye for now!')
    #         exit()


# def getFullTemplate(name):
#     g_qt   = fetchGraph(NS_namedGraph.get(GraphRole.QUESTION_TEMPLATE.ns().get(name)))
#     g_qt_s = fetchGraph(NS_namedGraph.get(GraphRole.QUESTION_TEMPLATE_SOLVED.ns().get(name)))

#     g = g_qt
#     g += g_qt_s
#     return g
# qt0 = getFullTemplate(templates_to_create_questions[5])


def questionStages():
    return [
        GraphRole.QUESTION_TEMPLATE,
        GraphRole.QUESTION_TEMPLATE_SOLVED,
        GraphRole.QUESTION,
        GraphRole.QUESTION_SOLVED
    ]


def findQuestionByName(questionName, questions_graph=qG):
    qG = questions_graph or fetchGraph(qG_URI);
    if qG:
        qNode = qG.value(None, rdflib.URIRef(NS_questions.get("name")), rdflib.Literal(questionName))
        if qNode:
            return qNode

    print("    (No question found for name: %s)" % questionName)
    return None;


def nameForQuestionGraph(questionName, role: GraphRole, questions_graph=qG, file_ext=".ttl", fileService=get_file_service()):
    # look for <Question>-<subgraph> relation in metadata first
    qG = questions_graph or fetchGraph(qG_URI);
    targetGraphUri = None

    if qG:
        qNode = findQuestionByName(questionName)
        # qNode = findQuestionOrTemplateByNameDB(questionName)
        if qNode:
            targetGraphUri = qG.value(
                qNode,
                rdflib.URIRef(questionSubgraphPropertyFor(role)),
                None)
            if targetGraphUri == RDF.nil:
                targetGraphUri = None

    if targetGraphUri:
        qsgName = str(targetGraphUri)
        return NS_file.localize(qsgName);

    # no known relation - get default for a new one
    print("    (No question graph found for Role '%s' and name: %s)" % (role.prefix, questionName))
    return fileService.prepareNameForFile(role.ns().get(questionName + file_ext), False);


def getSubpathForQuestionGraph(name, role: GraphRole, file_ext=".ttl", fileService=get_file_service()):
    file_path = role.ns().get(name)
    if not file_path.endswith(file_ext):
        file_path += file_ext
    return fileService.prepareNameForFile(file_path);


def getQuestionSubgraph(questionName, role, fileService=get_file_service()):
    return fileService.fetchModel(nameForQuestionGraph(questionName, role));


def setQuestionSubgraph(questionName, role, model: Graph, questionNode=None, subgraph_name=None,
                        fileService=get_file_service()):
    qgUri = subgraph_name or nameForQuestionGraph(questionName, role)
    if model:
        fileService.sendModel(qgUri, model);
    # update questions metadata
    questionNode = questionNode or findQuestionByName(questionName)
    # questionNode = questionNode or findQuestionOrTemplateByNameDB(questionName)
    assert questionNode, 'question node must present!'
    qgNode = NS_file.get(qgUri);

    upd_setGraph = makeUpdateTripleQuery(
        rdflib.URIRef(qG_URI).n3(),
        questionNode.n3(),
        rdflib.URIRef(questionSubgraphPropertyFor(role)).n3(),
        rdflib.URIRef(qgNode).n3()
    );

    ### print(upd_setGraph)

    res = sparql_endpoint.update(upd_setGraph)
    print('      SPARQL: set question subgraph response-code:', res.response.code)

    if model:
        # copy has_concept relations to metadata graph (into questions/ NS) ...
        has_concept = rdflib.URIRef(NS_code.get("has_concept"))

        # None ??? >>
        concepts = extract_graph_values(model, subject=None, predicate=has_concept)
        has_concept_qs = rdflib.URIRef(NS_questions.get("has_concept")).n3()
        insert_concepts_query = makeInsertTriplesQuery(
            named_graph=rdflib.URIRef(qG_URI).n3(),
            triples=[
                (questionNode.n3(),
                 has_concept_qs,
                 rdflib.Literal(concept_str).n3())
                for concept_str in concepts
            ]
        )
        res = sparql_endpoint.update(insert_concepts_query)
        print('      SPARQL: insert concepts query response-code:', res.response.code)


def setQuestionSubgraphDB(row_instance, role, new_stage: int, model: Graph, subgraph_path=None, fileService=get_file_service(),
                          _debug_path_suffix=None):
    # qgUri = subgraph_name or nameForQuestionGraph(questionName, role)
    file_subpath = subgraph_path or getSubpathForQuestionGraph(row_instance.name, role)
    db_field_name = tableFieldForRoleDB(role)

    if model:
        if _debug_path_suffix:
            file_subpath += _debug_path_suffix
        fileService.sendModel(file_subpath, model);

    # update question's metadata
    setattr(row_instance, db_field_name, file_subpath)

    if model and role == GraphRole.QUESTION_TEMPLATE:
        # copy has_concept relations to metadata graph (into questions/ NS) ...
        has_concept = rdflib.URIRef(NS_code.get("has_concept"))

        concepts = extract_graph_values(model, subject=None, predicate=has_concept)

        dbmeta.update_bit_field(row_instance, 'concept_bits', dbmeta.names_to_bitmask(concepts, entity=dbmeta.Concepts))

    if new_stage > row_instance._stage:
        row_instance._stage = new_stage
    row_instance._version = dbmeta.TOOL_VERSION
    row_instance.save()


def extract_graph_values(model: Graph, subject: rdflib.URIRef = None, predicate: rdflib.URIRef = None):
    objs = model.objects(subject, predicate)
    return [o.toPython() for o in objs]


def getQuestionModel(questionName, topRole=GraphRole.QUESTION_SOLVED, fileService=get_file_service()):
    if topRole.ordinal() >= GraphRole.QUESTION.ordinal() and (pos := questionName.rfind('_v')) > 0:
        # cut values added to template name
        qt_name = questionName[:pos]
    else:
        qt_name = questionName

    m = Graph()
    for role in questionStages():
        if role.ordinal() >= GraphRole.QUESTION.ordinal():
            graph_name = questionName
        else:
            graph_name = qt_name
        gm = getQuestionSubgraph(graph_name, role, fileService=get_file_service());
        if gm:
            m += gm
        if role == topRole:
            break
    return m


def getQuestionModelDB(qt_or_q, topRole=GraphRole.QUESTION_SOLVED, fileService=get_file_service()):
    if topRole.ordinal() >= GraphRole.QUESTION.ordinal() and isinstance(qt_or_q, dbmeta.Questions):
        qt = qt_or_q.template
        q = qt_or_q
    else:
        qt = qt_or_q
        q = None

    m = Graph();
    for role in questionStages():
        if q and role.ordinal() >= GraphRole.QUESTION.ordinal():
            qt_or_q = q
        else:
            qt_or_q = qt

        subpath = getattr(qt_or_q, tableFieldForRoleDB(role))
        assert subpath, (qt_or_q.name, role)
        gm = fileService.fetchModel(subpath);
        if gm:
            m += gm;

        if (role == topRole): break;
    return m


__schema4solving__m = None


def ctrl_flow_schema(schema_path=r'c:/D/Work/YDev/CompPr/c_owl/jena/control-flow-statements-domain-schema.rdf'):
    global __schema4solving__m
    if not __schema4solving__m:
        __schema4solving__m = Graph().parse(schema_path)
    return __schema4solving__m


def solve_template_with_jena(m: Graph, verbose=False, ) -> Graph:
    schema = ctrl_flow_schema()
    rdfxml_bytes = (m + schema).serialize(format="xml").encode()
    n3_bytes = run_jenaService_with_rdfxml(rdfxml_bytes, alg_only=True)

    assert n3_bytes, n3_bytes

    g = Graph().parse(data=n3_bytes, format='nt')
    initial_size = len(g)
    # leave only new triples
    g -= m
    g -= schema

    if verbose:
        print(f"\t* reasoning result graph has triples: {initial_size} (-> {len(g)})")

    g.bind('', NS_code.get())  # set default namespace
    return g


def solve_templates(limit=None) -> int:
    """ using jena via c_owl
    """

    # templates_total = 0
    done_count = 0

    # qt_list = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_CREATED, limit)
    qt_list = dbmeta.findTemplatesOnStageDB(2, limit)  # solved: to re-solve
    if not qt_list:
        return 0

    ch = Checkpointer()

    for qt in qt_list:

        # path = CONFIG.src_ttl_dir + (qt.src_path)
        # with open(path) as f:
        #     m = _patch_and_parse_ttl(f)
        m = getQuestionModelDB(qt, GraphRole.QUESTION_TEMPLATE)

        # solve...
        try:
            m = solve_template_with_jena(m, verbose=True)
        except Exception:
            print(f'error with template "{qt.name}"')
            # raise
            continue

        setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE_SOLVED, dbmeta.STAGE_QT_SOLVED, m)
        done_count += 1
        if done_count % 20 == 0:
            ch.hit('   + 20 templates solved')
            ch.since_start('[%3d] time elapsed so far:' % done_count)

    ch.since_start("Solving templates completed, in")
    print("Solved", done_count, 'templates of', len(qt_list), 'currently selected.')
    return len(qt_list)


__PATCH_TTL_RE = None


def _patch_and_parse_ttl(file_data):
    global __PATCH_TTL_RE
    if not __PATCH_TTL_RE:
        __PATCH_TTL_RE = re.compile(r'((?<=:return)|(?<=:break)|(?<=:continue))(\s+:stmt)')

    data = __PATCH_TTL_RE.sub(lambda m: m[1] + ',' + m[2], file_data)  # insert ,
    # check if it is changed
    if data != file_data:
        print('DEBUG: TTL data was patched effectively.')

    g = Graph().parse(format='ttl', data=data.encode())
    return g


def load_templates(limit=None) -> int:
    """ rdf metadata:
    * ! Set INIT_GLOBALS and PREFETCH_QUESTIONS to True !
    """

    # templates_total = 0
    done_count = 0

    # qt_list = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_FOUND, limit)
    ### re
    qt_list = dbmeta.findTemplatesOnStageDB(stage=None and dbmeta.STAGE_QT_USED, limit=limit,
                                            version=dbmeta.TOOL_VERSION - 1)
    if not qt_list:
        return 0

    from full_questions import repair_statements_in_graph

    ch = Checkpointer()

    for qt in qt_list:

        path = CONFIG.src_ttl_dir + qt.src_path
        with open(path) as f:
            m = _patch_and_parse_ttl(f.read())

        try:
            random.seed(hash(qt.name))  # make random stable
            m = repair_statements_in_graph(m)
        except AssertionError:
            print(f'error with "{qt.name}"')
            # raise
            # mark the error
            qt._stage = 10 + dbmeta.STAGE_QT_CREATED
            qt.save()
            continue

        file_subpath = setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE, dbmeta.STAGE_QT_CREATED, m)  ### , _debug_path_suffix='.v2'
        done_count += 1
        if done_count % 20 == 0:
            ch.hit('   + 20 templates created')
            ch.since_start('[%3d] time elapsed so far:' % done_count)

    ch.since_start("Loading templates completed, in")
    print("Loaded", done_count, 'templates of', len(qt_list), 'currently selected.')
    return len(qt_list)


def play_extracting_concepts(g: rdflib.Graph):

    raise DeprecationWarning("obsolete");

    gl = graph_lookup(g, PREFIXES)
    data = {}
    ppath = ((gl(':body') | gl(':branches_item')) * '?' / gl(':body_item') | gl(':body'))  ##  * '+'

    # nesting_depth (0 = 1 level, 1 = 2 levels)
    def action_depth(s):
        children = g.objects(s, ppath)
        return 1 + max([-1, *map(action_depth, children)])

    root = [*g.objects(None, gl(':global_code'))][0]
    max_depth = action_depth(root)
    data['nesting_depth'] = max_depth
    print("max_depth:", max_depth)

    # find max loop nesting depth (1 = 1 loop, 1 = 2 loops, one in other)
    loops = list(g.subjects(RDF.type, gl(':loop')))
    # print("loops:", loops)

    if not loops:
        data['max_loop_nesting_depth'] = 0
    else:
        # count how many loops are in each loop ...
        # in_loop__ppath = ~ppath * '+'
        in_loop__ppath = gl(':hasPartTransitive') | ppath * '+';
        nest_depths = [
            sum((L, in_loop__ppath, L2) in g for L2 in loops if L2 is not L)
            for L in loops
        ]
        data['max_loop_nesting_depth'] = max(nest_depths) + 1
        # max_loop_nesting_depth = max(nest_depths) + 1
        # print('max_loop_nesting_depth:', max_loop_nesting_depth)
    return data


def update_template_concepts(limit=None) -> int:
    """ get action types from rdf data
    """

    raise DeprecationWarning("obsolete");

    schema = ctrl_flow_schema()
    action_classes = get_class_descendants_rdf(
        rdflib.URIRef(NS_code.get("action")), schema
    )
    # print("\taction_classes:", action_classes)

    # templates_total = 0
    done_count = 0

    # qt_list = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_FOUND, limit)
    qt_list = dbmeta.findTemplatesOnStageDB(stage=None and dbmeta.STAGE_QT_SOLVED, limit=limit,
                                            version=dbmeta.TOOL_VERSION - 1)
    # qt_list = [dbmeta.findQuestionOrTemplateByNameDB('warmup_15463328')]
    if not qt_list:
        return 0

    # from full_questions import repair_statements_in_graph

    ch = Checkpointer()

    for qt in qt_list:

        # m = getQuestionModelDB(qt, GraphRole.QUESTION_TEMPLATE)
        m = getQuestionModelDB(qt, GraphRole.QUESTION_TEMPLATE_SOLVED)

        try:
            # concepts = [t for t in action_classes if (None, RDF.type, t) in m]
            # concepts = [NS_code.localize(t) for t in concepts]
            # concepts.remove('stmt')  # TODO: verify line

            concepts = []  # ??
            some_metrics = play_extracting_concepts(m)
            if some_metrics['max_loop_nesting_depth'] >= 2:
                concepts.append('nested_loop')  # note the name introduced here

            # show concepts
            print("\tconcepts:", concepts)
        except AssertionError as e:
            print(f'error with "{qt.name}"')
            # raise
            # mark the error
            qt._stage = 10 + dbmeta.STAGE_QT_CREATED
            qt.save()
            continue

        ### file_subpath = setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE, dbmeta.STAGE_QT_CREATED, m)  ### , _debug_path_suffix='.v2'
        new_bits = qt.concept_bits | dbmeta.names_to_bitmask(concepts)
        if qt.concept_bits != new_bits:
            qt.concept_bits |= new_bits
        if some_metrics:
            for k, v in some_metrics.items():
                if getattr(qt, k) != v:
                    setattr(qt, k, v)
        qt._version = dbmeta.TOOL_VERSION
        qt.save()
        if 'update questions as well':
            query = dbmeta.Questions.select()
            query = query.where(dbmeta.Questions.template_id == qt.id)
            iterator = query.execute()
            for q in iterator:
                new_bits = q.concept_bits | new_bits
                if q.concept_bits != new_bits:
                    q.concept_bits |= new_bits
                    q.save()

        done_count += 1
        print('\t\tsaved.')
        if done_count % 20 == 0:
            ch.hit('   + 20 templates updated')
            ch.since_start('[%3d] time elapsed so far:' % done_count)

    ch.since_start("Updating templates completed, in")
    print("Updated", done_count, 'templates of', len(qt_list), 'currently selected.')
    return len(qt_list)


def find_templates(rdf_dir, wanted_ext=".ttl", file_size_filter=(3 * 1024, 40 * 1024), skip_first=0):
    ''' Find files and add info about them to DB
    '''

    files_total = 0
    files_selected = 0

    src_fs = fs.open_fs(rdf_dir)
    for path, info in src_fs.walk.info(namespaces=['details']):
        if not info.is_dir:
            if not info.name.endswith(wanted_ext):
                continue
            files_total += 1

            if skip_first > 0 and files_total < skip_first:
                continue

            if file_size_filter and not (file_size_filter[0] <= info.size <= file_size_filter[1]):
                continue
            files_selected += 1

            # cut last section with digits (timestamp), cut last 12 digits from hash
            name = "_".join(info.name.split("__")[:-1])[:-12]
            print('[%3d]' % files_selected, name, '...')

            # qUri = createQuestionTemplate(name);
            qt = dbmeta.createQuestionTemplateDB(name, src_file_path=path);

    print("Searching for templates completed.")
    print("Used", files_selected, 'files of', files_total, 'in the directory.')


def createQuestionTemplate(questionTemplateName) -> 'question template URI':
    """Deprecated."""
    global qG
    if qG is None:
        # fetch it once as template data is needed only
        qG = fetchGraph(qG_URI);  # questions Graph containing questions metadata
    if qG is None:
        return None

    templNodeExists = (None, rdflib.URIRef(NS_questions.get("name")), rdflib.Literal(questionTemplateName)) in qG;

    if templNodeExists:
        qtemplNode = qG.value(None, rdflib.URIRef(NS_questions.get("name")), rdflib.Literal(questionTemplateName));
        return qtemplNode

    nodeClass = rdflib.URIRef(NS_classQuestionTemplate.base())

    ngNode = rdflib.URIRef(qG_URI);

    # create an uri in QuestionTemplate# namespace !
    qNode = rdflib.URIRef(NS_classQuestionTemplate.get(questionTemplateName));

    commands = [];

    commands.append(makeInsertTriplesQuery(ngNode.n3(), [(
        qNode.n3(),
        RDF.type.n3(),
        nodeClass.n3()
    )]));

    commands.append(makeUpdateTripleQuery(ngNode.n3(),
                                          qNode.n3(),
                                          rdflib.URIRef(NS_questions.get("name")).n3(),
                                          rdflib.Literal(questionTemplateName).n3()));

    # initialize template's graphs as empty ...
    # using "template-only" roles
    for role in (GraphRole.QUESTION_TEMPLATE, GraphRole.QUESTION_TEMPLATE_SOLVED):
        obj = RDF.nil
        commands.append(makeUpdateTripleQuery(ngNode.n3(),
                                              qNode.n3(),
                                              rdflib.URIRef(questionSubgraphPropertyFor(role)).n3(),
                                              obj.n3()));

    full_query = '\n;\n'.join(commands)

    ### print(full_query); # exit()

    res = sparql_endpoint.update(full_query)
    print('      SPARQL: create template response-code:', res.response.code)

    # cannot not update as quad insertion is not for a single graph
    # qG.update(full_query)
    return str(qNode);


class expr_bool_values:
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

    # def __iter__(self): return self
    def __next__(self):
        self.i += 1
        return self.get(self.i - 1)

    def __getitem__(self, index):
        return self.get(index)


# itvs = expr_bool_values(1, 2)
# [itvs[i] for i in range(10)]
# [next(itvs) for _ in range(10)]
# >>>
# [False, True, True, False, False, False, False, False, False, False]


# /**
#  * Create metadata representing empty Question, OVERWRITE any existing data.
#  * @param questionName unique Uri-conformant name of question
#  * @return true on success
#  */
def createQuestion(questionName, questionTemplateName, questionDataGraphUri=None, metrics={}) -> 'question URI':
    global qG
    if qG is None:
        # fetch it once as template data is needed only
        qG = fetchGraph(qG_URI);  # questions Graph containing questions metadata
    if qG is None:
        return None

    nodeClass = rdflib.URIRef(NS_classQuestion.base());

    # (skip checking for duplicates)

    qtemplNode = qG.value(None, rdflib.URIRef(NS_questions.get("name")), rdflib.Literal(questionTemplateName));

    assert qtemplNode, '     (No template found for name: "%s")' % questionTemplateName

    ngNode = rdflib.URIRef(qG_URI);

    # create an uri in Question# namespace !
    qNode = rdflib.URIRef(NS_classQuestion.get(questionName));

    commands = [];

    commands.append(makeUpdateTripleQuery(ngNode.n3(), qNode.n3(), RDF.type.n3(), nodeClass.n3()));

    commands.append(makeUpdateTripleQuery(ngNode.n3(),
                                          qNode.n3(),
                                          rdflib.URIRef(NS_questions.get("name")).n3(),
                                          rdflib.Literal(questionName).n3()));

    commands.append(makeUpdateTripleQuery(ngNode.n3(),
                                          qNode.n3(),
                                          rdflib.URIRef(NS_questions.get("has_template")).n3(),
                                          qtemplNode.n3()));

    # copy references to the graphs from template as is ...
    # using "template-only" roles
    for role in (GraphRole.QUESTION_TEMPLATE, GraphRole.QUESTION_TEMPLATE_SOLVED):
        propOfRole = rdflib.URIRef(questionSubgraphPropertyFor(role));
        graphWithRole = qG.value(qtemplNode, propOfRole, None);
        commands.append(makeUpdateTripleQuery(ngNode.n3(), qNode.n3(), propOfRole.n3(), graphWithRole.n3()));

    # initialize question's graphs as empty ...
    # using "question-only" roles
    for role in (
            GraphRole.QUESTION,
            GraphRole.QUESTION_SOLVED,
            GraphRole.QUESTION_DATA
    ):
        obj = RDF.nil
        if role == GraphRole.QUESTION and questionDataGraphUri:
            obj = rdflib.URIRef(questionDataGraphUri)
        commands.append(makeUpdateTripleQuery(ngNode.n3(),
                                              qNode.n3(),
                                              rdflib.URIRef(questionSubgraphPropertyFor(role)).n3(),
                                              obj.n3()));

    # > add other metadata
    triples = []
    for name, vals in metrics.items():
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        for v in vals:
            triples.append((qNode.n3(), URI(NS_questions.get(name)), rdflib.Literal(v).n3()))

    if triples:
        commands.append(makeInsertTriplesQuery(ngNode.n3(), triples, ))  # PREFIXES
    # < add other metadata

    # runQueries(commands);

    full_query = '\n;\n'.join(commands)

    ### print(full_query); exit()

    res = sparql_endpoint.update(full_query)
    print('      SPARQL: create question response-code:', res.response.code)

    # cannot not update as quad insertion is not for a single graph
    # qG.update(full_query)
    return str(qNode);


def sigmoid(x):
    """Numerically-stable sigmoid function.
    -5   0.006693
    -4   0.017986
    -3   0.047426
    -2   0.119203
    -1   0.268941
     0   0.500000
     1   0.731059
     2   0.880797
     3   0.952574
     4   0.982014
     5   0.993307
    """
    if x >= 0:
        z = exp(-x)
        return 1 / (1 + z)
    else:
        z = exp(x)
        return z / (1 + z)


CONCEPT_CANDIDATES = """expr alternative if else-if else loop while_loop do_while_loop for_loop foreach_loop 
    return break continue 
    alternative_simple alternative_single_with_else 
    alternative_multi_without_else alternative_multi_with_else""".split()  # no `stmt` here.


def question_metrics(g, gl, question_dict, quiet=False):
    data = {}
    add_structural_feature_concepts = True
    concepts = []

    # actions_count
    query = 'SELECT (COUNT(distinct ?s) as ?n) where {?s a :action}'
    r = g.query(query, initNs=PREFIXES)
    actions_count = next(iter(r.bindings[0].values())).toPython()
    data['actions_count'] = actions_count - 1  # omit 'global_code' sequence

    # cyclomatic
    query = 'SELECT (COUNT(?s) as ?n) where {?s a :expr}'
    r = g.query(query, initNs=PREFIXES)
    expr_count = next(iter(r.bindings[0].values())).toPython()
    data['cyclomatic'] = expr_count + 1

    # max_if_branches
    query = '''SELECT (COUNT(?b) as ?n) where {
        ?s :branches_item ?b . ?b a :alt_branch
    } group by ?s'''
    r = g.query(query, initNs=PREFIXES)
    max_if_branches_count = max([next(iter(b.values())).toPython() if b else 0 for b in r.bindings])
    data['max_if_branches'] = max_if_branches_count

    ppath = ((gl(':body') | gl(':branches_item')) * '?' / gl(':body_item'))  ##  * '+'

    # nesting_depth  (0 = 1 level, 1 = 2 levels)
    def action_depth(s):
        children = g.objects(s, ppath)
        return 1 + max([0, *map(action_depth, children)])

    root = [*g.objects(None, gl(':global_code'))][0]
    max_depth = action_depth(root) - 1
    data['nesting_depth'] = max_depth

    # find max loop nesting depth (1 = 1 loop, 1 = 2 loops, one in another)

    # query = 'SELECT ?s where {?s a :loop}'
    # r = g.query(query, initNs=PREFIXES)
    # loops = [next(iter(b.values())) for b in r.bindings]
    loops = list(g.subjects(RDF.type, gl(':loop')))
    if not loops:
        data['max_loop_nesting_depth'] = 0
    else:
        # count how many loops are in each loop ...
        in_loop__ppath = gl(':hasPartTransitive') | (ppath | gl(':body')) * '+';
        nest_depths = [
            sum((L, in_loop__ppath, L2) in g for L2 in loops if L2 is not L)
            for L in loops
        ]
        data['max_loop_nesting_depth'] = max(nest_depths) + 1

        if add_structural_feature_concepts and data['max_loop_nesting_depth'] >= 2:
            concepts.append('nested_loop')  # note the name introduced here

    #### cyclomatic = len(question_dict['name_suffix']) + 1  # Bad way as values count is NOT condtion count.
    values_count_plus_1 = len(question_dict['name_suffix']) + 1  # Bad way as values count is NOT condition count.

    tags = ["C++", "trace"]

    for concept in CONCEPT_CANDIDATES:
        if (None, RDF.type, gl(':' + concept)) in g:
            concepts.append(concept)
        # else:
        #     print("          [DEBUG] concept not found:", concept)

    ## cyclomatic = data['cyclomatic']
    solution_steps = question_dict['length']
    # % 4. - лучший на текущий момент
    # % точность 0.984848 на: (concepts+2), solution_steps, bad_cyclomatic
    # % [0.39399354, 0.16434003, 0.01391854, 0.05685927]

    learned_compexity = (0.39399354
                         + 0.16434003 * (len(concepts) + 2)
                         + 0.01391854 * solution_steps
                         + 0.05685927 * values_count_plus_1)

    complexity = learned_compexity
    x = (complexity - 2) * 5
    integral = sigmoid(x)
    if not quiet: print('    Question complexity: %f  --> integral_complexity: %5f' % (complexity, integral))

    return dict(
        solution_structural_complexity=round(complexity),  # ???
        solution_steps=question_dict['length'],
        distinct_errors_count=len(question_dict['possible_violations']),
        integral_complexity=round(integral, 4),  # 5 digits precision
        has_tag=tuple(tags),
        has_concept=tuple(sorted(concepts)),
        has_law=tuple(sorted(question_dict['laws'])),
        has_violation=tuple(sorted(question_dict['possible_violations'])),
        structural_complexity=data['actions_count'] + data['cyclomatic'],
        **data,  # data:
        # 'actions_count'
        # 'cyclomatic'
        # 'max_if_branches'
        # 'nesting_depth'
        # 'max_loop_nesting_depth'
    )


def question_trace_features(g, gl, q, quiet=False):
    data = jsObj()
    data.more_concepts = []
    # data.flags = {}  # see below
    data.numeric = {}

    # has-nested relation
    ppath = ((gl(':body') | gl(':branches_item')) * '?' / gl(':body_item'))  ##  * '+'

    # seq_longer_than1 : следование (более 1 элемента)
    # max seq child actions
    query = '''SELECT (COUNT(?b) as ?n) where {
        ?s a :sequence . ?s :body_item ?b .
    } group by ?s'''
    r = g.query(query, initNs=PREFIXES)
    max_seq_child_actions = max([next(iter(b.values())).toPython() if b else 0 for b in r.bindings])
    if max_seq_child_actions > 1:
        data.more_concepts.append('seq_longer_than1')

    data.numeric['longest_seq_count'] = max_seq_child_actions

    # selection_count
    query = 'SELECT (COUNT(distinct ?s) as ?n) where {?s a :alternative}'
    r = g.query(query, initNs=PREFIXES)
    selection_count = next(iter(r.bindings[0].values())).toPython()
    data.numeric['selection_count'] = selection_count

    # loop_count
    query = 'SELECT (COUNT(distinct ?s) as ?n) where {?s a :loop}'
    r = g.query(query, initNs=PREFIXES)
    loop_count = next(iter(r.bindings[0].values())).toPython()
    data.numeric['loop_count'] = loop_count

    # max_selection_nesting_depth
    alts = list(g.subjects(RDF.type, gl(':alternative')))
    if not alts:
        data.numeric['max_selection_nesting_depth'] = 0
    elif len(alts) == 1:
        data.numeric['max_selection_nesting_depth'] = 1
    else:
        # count how many alts are in each alt ...
        in_alt__ppath = gl(':hasPartTransitive') | (ppath | gl(':body')) * '+';
        nest_depths = [
            sum((A, in_alt__ppath, A2) in g for A2 in alts if A2 is not A)
            for A in alts
        ]
        data.numeric['max_selection_nesting_depth'] = max(nest_depths) + 1

    # avg_if_branches
    query = '''SELECT (COUNT(?b) as ?n) where {
        ?s :branches_item ?b . ?b a :alt_branch
    } group by ?s'''
    r = g.query(query, initNs=PREFIXES)
    avg_if_branches_count = avg([next(iter(b.values())).toPython() if b else 0 for b in r.bindings])
    data.numeric['avg_if_branches'] = avg_if_branches_count

    trace_data = _trace_features(g, gl, q, quiet)
    data.numeric = {**data.numeric, **trace_data.numeric}
    data.flags = trace_data.flags

    return data


def _trace_features(g, gl, q, quiet=False):
    from collections import defaultdict

    data = jsObj()
    data.flags = {}  # see below
    data.numeric = {}

    act_begin = gl(':act_begin')
    act_end = gl(':act_end')
    executes = gl(':executes')
    _next = gl(':next')
    next_act = gl(':next_act')
    boundary_of = gl(':boundary_of')
    begin_of = gl(':begin_of')
    end_of = gl(':end_of')
    cond = gl(':cond')
    branches_item = gl(':branches_item')
    body = gl(':body')
    expr_value = gl(':expr_value')
    _true = rdflib.Literal(True)
    _false = rdflib.Literal(False)

    # fetch trace first
    acts = []
    first_acts = list(set(g.subjects(executes / RDF.type, gl(':algorithm'))))
    if first_acts:
        acts.append(first_acts[0])
        act_inst = acts[0]
        while (act_inst := g.value(act_inst, next_act)):
            acts.append(act_inst)

    assert acts, (acts, first_acts)

    # 2+of-seq (выполнилось более 1 элемента следования (не 100% равно что такое следование есть т.к. return/break/continue))
    for inst, next_inst in zip(acts[:-1], acts[1:]):
        # pair-wise: check if subsequent acts run actions of the same seq
        if (
                (inst, RDF.type, act_end) in g
                and
                (next_inst, RDF.type, act_begin) in g
                and
                (
                        g.value(next_inst, executes / boundary_of, None) ==
                        g.value(next_inst, executes / boundary_of, None)
                )
        ):
            st1 = g.value(next_inst, executes / boundary_of, None)
            st2 = g.value(next_inst, executes / boundary_of, None)
            if st1 == st2 and (st1, RDF.type, gl(':sequence')) in g:
                # yes
                data.flags['2+of-seq'] = True
                break

    # 'if-cond-is-true'
    if_expr_acts = set(g.subjects(executes / end_of / ~cond / RDF.type, gl(':if')))
    if if_expr_acts:
        if_cond_is_true = any((e, expr_value, _true) in g for e in if_expr_acts)
        if if_cond_is_true:
            data.flags['if-cond-is-true'] = True

        # when cond is false...
        # if-cond-is-false_having-1-branch
        # if-cond-is-false_having-else-only
        # if-cond-is-false_having-elseif
        for e in if_expr_acts:
            if (e, expr_value, _false) in g:
                branch = g.value(e, executes / end_of / ~cond, None)
                next_branch = g.value(branch, _next, None)
                if not next_branch:
                    data.flags['if-cond-is-false_having-1-branch'] = True
                elif (next_branch, RDF.type, gl(':else')) in g:
                    data.flags['if-cond-is-false_having-else-only'] = True
                elif (next_branch, RDF.type, gl(':else-if')) in g:
                    data.flags['if-cond-is-false_having-elseif'] = True

    # 'elseif-cond-is-true'
    elseif_expr_acts = set(g.subjects(executes / end_of / ~cond / RDF.type, gl(':else-if')))
    if elseif_expr_acts:
        elseif_cond_is_true = any((e, expr_value, _true) in g for e in elseif_expr_acts)
        if elseif_cond_is_true:
            data.flags['elseif-cond-is-true'] = True

        # when cond is false...
        # elseif-cond-is-false_having-elseif-next
        # elseif-cond-is-false_having-else-next
        # elseif-cond-is-false_and-last
        for e in elseif_expr_acts:
            if (e, expr_value, _false) in g:
                branch = g.value(e, executes / end_of / ~cond, None)
                next_branch = g.value(branch, _next, None)
                if not next_branch:
                    data.flags['elseif-cond-is-false_and-last'] = True
                elif (next_branch, RDF.type, gl(':else')) in g:
                    data.flags['elseif-cond-is-false_having-else-next'] = True
                elif (next_branch, RDF.type, gl(':else-if')) in g:
                    data.flags['elseif-cond-is-false_having-elseif-next'] = True

    # loops: localize iterations over trace
    # warning: (?) recursion is not taken into account (TODO)
    # corresponding_end = gl(':corresponding_end')
    # any_corresponding_end = list(g.subject_objects(corresponding_end))  # no!

    action_stack = []  # [{action: URIRef, type: str, expr_values: [], }]
    action_types = tuple(map(gl, ':alternative :for_loop :while_loop :do_while_loop'.split()))
    interrupt_types = tuple(map(gl, ':return :break :continue'.split()))
    selection_to_branches_entered = defaultdict(int)
    loop_to_iterations_entered = defaultdict(int)
    for act_inst in acts:
        action = g.value(act_inst, executes / boundary_of, None)
        if not action:
            continue  # skip `algorithm`
        if (act_inst, RDF.type, act_begin) in g and (act_inst, executes / begin_of, None) in g:
            for action_type in action_types:
                if (action, RDF.type, action_type) in g:
                    action_stack.append(jsObj(
                        action=action,
                        type=NS_code.localize(action_type.toPython()),
                        expr_values=[],
                    ))
                    break  # inner for

            # 'max_if_branches_entered'
            if (selection_st := g.value(action, ~branches_item, None)) is not None:
                selection_to_branches_entered[selection_st] += 1
                ### print('selection_st:', selection_st, '---', selection_to_branches_entered[selection_st], ' act:', act_inst)

            # 'avg_iterations', 'max_iterations'
            if (loop_st := g.value(action, ~body, None)) and ((loop_st, RDF.type, gl('loop')) in g):
                loop_to_iterations_entered[loop_st] += 1

        else:
            # elif (act_inst, RDF.type, act_end) in g:
            # cond value
            if (act_value := g.value(act_inst, expr_value, None)) is not None:
                bool_value = act_value.toPython()
                if action_stack:
                    action_stack[-1].expr_values.append(bool_value)
                    enclosing_action = action_stack[-1].type
                    if enclosing_action.endswith('_loop'):
                        loop_name = enclosing_action[:-len('_loop')]
                        iteration_n = len(action_stack[-1].expr_values)
                        if iteration_n > 2 or iteration_n == 2 and (bool_value is False or loop_name == 'do_while'):
                            continue  # need not record anything about this cond act
                        flag_name = f"{loop_name}-cond-is-{str(bool_value).lower()}_at-iteration-{iteration_n}"
                        data.flags[flag_name] = True
                continue

            if action_stack and action == action_stack[-1].action:
                action_stack.pop()
                continue

            for action_type in interrupt_types:
                if (action, RDF.type, action_type) in g:
                    action_kind = NS_code.localize(action_type.toPython())
                    if action_kind == 'return' and not action_stack:
                        # hard guard (since there are some bugs with interrupting flow in generator)
                        if 'return-in-selection' not in data.flags and 'return-in-loop' not in data.flags:
                            data.flags['return-in-toplevel-code'] = True
                            break

                    if action_stack:
                        enclosing_action = action_stack[-1].type
                        if enclosing_action == 'alternative':
                            flag_name = f"{action_kind}-in-selection"
                            data.flags[flag_name] = True
                            break

                        if enclosing_action.endswith('_loop'):
                            if action_kind == 'return':
                                data.flags['return-in-loop'] = True
                                break

                            # check if outer loop present
                            is_loop_nested = False
                            for outer_action in reversed(action_stack[:-1]):
                                if outer_action.endswith('_loop'):
                                    is_loop_nested = True
                                    break
                            flag_name = f"{action_kind}-in-{'nested' if is_loop_nested else 'toplevel'}-loop"
                            data.flags[flag_name] = True
                    break
    # finished `for` over acts.

    data.numeric['max_if_branches_entered'] = max(list(selection_to_branches_entered.values()) or [0])

    iterations_count = list(loop_to_iterations_entered.values()) or [0]
    data.numeric['max_iterations'] = max(iterations_count)
    data.numeric['avg_iterations'] = avg(iterations_count)

    return data


import threading

CREATE_TRACES_TIMEOUT = 15  # seconds

# CLAMP_COMPLEXITY = (0.1, 0.6)
CLAMP_COMPLEXITY = (0.1, 0.8)
# CLAMP_COMPLEXITY = (0.5, 1.0)
MAX_ACTIONS_COUNT = 20


def process_template(qt, questions_counter=0, clamp_complexity=CLAMP_COMPLEXITY):
    """Create questions from template"""
    qtname = qt if isinstance(qt, str) else qt.name

    # g = getQuestionModel(qtname, GraphRole.QUESTION_TEMPLATE_SOLVED)
    g = getQuestionModelDB(qt, GraphRole.QUESTION_TEMPLATE_SOLVED)
    gl = graph_lookup(g, PREFIXES)

    # from full_questions import repair_statements_in_graph
    # g = repair_statements_in_graph(g, gl)

    # old code: just call it
    # questions = generate_questions_for_algorithm(g, gl)

    # new code: kill process on timeout
    questions = None  ## ()  # nothing by default

    def process_one(g, gl):
        nonlocal questions
        questions = generate_questions_for_algorithm(g, gl)

    t = threading.Thread(target=process_one, args=(g, gl))
    set_interrupt_flag(False)
    t.start()
    # Wait for at most 30 seconds for the thread to complete.
    t.join(CREATE_TRACES_TIMEOUT)
    set_interrupt_flag(True)
    # Now join without a timeout knowing that the thread is either already
    # finished or will finish "soon".
    t.join()

    # [{'name_suffix': '000',
    #     'length': 18,
    #     'depth': 7,        # < TODO
    #     'laws': frozenset({'AltBegin',
    #                'AltEndAllFalse',
    #                'SequenceBegin',
    #                'SequenceEnd',
    #                'SequenceNext'}),
    #     'possible_violations': frozenset({'DuplicateOfAct',
    #                'LastFalseNoEnd',
    #                'NoFirstCondition',
    #                'SequenceFinishedTooEarly',
    #                'TooEarlyInSequence'}),
    #     'rdf': <Graph>}]

    print("Total questions generated: ", questions and len(questions) or 0)

    if not questions:
        return ()

    seen_names = set()
    saved_questions = []

    for question in questions:
        if question['name_suffix'] in seen_names:
            continue  # prevent processing duplicates
        seen_names.add(question['name_suffix'])

        print()
        metrics = question_metrics(g, gl, question)
        if clamp_complexity:
            name_suffix = question['name_suffix']
            print(f"    name_suffix = {name_suffix}")
            # ### !!! Get only ones with 'true' values !!! ###
            # if '1' not in name_suffix:
            #     print(f'-x- Skip this question: name_suffix = {name_suffix} has no "true"')
            #     continue

            actions_count = metrics['actions_count']
            if actions_count > MAX_ACTIONS_COUNT:
                print(f'-x- Cannot take this question: actions_count = {actions_count} > max of {MAX_ACTIONS_COUNT}')
                continue

            complexity = metrics['integral_complexity']
            low, high = clamp_complexity
            if not (low <= complexity <= high):
                print(f'-x- Cannot take this question: complexity = {complexity} is not within [{low} , {high}]')
                continue

        suffix = question['name_suffix'] or ('_nocond_q%d' % questions_counter)
        question_name = '%s_v%s' % (qtname, suffix)

        file_path = getSubpathForQuestionGraph(question_name, GraphRole.QUESTION)
        # file_path = nameForQuestionGraph(question_name, GraphRole.QUESTION)
        assert file_path, question_name
        print("  Saving question: ", question_name, ' --> ', file_path)
        ### continue

        model = question['rdf']
        print("    Uploading model ...")  # "for question '%s' ... " % question_name)
        # uploadGraph(gUri, model, fuseki_update)
        for _i in range(3):
            try:
                if _i > 0: print("       [NETWORK] Retry uploading model: take %d" % _i)
                fileService.sendModel(file_path, model)
                break
            except:
                continue

        new_q = dbmeta.createQuestionDB(question_name, qt, q_graph=file_path, metrics=metrics)
        saved_questions.append(new_q)

        # gUri = NS_file.get(file_path)
        # qUri = createQuestion(question_name, qtname, gUri, metrics)
        # print("  Question URI:", qUri)

    return saved_questions


def generate_questions_for_templates(offset=None, limit=None):
    print("Requesting templates without questions ...", flush=True)
    # if limit:
    #     sparql_limit = limit
    #     limit = None
    # else:
    #     sparql_limit = None
    # templates_to_create_questions = templatesWithoutQuestions(sparql_limit)
    # templates_to_create_questions = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_SOLVED, limit)
    templates_to_create_questions = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_USED, limit=None, version=None)

    ### debugging: get existing questions instead
    # templates_to_create_questions = list({n[:n.rfind("_v")] for n in unsolvedQuestions(GraphRole.QUESTION_SOLVED)})

    print('Templates without questions found: %d' % len(templates_to_create_questions))

    # print(*templates_to_create_questions, sep='\n')
    # exit()

    templates_used = 0
    questions_count = 0
    skip_count = 0

    ch = Checkpointer()

    filter_by_concepts = 0
    # filter_by_concepts = dbmeta.names_to_bitmask(['break', 'continue'])

    # for qtname in templates_to_create_questions[offset:limit]:
    for qt in templates_to_create_questions:

        if qt._version >= dbmeta.TOOL_VERSION:
            continue

        if filter_by_concepts:
            if not (qt.concept_bits & filter_by_concepts):
                continue

        qtname = qt.name

        print()
        print()
        print("Processing template: ", qtname)
        print("    (skipped so far: %d)" % skip_count)
        print("========")
        if qtname in ('curl_mvsnprintf',):
            print('intended skip.')
            continue
        try:
            questions_made = process_template(qt, questions_count)
            questions_count += len(questions_made)
            templates_used += 1
            # set even if no questions made, to avoid trying it next time
            qt._stage = dbmeta.STAGE_QT_USED
            qt._version = dbmeta.TOOL_VERSION
            qt.save()
            if questions_made > 0:
                ch.hit('   + 1 template used')
                ch.since_start('[%3d] time elapsed so far:' % (templates_used + skip_count))
        except NotImplementedError as e:
            skip_count += 1
            print()
            print('Error with template: ', qtname)
            print(e)
            print()

        if questions_count > limit:  break

    print()
    ch.since_start("Completed in")
    print(questions_count, 'questions created from', templates_used, 'templates.')
    print('done.')
    return questions_count


def generate_data_for_question(q_row_instance) -> 'q_row or None':
    """ generating data for question """
    q = q_row_instance
    qname = q.name
    g = getQuestionModelDB(q, GraphRole.QUESTION)
    # gl = graph_lookup(g, PREFIXES)

    from full_questions import convert_graph_to_json
    alg_json = convert_graph_to_json(g, remove_acts_bounds=False)

    # ## dump alg_json to debug
    # # fileService.sendFile(file_subpath[:-4] + 'src.json',
    # fileService.sendFile('debug/' + qname + 'src.json',
    #     # json.dumps(q_dict, ensure_ascii=False).encode()
    #     json.dumps(alg_json, ensure_ascii=False, indent=2).encode()
    # )
    # return 0  # !!!!!!!!!!!!!!!!!!!
    # ## / dump alg_json to debug

    try:
        q_dict = make_question_dict_for_alg_json(alg_json, qname)

        # fill metadata (CompP format) for the question
        metadata = dict(
            name = q.name,
            domain_shortname = 'control_flow',
            template_id = q.template.id,
            qt_graph = None,
            qt_s_graph = None,
            q_graph = None,
            q_s_graph = None,
            q_data_graph = q.q_data_graph,
            tag_bits = q.tag_bits,
            concept_bits = q.concept_bits,
            law_bits = q.law_bits,
            violation_bits = q.violation_bits,
            trace_concept_bits = q.trace_concept_bits,
            solution_structural_complexity = q.solution_structural_complexity,
            integral_complexity = q.integral_complexity,
            solution_steps = q.solution_steps,
            distinct_errors_count = q.distinct_errors_count,
            _stage = q._stage,
            _version = q._version,
        )
        # q_dict['metadata'] = metadata
        q_dict['questionData']['options']['metadata'] = metadata

        # use proper metadata
        q_dict["concepts"] = sorted(dbmeta.bitmask_to_names(q.concept_bits, entity=dbmeta.Concepts))
        q_dict["negativeLaws"] = sorted(dbmeta.bitmask_to_names(q.violation_bits, entity=dbmeta.Violations))


        # fullname = nameForQuestionGraph(qname, GraphRole.QUESTION_DATA, file_ext=".json")
        file_subpath = getSubpathForQuestionGraph(qname, GraphRole.QUESTION_DATA, file_ext=".json")

        # print('    Uploading json file ...')
        fileService.sendFile(file_subpath,
                             json.dumps(q_dict, ensure_ascii=False).encode()
                             # json.dumps(q_dict, ensure_ascii=False, indent=2).encode()
                             )

        # setQuestionSubgraph(qname, GraphRole.QUESTION_DATA, model=None, subgraph_name=file_subpath)
        setQuestionSubgraphDB(q, GraphRole.QUESTION_DATA, dbmeta.STAGE_Q_DATA_SAVED, model=None,
                              subgraph_path=file_subpath)

        return q
    except Exception as e:
        print("exception in generate_data_for_question:")
        print(e)
        print()
        raise
        q._stage += 10  # mark the error
        q.save()
        return None


def generate_data_for_questions(offset=None, limit=None):
    print("Requesting questions without data ...", flush=True)

    # questions_to_process = unsolvedQuestions(GraphRole.QUESTION_DATA)
    questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_CREATED, limit)
    # questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_DATA_SAVED, limit, dbmeta.TOOL_VERSION - 1)

    ### debugging: get all existing questions instead
    # questions_to_process = unsolvedQuestions(GraphRole.QUESTION_SOLVED)

    print('Questions without data found: %d' % len(questions_to_process))

    questions_count = 0
    skip_count = 0

    for q in questions_to_process[offset:limit]:
        qname = q.name
        print()
        print()
        print("Processing question: ", qname, "(i: %d)" % (questions_count + skip_count))
        print("    (with errors so far: %d)" % skip_count)
        print("========")
        try:
            q = generate_data_for_question(q)
            n = 1 if q else 0
            questions_count += n
            skip_count += not n
        except (NotImplementedError, AssertionError) as e:
            skip_count += 1
            print()
            print('Error with question: ', qname)
            print(e)
            q._stage += 10  # mark the error
            q.save()
            print()

    print()
    print(questions_count, 'questions updated with data.')
    print(skip_count, 'questions with errors.')
    print('done.')
    return questions_count


def update_questions_trace_concepts(limit=None):

    raise DeprecationWarning("obsolete");

    print("Requesting not updated questions ...", flush=True)

    # questions_to_process = unsolvedQuestions(GraphRole.QUESTION_DATA)
    # questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_CREATED, limit)
    questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_DATA_SAVED)  # , limit, dbmeta.TOOL_VERSION - 1)

    # # custom filter
    # questions_to_process = [q for q in questions_to_process if q.trace_concept_bits == 0]
    questions_to_process = [q for q in questions_to_process if q._version < dbmeta.TOOL_VERSION]

    print('Questions not-updated found: %d' % len(questions_to_process))

    schema = ctrl_flow_schema()
    gl = graph_lookup(schema, PREFIXES)
    ppath = (gl(':executes') / gl(':boundary_of') / RDF.type)

    # action_classes = get_class_descendants_rdf(
    #     rdflib.URIRef(NS_code.get("action")), schema
    # )
    # print("\taction_classes:", action_classes)

    questions_count = 0
    skip_count = 0

    for q in questions_to_process[-limit:]:
        qname = q.name
        print()
        print("Updating question: ", qname, "(i: %d)" % (questions_count + skip_count))
        try:
            g = getQuestionModelDB(q, GraphRole.QUESTION)
            executed_actions = set(extract_graph_values(g, None, ppath))
            # print(executed_actions)
            trace_action_classes = sorted(filter(None,
                                                 ((NS_code.localize(uri) or '') for uri in executed_actions)
                                                 ))
            trace_action_classes = [t for t in trace_action_classes if t in CONCEPT_CANDIDATES]

            print(trace_action_classes, end=' ==> ')
            bitmask = dbmeta.names_to_bitmask(trace_action_classes)
            print(bitmask)
            q.trace_concept_bits = bitmask
            q._version = dbmeta.TOOL_VERSION
            q.save()

            questions_count += 1
            # skip_count += not n
        except (NotImplementedError, AssertionError) as e:
            skip_count += 1
            print()
            print('Error with question: ', qname)
            print(e)
            q._stage = dbmeta.STAGE_Q_DATA_SAVED + 10  # mark the error
            q.save()
            print()

    print()
    print(questions_count, 'questions updated with data.')
    print(skip_count, 'questions with errors.')
    print('done.')
    return questions_count


def update_questions_trace_features(limit=None):
    """Update trace_features_json column with trace features calculated from question data where not set"""
    print("Requesting not updated questions ...", flush=True)

    # questions_to_process = unsolvedQuestions(GraphRole.QUESTION_DATA)
    # questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_CREATED, limit)
    questions_to_process = dbmeta.findQuestionsOnStageDB(dbmeta.STAGE_Q_DATA_SAVED)  # , limit, dbmeta.TOOL_VERSION - 1)

    # # custom filter
    # questions_to_process = [q for q in questions_to_process if q.trace_concept_bits == 0]
    questions_to_process = [q for q in questions_to_process if q._version < dbmeta.TOOL_VERSION]

    total = len(questions_to_process)
    print('Questions not-updated found: %d' % total)

    schema = ctrl_flow_schema()
    gl = graph_lookup(schema, PREFIXES)
    ppath = (gl(':executes') / gl(':boundary_of') / RDF.type)

    # action_classes = get_class_descendants_rdf(
    #     rdflib.URIRef(NS_code.get("action")), schema
    # )
    # print("\taction_classes:", action_classes)

    questions_count = 0
    skip_count = 0

    qt_feature_columns = "structural_complexity actions_count cyclomatic max_if_branches nesting_depth max_loop_nesting_depth".split()

    for q in questions_to_process[:limit:]:
        qname = q.name
        print()
        print("Updating question: ", qname, "(i: %d)" % (questions_count + skip_count))
        try:
            # ###
            # qf_str = q.trace_features_json
            # if '"max_if_branches_entered": 0' in qf_str:
            #     q._version = dbmeta.TOOL_VERSION
            #     q.save()
            #     questions_count += 1
            #     continue

            trace_features_json = {'flags': {}, 'numeric': {}}

            qt = q.template

            # get useful data from qt
            for key in qt_feature_columns:
                trace_features_json['numeric'][key] = getattr(qt, key) or 0

            g = getQuestionModelDB(q, GraphRole.QUESTION)

            data = question_trace_features(g, gl, q, quiet=False)

            # if data.more_concepts:
            #     bitmask = dbmeta.names_to_bitmask(data.more_concepts)
            #     # print(bitmask)
            #     q.concept_bits |= bitmask
            #     q.trace_concept_bits |= bitmask
            #     del data['more_concepts']

            trace_features_json['flags'] |= data.flags
            trace_features_json['numeric'] |= data.numeric
            ### print(trace_features_json)

            q.trace_features_json = json.dumps(trace_features_json)

            ###
            q._version = dbmeta.TOOL_VERSION
            q.save()

            questions_count += 1
            # skip_count += not n
            if questions_count % 20 == 0:
                print('   ... total unprocessed: ', total)
        except (NotImplementedError, AssertionError) as e:
            skip_count += 1
            print()
            print('Error with question: ', qname)
            print(e)
            q._stage = dbmeta.STAGE_Q_DATA_SAVED + 10  # mark the error
            q.save()
            print()

    print()
    print(questions_count, 'questions updated with data.')
    print(skip_count, 'questions with errors.')
    print('done.')
    return questions_count


def make_questions__main():
    if 1:
        generate_questions_for_templates(0, None)  # 30
        exit(0)
    else:
        # qtname = 'packet_queue_get'
        qtname = 'SDL_CondWaitTimeout'
        print("========", flush=True)
        questions_count = len(process_template(qtname))
        print()
        print(questions_count, 'questions created for template.')


def add_concepts_from_list(file_path='new_types_assigned.txt'):
    'insert `has_concept` relations to questions by name based on (tsv-like) data from a text file'
    from pathlib import Path
    text = Path(file_path).read_text()
    tasks = [s.split('\t', maxsplit=1) for s in text.splitlines()]
    # print(tasks[:30])

    insert_concept_query = '''insert {  GRAPH <http://vstu.ru/poas/questions> {
  ?s <http://vstu.ru/poas/questions/has_concept> %s .
  }}
where {  GRAPH <http://vstu.ru/poas/questions> {
    ?s <http://vstu.ru/poas/questions/has_template> / <http://vstu.ru/poas/questions/name> "%s" .
}}'''
    # insert_concept_query % (comma-separated double-quoted strings, template name)

    _sparql_endpoint = get_endpoint()

    print(len(tasks), 'questions templates to update, starting ...')
    ###
    skipping = True
    begin_after = 'add_dimension_to_app_chart'
    ###
    for template_name, concepts in tasks:
        if template_name == begin_after:
            skipping = False
            continue
        if skipping: continue
        print(template_name, '...')
        # split, qoute & join (there may be several words on the line)
        concepts = ', '.join('"%s"' % s for s in concepts.split())
        query = insert_concept_query % (concepts, template_name)
        res = _sparql_endpoint.update(query)
        print('      SPARQL: insert_concept response-code:', res.response.code)

    print('Finished updating questions.')


def float_range(start, stop, step):
    while start < stop:
        yield float(start)
        start += step  #### += decimal.Decimal(step)


def make_questions_sample(src_graph='http://vstu.ru/poas/questions',
                          dest_graph='http://vstu.ru/poas/selected_questions', size=100, bins=20):
    ''' Copy a sample of questions with templates from src named graph to dest named graph keeping all the range of available complexity '''
    import random

    sparql_endpoint = get_endpoint()

    # select all values from src_graph first
    select_all_questions = '''SELECT ?q ?complexity
    where { GRAPH <%s> {
        ?q a <http://vstu.ru/poas/questions/Question> .
        ?q <http://vstu.ru/poas/questions/integral_complexity> ?complexity.
    }}''' % src_graph

    query_results = sparql_endpoint.query(select_all_questions, return_format="json")
    cplx_qs = [(float(b['complexity']['value']), b['q']['value'])
               for b in query_results['results']['bindings']]
    del query_results
    print(len(cplx_qs), 'questions total.')

    complexities = [t[0] for t in cplx_qs]
    min_c = min(complexities)
    max_c = max(complexities)
    if min_c == max_c:
        bins = 1
    step = (max_c - min_c) / bins
    count_per_step = int(math.ceil(size / bins))

    sample = []
    # eps = step * 0.0001
    for L in float_range(min_c, max_c, step):
        R = L + step
        sub_sample = [uri for v, uri in cplx_qs if L <= v <= R]
        print(len(sub_sample), "\tsamples within range [%f, %f]" % (L, R))
        # select limited number of those
        sub_sample = random.sample(sub_sample, count_per_step)
        sample += sub_sample

    sample = list(set(sample))  # filter possible duplicates (taken on sub-range boundaries)
    print(len(sample), 'questions sampled.')
    ### print(sample[:2])  # [(0.3385, 'http://vstu.ru/poas/questions/Question#kuhl_m_sekurlsa_krbtgt_keys_v100'), (0.4676, 'http://vstu.ru/poas/questions/Question#computeJD_v010010')]

    copy_question = '''INSERT {
    GRAPH <%s> {
        ?s ?qp ?qo .
        ?t ?tp ?to .
      }}
    where {
      GRAPH <%s> {
        ?s <http://vstu.ru/poas/questions/has_template> ?t.
        ?s ?qp ?qo .
        ?t ?tp ?to .
      }}''' % (dest_graph, src_graph)
    # copy_question.replace("?s", '<%s>' % question_uri)

    for question_uri in sample:
        query = copy_question.replace("?s", '<%s>' % question_uri)
        res = sparql_endpoint.update(query)
        print('      SPARQL: insert_concept response-code:', res.response.code)

    print('Finished selecting questions.')


def archive_required_files(src_graph='http://vstu.ru/poas/selected_questions',
                           target_zip='./selected_questions-files.zip'):
    import fs.copy
    from fs import open_fs
    from fs.zipfs import WriteZipFS
    import zipfile

    sparql_endpoint = get_endpoint()

    # <http://vstu.ru/poas/questions/has_graph_qt_s>
    # select all values from src_graph first
    select_all_files = '''SELECT distinct ?f
    where { GRAPH <%s> {
        { [] <http://vstu.ru/poas/questions/has_graph_qt_s> ?f }
        union
        { [] <http://vstu.ru/poas/questions/has_graph_qt>   ?f }
        union
        { [] <http://vstu.ru/poas/questions/has_graph_q>    ?f }
        union
        { [] <http://vstu.ru/poas/questions/has_graph_q_s>  ?f }
    }}''' % src_graph

    query_results = sparql_endpoint.query(select_all_files, return_format="json")
    file_uris = [b['f']['value']
                 for b in query_results['results']['bindings']]
    del query_results

    # convert to paths & filter "blank" values
    # print(file_uris)
    file_uris = [NS_file.localize(u) for u in file_uris if u not in ("rdf:nil", str(RDF.nil))]
    # print()
    # print(file_uris)

    print(len(file_uris), 'files total.')

    # save files to archive
    assert target_zip.lower().endswith('.zip')
    src_fs = open_fs(FTP_DOWNLOAD_BASE)
    dst_fs = WriteZipFS(target_zip, compression=zipfile.ZIP_DEFLATED)

    print('copying ..', end='')
    for sub_path in file_uris:
        if not src_fs.exists(sub_path):
            print('! path not found:', sub_path)
            continue

        dst_fs.makedirs(fs.path.dirname(sub_path), recreate=True)
        # fs.copy.copy_file_if(src_fs, src_path, dst_fs, dst_path, condition, preserve_time=False)
        src_path = sub_path
        dst_path = sub_path
        fs.copy.copy_file_if(src_fs, src_path, dst_fs, dst_path, condition="newer", preserve_time=False)
        print('.', end='')

    print(' completed.')

    # Saving is performed automatically when the ZipFS is closed.
    dst_fs.close()

    print('Archive saved.')


def just_rdfdb_monitoring():
    from time import sleep
    sw = CONFIG.rdfdb_watcher
    while True:
        sw.take_snapshot()
        print(end='.')
        sleep(5)


def _insert_triples(triples, ng_uri=rdflib.URIRef(qG_URI).n3()):
    sparql_text = makeInsertTriplesQuery(ng_uri, triples)
    sparql_endpoint.update(sparql_text)


def measure_disk_usage_uploading_questions(rdf_src_filepath='c:/Temp2/compp/control_flow.ttl'):
    'Note: set PREFETCH_QUESTIONS = False'
    g = rdflib.Graph().parse(rdf_src_filepath)

    print(len(g), 'triples in src graph.')

    batch_size = 400
    _upload_graph(g, rdflib.URIRef(qG_URI).n3(), batch_size)
    print('triples insertion completed.')


def _upload_graph(g, ng_uri, batch_size=-1, verbose=True):
    batch = []
    i = 0

    for t in g:
        batch.append(tuple(
            ### ??? (for Parliament) ###

            node.n3() for node in t
        ))

        if batch_size > 0 and len(batch) >= batch_size:
            _insert_triples(batch, ng_uri)
            batch.clear()
            i += batch_size
            if verbose: print(i, 'triples inserted')

    if batch:
        _insert_triples(batch, ng_uri)
        i += len(batch)
        batch.clear()
        if verbose: print(i, 'triples inserted.')


def measure_disk_usage_uploading_named_graphs(target_role=GraphRole.QUESTION_TEMPLATE, skip=0):
    'Note: set PREFETCH_QUESTIONS = True'
    target_role_uriref = rdflib.URIRef(questionSubgraphPropertyFor(target_role))

    target_model_paths = []

    print("searching for named graphs for", target_role.prefix, "...")

    if qG:
        for targetGraphUri in qG.objects(None, target_role_uriref):
            if targetGraphUri != RDF.nil:

                qsgName = str(targetGraphUri)
                target_model_paths.append(
                    (qsgName, NS_file.localize(qsgName))
                )
            else:
                print('... not a graph!')

    print(len(target_model_paths), "target named graphs found.")
    target_model_paths = list(set(target_model_paths))
    print(len(target_model_paths), "unique graphs.")

    if skip > 0:
        target_model_paths = target_model_paths[skip:]
    print(len(target_model_paths), "graphs to send.")

    for i, (qgUri, path) in enumerate(target_model_paths):
        g = fileService.fetchModel(path)
        # ###
        # # set constant NG (for Parliament)
        # qgUri = str(rdflib.URIRef(qG_URI))
        # ###
        _upload_graph(g, ng_uri=URI(qgUri), batch_size=0)
        print('graph #%d uploaded:' % (i + 1), path)


def automatic_pipeline(batch=700, offset=0):
    if load_templates(limit=batch) > 20:  # note 14 errors
        return

    # obsolete, TODO: remove func
    # if update_template_concepts(limit=batch) > 0:
    #     return

    if solve_templates(limit=None) > 0:
        return

    if generate_questions_for_templates(limit=batch) > 0:
        return

    # obsolete, TODO: remove func
    # if update_questions_trace_concepts(limit=700) > 0:
    #     return
    # obsolete, TODO: remove func
    # if update_questions_trace_features(limit=6000) > 0:
    #     return

    # if generate_data_for_questions(offset=offset, limit=300) > 0:
    #     return

    print('everything is done!')
    print('Just waiting...')
    from time import sleep
    sleep(30 * 60)
    exit()


if __name__ == '__main__':
    print('Initializing...')

    automatic_pipeline()
    # automatic_pipeline(5)
    # automatic_pipeline(300, offset=0)

    # add_concepts_from_list()
    # make_questions_sample(size=200)
    # archive_required_files()
    # just_rdfdb_monitoring()

    # measure_disk_usage_uploading_questions()
    # measure_disk_usage_uploading_named_graphs()
    # measure_disk_usage_uploading_named_graphs(target_role=GraphRole.QUESTION_TEMPLATE_SOLVED)
    # measure_disk_usage_uploading_named_graphs(target_role=GraphRole.QUESTION, skip=0)
    # measure_disk_usage_uploading_questions('c:/D/Work/YDev/CompPr/3stores/bench/bsbmtools-0.2/pc2815-1M.ttl')
    print('Bye.')

'''

20.11.2022
----------
Searching for templates completed.
Used 17073 files of 25604 in the directory.

1.8 Мб - размер файла sqlite.
7.0 Мб - размер файла sqlite после создания всей базы на 17+тыс. шаблонов + 23+тыс. вопросов.

'''
