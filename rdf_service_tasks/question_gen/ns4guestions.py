# ns4guestions.py

# from rdflib import Graph, RDF

from NamespaceUtil import NamespaceUtil

NS_root = NamespaceUtil("http://vstu.ru/poas/");
NS_code = NamespaceUtil(NS_root.get("code#"));
#### NS_namedGraph = NamespaceUtil("http://named.graph/");
NS_file = NamespaceUtil("ftp://plain.file/");
NS_graphs = NamespaceUtil(NS_root.get("graphs/"));
NS_questions = NamespaceUtil(NS_root.get("questions/"));
NS_oop = NamespaceUtil(NS_root.get("oop/"));

NS_classQuestionTemplate = NamespaceUtil(NS_questions.get('QuestionTemplate#'));
NS_classQuestion = NamespaceUtil(NS_questions.get('Question#'));



PREFIXES = dict(
rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
rdfs= "http://www.w3.org/2000/01/rdf-schema#",
owl = "http://www.w3.org/2002/07/owl#",
)
PREFIXES[''] = NS_code.get()

