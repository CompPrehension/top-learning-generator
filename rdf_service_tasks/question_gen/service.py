# service.py

'''
    Entry point (main module) for question-creation service, a part of CompPrehension project.
    @ 2022
'''

import json
from math import exp

import pyfuseki
from pyfuseki import FusekiUpdate, FusekiQuery
import rdflib
from rdflib import Graph, RDF
import yaml

from analyze_alg import generate_questions_for_algorithm
from chain_utils import builder
from GraphRole import GraphRole
from NamespaceUtil import NamespaceUtil
from ns4guestions import *
from rdflib_utils import graph_lookup, uploadGraph
from RemoteFileService import RemoteFileService


# using patched version of SPARQLBurger
from SPARQLBurger.SPARQLQueryBuilder import *


# Global variables
INIT_GLOBALS = True
qG = None  # guestions graph (pre-fetched)
fileService = None
fuseki_update = None
fuseki_query = None


def read_access_config(file_path='./access_urls.yml'):
    try:
        # read config
        with open(file_path) as f:
            data = yaml.load(f, yaml.Loader)
    except OSError as e:
        print("Error: cannot read configuration from", file_path)
        print(e)
        exit(1)

    global fuseki_host
    global fuseki_db_name
    global FTP_BASE
    global FTP_DOWNLOAD_BASE
    fuseki_host = data["fuseki_host"]
    fuseki_db_name = data["fuseki_db_name"]
    FTP_BASE = data["ftp_base"]
    FTP_DOWNLOAD_BASE = data["ftp_download_base"]


if INIT_GLOBALS:
    read_access_config()
    fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
    fuseki_update = FusekiUpdate(fuseki_host, fuseki_db_name)
    fuseki_query  = FusekiQuery (fuseki_host, fuseki_db_name)

    # qG = fetchGraph(NS_questions.base())



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


def unsolvedQuestions(unsolvedSubgraph:GraphRole) -> list:
    'get names of questions with `rdf:nil` set for specified graph'
    ng = URI(NS_questions.base());

    unsolvedTemplates = builder(SPARQLSelectQuery()
    ).add_prefix(
        Prefix('rdf', RDF.uri)
    ).add_variables(
        ["?name"]
    ).set_where_pattern(
        builder(SPARQLGraphPattern(graph_name=ng)
        ).add_triples([
            Triple("?node", URI(NS_questions.get("name")), "?name"),
            Triple("?node", URI(questionSubgraphPropertyFor(unsolvedSubgraph)), 'rdf:nil'),
        ]).builder
    ).get_text().result

    query_result = fuseki_query.run_sparql(unsolvedTemplates, return_format="json")
    query_results = json.loads(b''.join(list(query_result)))
    # {'head': {'vars': ['name']},
    #  'results': {'bindings': [
    #    {'name': {'type': 'literal', 'value': '1__memcpy_s'}},
    #    {'name': {'type': 'literal', 'value': '5__strnlen_s'}}]}}
    names = [b['name']['value'] for b in query_results['results']['bindings']]
    # del query_result; del query_results
    return names

# unsolved_qs = unsolvedQuestions(GraphRole.QUESTION_SOLVED)



def templatesWithoutQuestions() -> list:
    'get names of question templates without questions'
    ng = URI(NS_questions.base());

    lonelyTemplates = builder(SPARQLSelectQuery()
    ).add_prefix(
        Prefix('rdf', RDF.uri)
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

    query_result = fuseki_query.run_sparql(lonelyTemplates, return_format="json")
    query_results = json.loads(b''.join(list(query_result)))
    # {'head': {'vars': ['name']},
    #  'results': {'bindings': [
    #    {'name': {'type': 'literal', 'value': '1__memcpy_s'}},
    #    {'name': {'type': 'literal', 'value': '5__strnlen_s'}}]}}
    names = [b['name']['value'] for b in query_results['results']['bindings']]
    # del query_result; del query_results
    return names

# templates_to_create_questions = templatesWithoutQuestions()


CONSTRUCT_PATTERN = '''CONSTRUCT {
   ?s ?p ?o .
}
WHERE { GRAPH <%s> {
   ?s ?p ?o .
} }
'''

def fetchGraph(gUri: str):
    prefixes = '\n'.join((
        f"PREFIX qs: <{NS_questions.get()}>",
    ))
    q = CONSTRUCT_PATTERN % gUri
    query_result = fuseki_query.run_sparql(q, return_format="turtle")
    query_results = b''.join(list(query_result))
    g = Graph().parse(format='n3', data=query_results)
    return g

# q_graph = fetchGraph(NS_questions.base())
if INIT_GLOBALS:
    qG = fetchGraph(NS_questions.base())



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


def findQuestionByName(questionName, questions_graph=qG, fileService=fileService):
        qG = questions_graph or fileService.getGraph(NS_questions.base());
        if qG:
            qNode = qG.value(None, rdflib.term.URIRef(NS_questions.get("name")), rdflib.term.Literal(questionName))
            if qNode:
                return qNode

        print("    (No question found for name: %s)" % questionName)
        return None;


def nameForQuestionGraph(questionName, role:GraphRole, questions_graph=qG, fileService=fileService):
        # look for <Question>-<subgraph> relation in metadata first
        qG = questions_graph or fileService.getGraph(NS_questions.base());
        targetGraphUri = None

        if qG:
            qNode = findQuestionByName(questionName)
            if qNode:
                targetGraphUri = qG.value(
                    qNode,
                    rdflib.term.URIRef(questionSubgraphPropertyFor(role)),
                    None)
                if targetGraphUri == RDF.nil:
                    targetGraphUri = None

        if targetGraphUri:
            qsgName = str(targetGraphUri)
            return NS_file.localize(qsgName);

        # no known relation - get default for a new one
        print("    (No question graph found for Role '%s' and name: %s)" % (role.prefix, questionName))
        ext = ".ttl"
        return fileService.prepareNameForFile(role.ns().get(questionName + ext), False);




def getQuestionSubgraph(questionName, role, fileService=fileService):
    return fileService.fetchModel(nameForQuestionGraph(questionName, role));

def getQuestionModel(questionName, topRole=GraphRole.QUESTION_SOLVED, fileService=fileService):
    m = Graph();
    for role in questionStages():
        gm = getQuestionSubgraph(questionName, role, fileService=fileService);
        if gm:
            m += gm;
        if (role == topRole): break;
    return m


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
        qG = fetchGraph(NS_questions.base());  # questions Graph containing questions metadata
    if qG is None:
        return None

    nodeClass = rdflib.term.URIRef(NS_classQuestion.base());

    # (skip checking for duplicates)

    qtemplNode = qG.value(None, rdflib.term.URIRef(NS_questions.get("name")), rdflib.term.Literal(questionTemplateName));

    assert qtemplNode, '     (No template found for name: "%s")' % questionTemplateName

    ngNode = rdflib.term.URIRef(NS_questions.base());

    # create in Question# namespace !
    qNode = rdflib.term.URIRef(NS_classQuestion.get(questionName));

    commands = [];

    commands.append(makeUpdateTripleQuery(ngNode.n3(), qNode.n3(), RDF.type.n3(), nodeClass.n3()));

    commands.append(makeUpdateTripleQuery(ngNode.n3(),
            qNode.n3(),
            rdflib.term.URIRef(NS_questions.get("name")).n3(),
            rdflib.term.Literal(questionName).n3()));

    commands.append(makeUpdateTripleQuery(ngNode.n3(),
            qNode.n3(),
            rdflib.term.URIRef(NS_questions.get("has_template")).n3(),
            qtemplNode.n3()));

    # copy references to the graphs from template as is ...
    # using "template-only" roles
    for role in (GraphRole.QUESTION_TEMPLATE, GraphRole.QUESTION_TEMPLATE_SOLVED):
        propOfRole = rdflib.term.URIRef(questionSubgraphPropertyFor(role));
        graphWithRole = qG.value(qtemplNode, propOfRole, None);
        commands.append(makeUpdateTripleQuery(ngNode.n3(), qNode.n3(), propOfRole.n3(), graphWithRole.n3()));

    # initialize question's graphs as empty ...
    # using "question-only" roles
    for role in (GraphRole.QUESTION, GraphRole.QUESTION_SOLVED):
        obj = RDF.nil
        if role == GraphRole.QUESTION and questionDataGraphUri:
            obj = rdflib.term.URIRef(questionDataGraphUri)
        commands.append(makeUpdateTripleQuery(ngNode.n3(),
                qNode.n3(),
                rdflib.term.URIRef(questionSubgraphPropertyFor(role)).n3(),
                obj.n3()));


    # > add other metadata
    triples = []
    for name, vals in metrics.items():
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        for v in vals:
            triples.append(( qNode.n3(), URI(NS_questions.get(name)), rdflib.term.Literal(v).n3() ))

    if triples:
        commands.append(makeInsertTriplesQuery(ngNode.n3(), triples, )) ## PREFIXES
    # < add other metadata


    # runQueries(commands);

    full_query = '\n;\n'.join(commands)

    ### print(full_query); exit()

    res = fuseki_update.run_sparql(full_query)
    print('      SPARQL: create question response code:', res.response.code)

    # do not update as quad insertion is not for a single graph
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


TAG_CANDIDATES = "expr alternative if else-if else loop while_loop do_while_loop for_loop foreach_loop".split()

def question_metrics(g, gl, question_dict, quiet=False):
    cyclomatic = len(question_dict['name_suffix']) + 1
    complexity = (question_dict['length'] * 0.1 + cyclomatic) * question_dict['depth'] ** 0.5
    x = (complexity - 25) / 10
    integral = sigmoid(x)
    if not quiet: print('    Question complexity: %d  --> integral_complexity: %5f' % (complexity, integral))

    tags = ["C++", "trace"]
    for tag in TAG_CANDIDATES:
        if (None, RDF.type, gl(':' + tag)) in g:
            tags.append(tag)
        # else:
        #     print("          [DEBUG] tag not found:", tag)

    return dict(
        solution_structural_complexity = round(complexity),
        solution_steps = question_dict['length'],
        distinct_errors_count = len(question_dict['possible_violations']),
        integral_complexity = round(integral, 4),  # 5 digits precision
        has_tag = tuple(tags),
        has_law = tuple(sorted(question_dict['laws'])),
        has_violation = tuple(sorted(question_dict['possible_violations'])),
    )


def generate_questions_for_templates(limit=None):

    templates_to_create_questions = templatesWithoutQuestions()

    ### debugging: get existing questions instead
    # templates_to_create_questions = list({n[:n.rfind("_v")] for n in unsolvedQuestions(GraphRole.QUESTION_SOLVED)})


    print('Templates without questions found: %d' % len(templates_to_create_questions))

    # print(*templates_to_create_questions, sep='\n')
    # exit()

    questions_count = 0

    for qtname in templates_to_create_questions[:limit]:

        print()
        print()
        print("Processing template: ", qtname)
        print("========")

        g = getQuestionModel(qtname, GraphRole.QUESTION_TEMPLATE_SOLVED)

        gl = graph_lookup(g, PREFIXES)

        questions = generate_questions_for_algorithm(g, gl)
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

        print("Total questions generated: ", len(questions))

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
            questions_count += 1


    print()
    print(questions_count, 'questions created.')
    print('done.')




if __name__ == '__main__':
    generate_questions_for_templates(30)