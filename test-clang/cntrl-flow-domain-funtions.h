#pragma once
#include <iostream>
#include <string>
#include <sstream>
#include "ControlFlowDomainNodes.h"
#include "ControlFlowDomainRdfNodes.h"
#include "helpers.h"

using namespace std;

ControlFlowDomainStmtNode* mapToControlflowDst(Stmt* stmt);
ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl);

std::string toOriginalCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr);
std::string toCustomCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr, bool isDebug = false);

ControlFlowDomainAlgorythmRdfNode* mapToRdfNode(string algUniqueName, ControlFlowDomainFuncDeclNode* node, clang::SourceManager& mgr);
