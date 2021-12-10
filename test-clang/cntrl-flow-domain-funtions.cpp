#include "cntrl-flow-domain-funtions.h"


ControlFlowDomainExprStmtNode* mapToControlflowDst(Expr* expr)
{
	if (expr == nullptr)
		return nullptr;

	return new ControlFlowDomainExprStmtNode(expr);
}

ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl)
{
	if (funcDecl == nullptr)
		return nullptr;

	auto body = mapToControlflowDst(funcDecl->getBody());
	return new ControlFlowDomainFuncDeclNode(funcDecl, body);
}

ControlFlowDomainStmtNode* mapToControlflowDst(Stmt* stmt)
{
	if (stmt == nullptr)
		return nullptr;

	if (auto compoundStmt = dyn_cast<clang::CompoundStmt>(stmt))
	{
		vector<ControlFlowDomainStmtNode*> childs;
		for (auto stmt : compoundStmt->body())
		{
			childs.push_back(mapToControlflowDst(stmt));
		}
		return new ControlFlowDomainStmtListNode(compoundStmt, childs);
	}		
	if (auto declStmt = dyn_cast<clang::DeclStmt>(stmt))
	{
		bool isAllVarDecl = true;
		for (auto childDecl : declStmt->getDeclGroup())
		{
			isAllVarDecl = isAllVarDecl && isa<clang::VarDecl>(childDecl);
		}
		if (isAllVarDecl)
			return new ControlFlowDomainVarDeclStmtNode(declStmt);
	}
	if (auto ifStmt = dyn_cast<clang::IfStmt>(stmt))
	{
		auto expr = mapToControlflowDst(ifStmt->getCond());
		auto then = mapToControlflowDst(ifStmt->getThen());
		auto _else = mapToControlflowDst(ifStmt->getElse());
		return new ControlFlowDomainIfStmtNode(ifStmt, expr, then, _else);
	}
	if (auto whileStmt = dyn_cast<clang::WhileStmt>(stmt))
	{
		auto expr = mapToControlflowDst(whileStmt->getCond());
		auto body = mapToControlflowDst(whileStmt->getBody());
		return new ControlFlowDomainWhileStmtNode(whileStmt, expr, body);
	}
	if (auto doStmt = dyn_cast<clang::DoStmt>(stmt))
	{
		auto expr = mapToControlflowDst(doStmt->getCond());
		auto body = mapToControlflowDst(doStmt->getBody());
		return new ControlFlowDomainDoWhileStmtNode(doStmt, expr, body);
	}
	if (auto returnStmt = dyn_cast<clang::ReturnStmt>(stmt))
	{
		auto expr = mapToControlflowDst(returnStmt->getRetValue());
		return new ControlFlowDomainReturnStmtNode(returnStmt, expr);
	}
	if (auto exprStmt = dyn_cast<clang::Expr>(stmt))
	{
		return mapToControlflowDst(exprStmt);
	}

	return new ControlFlowDomainUndefinedStmtNode(stmt);
}

std::string toOriginalCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr)
{
	return get_source_text_raw(func->getAstNode()->getSourceRange(), mgr);
}


std::string toCustomCppString(ControlFlowDomainFuncDeclNode* func)
{
	return "";
}