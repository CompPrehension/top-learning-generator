#pragma once
#include "ControlFlowDomainNodes.h"
#include "helpers.h"

ControlFlowDomainStmtNode* mapToControlflowDst(Stmt* stmt);
ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl);

std::string toOriginalCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr);
std::string toCustomCppString(ControlFlowDomainFuncDeclNode* func);