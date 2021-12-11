#include "cntrl-flow-domain-funtions.h"


ControlFlowDomainExprStmtNode* mapExprToControlflowDst(Expr* expr)
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
		auto expr = mapExprToControlflowDst(ifStmt->getCond());
		auto then = mapToControlflowDst(ifStmt->getThen());
		auto _else = mapToControlflowDst(ifStmt->getElse());
		return new ControlFlowDomainIfStmtNode(ifStmt, expr, then, _else);
	}
	if (auto whileStmt = dyn_cast<clang::WhileStmt>(stmt))
	{
		auto expr = mapExprToControlflowDst(whileStmt->getCond());
		auto body = mapToControlflowDst(whileStmt->getBody());
		return new ControlFlowDomainWhileStmtNode(whileStmt, expr, body);
	}
	if (auto doStmt = dyn_cast<clang::DoStmt>(stmt))
	{
		auto expr = mapExprToControlflowDst(doStmt->getCond());
		auto body = mapToControlflowDst(doStmt->getBody());
		return new ControlFlowDomainDoWhileStmtNode(doStmt, expr, body);
	}
	if (auto returnStmt = dyn_cast<clang::ReturnStmt>(stmt))
	{
		auto expr = mapExprToControlflowDst(returnStmt->getRetValue());
		return new ControlFlowDomainReturnStmtNode(returnStmt, expr);
	}
	if (auto exprStmt = dyn_cast<clang::Expr>(stmt))
	{
		return mapExprToControlflowDst(exprStmt);
	}

	return new ControlFlowDomainUndefinedStmtNode(stmt);
}

std::string toOriginalCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr)
{
	return get_source_text(func->getAstNode()->getSourceRange(), mgr);
}


std::stringstream& printTabs(std::stringstream& ss, int level)
{
	ss << string(level * 4, ' ');
	return ss;
}


std::stringstream& printExpr(std::stringstream& ss, ControlFlowDomainExprStmtNode* expr, clang::SourceManager& mgr)
{
	if (expr == nullptr || expr->getAstNode() == nullptr)
		return ss;

	auto s = removeMultipleSpaces(removeNewLines(get_source_text(expr->getAstNode()->getSourceRange(), mgr)));
	if (s.length() == 0)
	{
		s = removeMultipleSpaces(removeNewLines(get_source_text_raw_tr(expr->getAstNode()->getSourceRange(), mgr)));
	}

	ss << s;
	return ss;
}


void toCustomCppStringInner(std::stringstream& ss, ControlFlowDomainStmtNode* stmt, clang::SourceManager& mgr, bool isDebug, int recursionLevel = 0, bool ignoreFirstLineSpaces = false)
{
	if (stmt == nullptr)
		return;


	if (auto node = dynamic_cast<ControlFlowDomainUndefinedStmtNode*>(stmt))
	{
		if (isDebug)
		{
			if (!ignoreFirstLineSpaces)
				printTabs(ss, recursionLevel);
			ss << "/* undefined stmt */" << "\n";
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainStmtListNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		ss << "{" << "\n";
		for (auto innerStmt : node->getChilds())
		{
			toCustomCppStringInner(ss, innerStmt, mgr, isDebug, recursionLevel + 1);
		}
		printTabs(ss, recursionLevel) << "}" << "\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainExprStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		printExpr(ss, node, mgr);
		ss << ";\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainIfStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		ss << "if (";
		printExpr(ss, node->getExpr(), mgr);
		ss << ")\n";
		toCustomCppStringInner(ss, node->getThenBody(), mgr, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getThenBody()) ? recursionLevel : recursionLevel + 1);
		if (node->getElseBody() && node->getElseBody()->getAstNode())
		{
			if (dynamic_cast<ControlFlowDomainIfStmtNode*>(node->getElseBody()))
			{
				printTabs(ss, recursionLevel) << "else ";
				toCustomCppStringInner(ss, node->getElseBody(), mgr, isDebug, recursionLevel, true);
			}
			else
			{
				printTabs(ss, recursionLevel) << "else\n";
				toCustomCppStringInner(ss, node->getElseBody(), mgr, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getElseBody()) ? recursionLevel : recursionLevel + 1);
			}
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainWhileStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		ss << "while (";
		printExpr(ss, node->getExpr(), mgr);
		ss << ")\n";
		toCustomCppStringInner(ss, node->getBody(), mgr, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getBody()) ? recursionLevel : recursionLevel + 1);
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainDoWhileStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		ss << "do\n";
		toCustomCppStringInner(ss, node->getBody(), mgr, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getBody()) ? recursionLevel : recursionLevel + 1);
		printTabs(ss, recursionLevel) << "while (";
		printExpr(ss, node->getExpr(), mgr);
		ss << ");\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainReturnStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		if (node->getExpr() == nullptr || node->getExpr()->getAstNode() == nullptr)
		{
			ss << "return;\n";
		}
		else
		{
			ss << "return ";
			printExpr(ss, node->getExpr(), mgr);
			ss << ";\n";
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainVarDeclStmtNode*>(stmt))
	{
		if (!ignoreFirstLineSpaces)
			printTabs(ss, recursionLevel);
		ss << removeNewLines(get_source_text(node->getAstNode()->getSourceRange(), mgr));
		ss << "\n";
		return;
	}

	throw std::string("unexpected node");
}


std::string toCustomCppString(ControlFlowDomainFuncDeclNode * func, clang::SourceManager & mgr, bool isDebug)
{
	std::stringstream ss;
	//func->getAstNode()->getDeclaredReturnType().getAsString()
	ss << func->getAstNode()->getDeclaredReturnType().getAsString() << " " 
	   << func->getAstNode()->getDeclName().getAsString()
	   << "(" << removeMultipleSpaces(removeNewLines(get_source_text(func->getAstNode()->getParametersSourceRange(), mgr))) << ")\n";

	//ss << removeNewLines(get_source_text(func->getAstNode()->getSourceRange(), mgr));
	toCustomCppStringInner(ss, func->getBody(), mgr, isDebug);
	return ss.str();
}