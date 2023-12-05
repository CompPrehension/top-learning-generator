#pragma once
#include <iostream>
#include <string>
#include <sstream>
#include "ControlFlowDomainNodes.h"
#include "ControlFlowDomainRdfNodes.h"
#include "helpers.h"
#include "Logger.h"

using namespace std;



ControlFlowDomainAlgo* mapToControlflowDst(FunctionDecl* funcDecl, ASTContext& astCtx, clang::SourceManager& mgr);
ControlFlowDomainExprStmtNode* mapExprToControlflowDst(Expr *expr, ASTContext& astCtx, clang::SourceManager &mgr, int funcDepth, ControlFlowDomainFuncDeclNodeSet& calledFunctions);
ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl, ASTContext& astCtx, clang::SourceManager &mgr, int funcDepth);
ControlFlowDomainStmtNode* mapToControlflowDst(Stmt *stmt, ASTContext &astCtx, clang::SourceManager &mgr, int funcDepth, ControlFlowDomainFuncDeclNodeSet& calledFunctions);

std::string toOriginalCppString(ControlFlowDomainAlgo* algo, clang::SourceManager& mgr);
std::string toCustomCppString(ControlFlowDomainAlgo* algo, clang::SourceManager& mgr, ASTContext& astCtx, bool isDebug = false);

ControlFlowDomainAlgorythmRdfNode* mapToRdfNode(string algUniqueName, ControlFlowDomainFuncDeclNode* node, clang::SourceManager& mgr, ASTContext& astCtx);
