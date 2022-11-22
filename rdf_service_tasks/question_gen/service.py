# service.py

'''
    Entry point (main module) for question-creation service, a part of CompPrehension project.
    @ 2022
'''

import json
from math import exp
import math
import re
import sys

import fs
import rdflib
from rdflib import Graph, RDF
import yaml

from analyze_alg import generate_questions_for_algorithm, set_interrupt_flag
from chain_utils import builder
from GraphRole import GraphRole
from NamespaceUtil import NamespaceUtil
from ns4guestions import *
from rdflib_utils import graph_lookup, uploadGraph
from RemoteFileService import RemoteFileService
from sparql_wrapper import Sparql
from analyze_alg import jsObj

import sqlite_questions_metadata as dbmeta
sys.path.insert(1, '../../../c_owl/')
if 0:
    # just for debugger to see the code in different directory
    from ....c_owl.ctrlstrct_test import make_question_dict_for_alg_json
from ctrlstrct_test import make_question_dict_for_alg_json
### inspecting loading of qG
from common_helpers import Checkpointer


# using patched version of SPARQLBurger
from SPARQLBurger.SPARQLQueryBuilder import *

print('imports completed.')

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

qG = None  # guestions graph (pre-fetched)
fileService = None
sparql_endpoint = None


def read_access_config(file_path='./access_urls.yml'):
    try:
        # read config
        with open(file_path) as f:
            data = yaml.load(f, yaml.Loader)
    except OSError as e:
        print("Error: cannot read configuration from", file_path)
        print(e)
        exit(1)

    global CONFIG
    global fuseki_host
    global rdf_db_name
    global FTP_BASE
    global FTP_DOWNLOAD_BASE
    CONFIG = jsObj(data)
    fuseki_host = data["fuseki_host"]
    rdf_db_name = data["rdf_db_name"]
    FTP_BASE = data["ftp_base"]
    FTP_DOWNLOAD_BASE = data["ftp_download_base"]


def _get_rdfdb_stats_collectors():
    'init StateWatcher to watch dataset size on disk as well as number of triples in th dataset.'

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
            query_results = sparql_endpoint.query("select (count(*) as ?count) {graph ?g {?s ?p ?o}} ", return_format="json")
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


if INIT_GLOBALS:
    read_access_config()
    fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
    sparql_endpoint = Sparql(
        fuseki_host, rdf_db_name,
        query_url=CONFIG.query_url,
        update_url=CONFIG.update_url,
        credentials=CONFIG.get('credentials'),
        post_update_hooks=_get_rdfdb_stats_collectors()
    )

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

    return(update_query.get_text())

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


def unsolvedQuestions(unsolvedSubgraph:GraphRole) -> list:
    'get names of questions with `rdf:nil` set for specified graph'
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
    'get names of question templates without questions'
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

# q_graph = fetchGraph(qG_URI)
if INIT_GLOBALS and PREFETCH_QUESTIONS and not qG:
    ### empty graph:
    # qG = Graph().parse(format='n3', data='@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n[] a rdf:Class .')
    # pre-download whole questions graph
    print('Pre-download whole questions graph ...')
    if False:
        pass;  # qUri = qG_URI
    else:
        ## qUri = 'http://vstu.ru/poas/questions_only'
        # qUri = 'http://vstu.ru/poas/selected_questions'
        # ! qG_URI !
        print('Fetching graph as specified:', qG_URI)
    qG = fetchGraph(qG_URI, verbose=True)

    if DUMP_QUESTION_GRAPH_TO_FILE:
        ###
        # dump_qG_to = CONFIG.ftp_base + CONFIG.rdf_db_name + '.ttl'
        dump_qG_to = CONFIG.ftp_base + '../' + CONFIG.rdf_db_name + '.ttl'

        if REMOVE_TRIPLES_FOR_PRODUCTION:
            # just remove unused properties (has_graph_*) from question nodes
            # before exporting to production env
            nsQ = 'http://vstu.ru/poas/questions/'
            prop_names = '''
            has_graph_q_s
            has_graph_q
            has_graph_qt
            has_graph_qt_s'''.split()

            i = 0
            for pn in prop_names:
                p = rdflib.URIRef(pn, nsQ)
                for s, o in qG.subject_objects(p):
                    qG.remove((s, p, o))
                    i += 1
            print("Removed %d triples from graph (for production)." % i)

        # shorten length of serialized data
        qG.bind('Q', 'http://vstu.ru/poas/questions/Question#')
        qG.bind('QT', 'http://vstu.ru/poas/questions/QuestionTemplate#')
        qG.bind('qs', 'http://vstu.ru/poas/questions/')
        qG.serialize(dump_qG_to, format='turtle')
        print(len(qG), f"triples saved to file: {dump_qG_to}")
        print('Bye for now!')
        exit()


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


def nameForQuestionGraph(questionName, role:GraphRole, questions_graph=qG, file_ext=".ttl", fileService=fileService):
        # look for <Question>-<subgraph> relation in metadata first
        qG = questions_graph or fetchGraph(qG_URI);
        targetGraphUri = None

        if qG:
            qNode = findQuestionByName(questionName)
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


def getSubpathForQuestionGraph(name, role:GraphRole, file_ext=".ttl", fileService=fileService):
    file_path = GraphRole.QUESTION_TEMPLATE.ns().get(name)
    if not file_path.endswith(file_ext):
        file_path += file_ext
    return fileService.prepareNameForFile(file_path);



def getQuestionSubgraph(questionName, role, fileService=fileService):
    return fileService.fetchModel(nameForQuestionGraph(questionName, role));

def setQuestionSubgraph(questionName, role, model: Graph, questionNode=None, subgraph_name=None, fileService=fileService):
    qgUri = subgraph_name or nameForQuestionGraph(questionName, role)
    if model:
        fileService.sendModel(qgUri, model);
    # update questions metadata
    questionNode = questionNode or findQuestionByName(questionName)
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


def setQuestionSubgraphDB(row_instance, role, model: Graph, subgraph_path=None, fileService=fileService):
    # qgUri = subgraph_name or nameForQuestionGraph(questionName, role)
    file_subpath = subgraph_path or getSubpathForQuestionGraph(row_instance.name, role)
    db_field_name = tableFieldForRoleDB(role)

    if model:
        fileService.sendModel(file_subpath, model);

    # update question's metadata
    setattr(row_instance, db_field_name, file_subpath)

    if model:
        # copy has_concept relations to metadata graph (into questions/ NS) ...
        has_concept = rdflib.URIRef(NS_code.get("has_concept"))

        concepts = extract_graph_values(model, subject=None, predicate=has_concept)

        dbmeta.update_bit_field(row_instance, 'concept_bits', dbmeta.names_to_bitmask(concepts, entity=dbmeta.Concepts))


    row_instance._stage = dbmeta.STAGE_QT_CREATED
    row_instance._version = dbmeta.TOOL_VERSION
    row_instance.save()


def extract_graph_values(model: Graph, subject: rdflib.URIRef=None, predicate: rdflib.URIRef=None):
    objs = model.objects(subject, predicate)
    return [o.toPython() for o in objs]



def getQuestionModel(questionName, topRole=GraphRole.QUESTION_SOLVED, fileService=fileService):
    if topRole.ordinal() >= GraphRole.QUESTION.ordinal() and (pos := questionName.rfind('_v')) > 0:
        # cut values added to template name
        qt_name = questionName[:pos]
    else:
        qt_name = questionName

    m = Graph();
    for role in questionStages():
        if role.ordinal() >= GraphRole.QUESTION.ordinal():
            graph_name = questionName
        else:
            graph_name = qt_name
        gm = getQuestionSubgraph(graph_name, role, fileService=fileService);
        if gm:
            m += gm;
        if (role == topRole): break;
    return m

__PATCH_TTL_RE = None

def _patch_and_parse_ttl(opened_file):
    global __PATCH_TTL_RE
    if not __PATCH_TTL_RE:
        __PATCH_TTL_RE = re.compile(r'((?<=:return)|(?<=:break)|(?<=:continue))(\s+:stmt)')

    data = opened_file.read()
    data = __PATCH_TTL_RE.sub(lambda m: m[1] + ',' + m[2], data)  # insert ,
    g = Graph().parse(format='ttl', data=data.encode())
    return g


def load_templates(limit=None) -> int:
    ''' rdf metadata: ! Set INIT_GLOBALS and PREFETCH_QUESTIONS to True !
    '''

    # templates_total = 0
    done_count = 0

    qt_list = dbmeta.findTemplatesOnStageDB(dbmeta.STAGE_QT_FOUND, limit)
    if not qt_list:
        return 0

    from full_questions import repair_statements_in_graph

    ch = Checkpointer()

    for qt in qt_list:

        path = CONFIG.src_ttl_dir + (qt.src_path)
        with open(path) as f:
            m = _patch_and_parse_ttl(f)

        try:
            m = repair_statements_in_graph(m)
        except AssertionError:
            print(f'error with "{qt.name}"')
            # raise

        file_subpath = setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE, m)
        done_count += 1
        if done_count % 20 == 0:
	        ch.hit(        '   + 20 templates created')
	        ch.since_start('[%3d] time elapsed so far:' % done_count)

    ch.since_start("Loading templates completed, in")
    print("Loaded", done_count, 'templates of', len(qt_list), 'currently selected.')
    return len(qt_list)


def find_templates(rdf_dir, wanted_ext=".ttl", file_size_filter=(3*1024, 40*1024), skip_first=0):
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

            if file_size_filter and not(file_size_filter[0] <= info.size <= file_size_filter[1]):
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
        self.i = 0 # state for next()
    def get(self, index):
        if index < self.delay or index >= (self.delay + self.active):
            return self.safe_value
        else:
            return not self.safe_value

    # def __iter__(self): return self
    def __next__(self):
        self.i += 1
        return self.get(self.i - 1)
    def __getitem__(self, index): return self.get(index)


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
            triples.append(( qNode.n3(), URI(NS_questions.get(name)), rdflib.Literal(v).n3() ))

    if triples:
        commands.append(makeInsertTriplesQuery(ngNode.n3(), triples, )) ## PREFIXES
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


CONCEPT_CANDIDATES = "expr alternative if else-if else loop while_loop do_while_loop for_loop foreach_loop sequence return break continue".split()

def question_metrics(g, gl, question_dict, quiet=False):
    data = {}

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
    max_if_branches_count = max([next(iter(b.values())).toPython() if b else 0  for b in r.bindings])
    data['max_if_branches'] = max_if_branches_count


    ppath = ((gl(':body') | gl(':branches_item')) * '?' / gl(':body_item'))  ##  * '+'

    # nesting_depth
    def action_depth(s):
        children = g.objects(s, ppath)
        return 1 + max([0, *map(action_depth, children)])

    root = [*g.objects(None, gl(':global_code'))][0]
    max_depth = action_depth(root) - 1
    data['nesting_depth'] = max_depth


    # find max loop nesting depth by counting parent loops looking up from bottom
    query = 'SELECT ?s where {?s a :loop}'
    r = g.query(query, initNs=PREFIXES)
    loops = [next(iter(b.values())) for b in r.bindings]
    if not loops:
        data['max_loop_nesting_depth'] = 0
    else:
        # find reverse nesting: how many loops a loop is nested in?
        in_loop__ppath = ~ppath * '+'
        nest_depths = [
            sum((L, in_loop__ppath, L2) in g  for L2 in loops if L2 is not L)
            for L in loops
        ]
        data['max_loop_nesting_depth'] = max(nest_depths) + 1


    #### cyclomatic = len(question_dict['name_suffix']) + 1  # Bad way as values count is NOT condtion count.
    values_count_plus_1 = len(question_dict['name_suffix']) + 1  # Bad way as values count is NOT condtion count.

    tags = ["C++", "trace"]

    concepts = []
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
    if not quiet: print('    Question complexity: %d  --> integral_complexity: %5f' % (complexity, integral))

    return dict(
        solution_structural_complexity = round(complexity),
        solution_steps = question_dict['length'],
        distinct_errors_count = len(question_dict['possible_violations']),
        integral_complexity = round(integral, 4),  # 5 digits precision
        has_tag = tuple(tags),
        has_concept = tuple(sorted(concepts)),
        has_law = tuple(sorted(question_dict['laws'])),
        has_violation = tuple(sorted(question_dict['possible_violations'])),
        **data
    )

import threading
import time
CREATE_TRACES_TIMEOUT = 15  # seconds


def process_template(qtname, questions_count=0):
    g = getQuestionModel(qtname, GraphRole.QUESTION_TEMPLATE_SOLVED)
    gl = graph_lookup(g, PREFIXES)

    # old code: just call it
    # questions = generate_questions_for_algorithm(g, gl)

    # new code: kill process on timeout
    questions = None ## ()  # nothing by default

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

    print("Total questions generated: ", questions and len(questions))

    if not questions:
        return 0

    for question in questions:
        print()
        suffix = question['name_suffix'] or ('_nocond_q%d' % questions_count)
        question_name = '%s_v%s' % (qtname, suffix)
        file_path = nameForQuestionGraph(question_name, GraphRole.QUESTION)
        assert file_path, question_name
        print("  Saving question: ", question_name, ' --> ', file_path)
        ### continue

        #### gUri = NS_file.get(GraphRole.QUESTION.ns().get(file_path))
        gUri = NS_file.get(file_path)
        model = question['rdf']
        print("    Uploading model ...")  # "for question '%s' ... " % question_name)
        # uploadGraph(gUri, model, fuseki_update)
        for _i in range(3):
            try:
                if _i > 0: print("       [NETWORK] Retry uploading model: take %d" % _i)
                fileService.sendModel(file_path, model);
                break
            except:
                continue

        qUri = createQuestion(question_name, qtname, gUri, question_metrics(g, gl, question))
        print("  Question URI:", qUri)

    return len(questions)



def generate_questions_for_templates(offset=None, limit=None):

    print("Requesting templates without questions ...", flush=True)
    if limit:
        sparql_limit = limit
        limit = None
    else:
        sparql_limit = None
    templates_to_create_questions = templatesWithoutQuestions(sparql_limit)

    ### debugging: get existing questions instead
    # templates_to_create_questions = list({n[:n.rfind("_v")] for n in unsolvedQuestions(GraphRole.QUESTION_SOLVED)})


    print('Templates without questions found: %d' % len(templates_to_create_questions))
    ### return

    # print(*templates_to_create_questions, sep='\n')
    # exit()

    questions_count = 0
    skip_count = 0

    # def process_one(qtname):
    #     nonlocal questions_count
    #     nonlocal skip_count
    #     try:
    #         questions_count += process_template(qtname, questions_count)
    #     except NotImplementedError as e:
    #         skip_count += 1
    #         print()
    #         print('Error with template: ', qtname)
    #         print(e)


    for qtname in templates_to_create_questions[offset:limit]:

        print()
        print()
        print("Processing template: ", qtname)
        print("    (skipped so far: %d)" % skip_count)
        print("========")
        if qtname in ('curl_mvsnprintf', ):
            print('intended skip.')
            continue
        try:
            questions_count += process_template(qtname, questions_count)
        except NotImplementedError as e:
            skip_count += 1
            print()
            print('Error with template: ', qtname)
            print(e)
            print()


    print()
    print(questions_count, 'questions created.')
    print('done.')


def process_question(qname):
    ''' generating data for question '''
    g = getQuestionModel(qname, GraphRole.QUESTION)
    # gl = graph_lookup(g, PREFIXES)

    from full_questions import convert_graph_to_json

    alg_json = convert_graph_to_json(g)

    try:
        q_dict = make_question_dict_for_alg_json(alg_json, qname)

        fullname = nameForQuestionGraph(qname, GraphRole.QUESTION_DATA, file_ext=".json")

        print('    Uploading json file ...')
        fileService.sendFile(fullname,
            # json.dumps(q_dict, ensure_ascii=False).encode()
            json.dumps(q_dict, ensure_ascii=False, indent=2).encode()
        )

        ### dump alg_json to debug
        # fileService.sendFile(fullname[:-4] + 'src.json',
        #     # json.dumps(q_dict, ensure_ascii=False).encode()
        #     json.dumps(alg_json, ensure_ascii=False, indent=2).encode()
        # )

        setQuestionSubgraph(qname, GraphRole.QUESTION_DATA, model=None, subgraph_name=fullname)
    except Exception as e:
        print("exception in process_question:")
        print(e)
        print()


def generate_data_for_questions(offset=None, limit=None):

    print("Requesting questions without data ...", flush=True)

    questions_to_process = unsolvedQuestions(GraphRole.QUESTION_DATA)

    ### debugging: get all existing questions instead
    # questions_to_process = unsolvedQuestions(GraphRole.QUESTION_SOLVED)


    print('Questions without data found: %d' % len(questions_to_process))

    questions_count = 0
    skip_count = 0

    for qname in questions_to_process[offset:limit]:

        print()
        print()
        print("Processing question: ", qname, "(i: %d)" % questions_count)
        print("    (with errors so far: %d)" % skip_count)
        print("========")
        try:
            process_question(qname)
            questions_count += 1
        except NotImplementedError as e:
            skip_count += 1
            print()
            print('Error with question: ', qname)
            print(e)
            print()

    print()
    print(questions_count, 'questions updated with data.')
    print('done.')



def make_questions__main():
    if 1:
        generate_questions_for_templates(0, None) # 30
        exit(0)
    else:
        # qtname = 'packet_queue_get'
        qtname = 'SDL_CondWaitTimeout'
        print("========", flush=True)
        questions_count = process_template(qtname)
        print()
        print(questions_count, 'questions created for template.')


    '''
    Templates without questions found: 24  (of 1 315)
    [Finished in 39.5s]
    '''


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

    if not sparql_endpoint:
        read_access_config()
        _sparql_endpoint = Sparql(fuseki_host, rdf_db_name, )
    else:
        _sparql_endpoint = sparql_endpoint

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

def make_questions_sample(src_graph='http://vstu.ru/poas/questions', dest_graph='http://vstu.ru/poas/selected_questions', size=100, bins=20):
    ''' Copy a sample of questions with templates from src named graph to dest named graph keeping all the range of available complexity '''
    import random

    if not INIT_GLOBALS:
    # if not sparql_endpoint:
        read_access_config()
        #### fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
        sparql_endpoint = Sparql(fuseki_host, rdf_db_name, )

    # select all values from src_graph first
    select_all_questions = '''SELECT ?q ?complexity
    where { GRAPH <%s> {
        ?q a <http://vstu.ru/poas/questions/Question> .
        ?q <http://vstu.ru/poas/questions/integral_complexity> ?complexity.
    }}''' % src_graph

    query_results = sparql_endpoint.query(select_all_questions, return_format="json")
    cplx_qs = [(float(b['complexity']['value']), b['q']['value'] )
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


def archive_required_files(src_graph='http://vstu.ru/poas/selected_questions', target_zip='./selected_questions-files.zip'):
    import fs
    import fs.copy
    from fs import open_fs
    from fs.zipfs import WriteZipFS
    import zipfile

    if not INIT_GLOBALS:
    # if not sparql_endpoint:
        read_access_config()
        # fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
        sparql_endpoint = Sparql(fuseki_host, rdf_db_name, )

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


def automatic_pipeline(batch=300):
    if load_templates(limit=None) > 0:
        return

    # if solve_templates(limit=batch) > 0:
    #   return


    print('everything is done!')
    print('Just waiting...')
    from time import sleep
    sleep(30*60)
    exit()


if __name__ == '__main__':
    print('Initializing...')
    # upload_templates(r'c:/Temp2/cf_v8-pre')
    # upload_templates(r'c:/Temp2/cf_v8')
    # upload_templates(r'c:/Temp2/cf_v9-expr-concepts/__result', skip_first=5200)

    # find_templates(r'c:/Temp2/cf_v9-expr-concepts/__result', skip_first=0)
    # find_templates(CONFIG.src_ttl_dir, skip_first=0)

    automatic_pipeline()


    # make_questions__main()

    # generate_data_for_questions(0, None)


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
