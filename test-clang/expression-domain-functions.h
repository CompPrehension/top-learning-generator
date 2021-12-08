#pragma once
#include "ExpressionDomainNodes.h"
#include "ExpressionDomainRdfNode.h"
#include <vector>
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

using namespace std;
using namespace clang;

/* Ensure node validity */
bool isValidNode(ExpressionDomainNode* node);
//void isValidNodeInner(ExpressionDomainNode* node, bool& _isValid, int& operatorsCount);

/* Map clang expr to dst */
ExpressionDomainNode* mapToDst(const clang::Expr* node, clang::SourceManager* sourceMgr);
//void mapToExressionDomainRdfNodes(ExpressionDomainNode* node, vector<ExpressionDomainRdfNode>& acc, int& index);

/* Map dst to rdf object model */
vector<ExpressionDomainRdfNode> mapToExressionDomainRdfNodes(ExpressionDomainNode* node);

/* Converts rdf object model to plain text */
string rdfTreeToString(string stingExpr, vector<ExpressionDomainRdfNode>& nodes);
