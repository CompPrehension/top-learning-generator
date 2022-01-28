#include "cntrl-flow-domain-funtions.h"
using namespace llvm;


ControlFlowDomainExprStmtNode* mapExprToControlflowDst(Expr* expr)
{
	if (expr == nullptr)
		return nullptr;

	return new ControlFlowDomainExprStmtNode(expr);
}

ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl, ASTContext& astCtx)
{
	if (funcDecl == nullptr || !funcDecl->getBody() || (isa<clang::CompoundStmt>(funcDecl->getBody()) && dyn_cast<clang::CompoundStmt>(funcDecl->getBody())->body().empty()))
		return nullptr;

	auto body = mapToControlflowDst(funcDecl->getBody(), astCtx);
	return new ControlFlowDomainFuncDeclNode(funcDecl, body);
}

ControlFlowDomainStmtNode* mapToControlflowDst(Stmt* stmt, ASTContext& astCtx)
{
	if (stmt == nullptr)
		return nullptr;

	if (auto compoundStmt = dyn_cast<clang::CompoundStmt>(stmt))
	{
		Logger::info("Found CompoundStmt");
		vector<ControlFlowDomainStmtNode*> childs;
		for (auto stmt : compoundStmt->body())
		{
			childs.push_back(mapToControlflowDst(stmt, astCtx));
		}
		return new ControlFlowDomainStmtListNode(compoundStmt, childs);
	}		
	if (auto declStmt = dyn_cast<clang::DeclStmt>(stmt))
	{
		Logger::info("Found DeclStmt");
		bool isAllVarDecl = true;
		for (auto childDecl : declStmt->getDeclGroup())
		{
			isAllVarDecl = isAllVarDecl && isa<clang::VarDecl>(childDecl);
		}
		if (isAllVarDecl)
			return new ControlFlowDomainVarDeclStmtNode(declStmt);
	}
	if (auto forStmt = dyn_cast<clang::ForStmt>(stmt))
	{
		Logger::info("Found ForStmt");

		auto init = mapToControlflowDst(forStmt->getInit(), astCtx);
		auto expr = mapExprToControlflowDst(forStmt->getCond());
		auto inc = mapExprToControlflowDst(forStmt->getInc());
		auto body = mapToControlflowDst(forStmt->getBody(), astCtx);

		auto result = new ControlFlowDomainForStmtNode(forStmt, init, expr, inc, body);
		result->calculateComplexity(astCtx);
		return result;
	}
	if (auto ifStmt = dyn_cast<clang::IfStmt>(stmt))
	{
		Logger::info("Found IfStmt");
		auto currentIf = ifStmt;
		vector<ControlFlowDomainIfStmtPart*> ifParts;
		do
		{
			ifParts.push_back(new ControlFlowDomainIfStmtPart(currentIf, mapExprToControlflowDst(currentIf->getCond()), mapToControlflowDst(currentIf->getThen(), astCtx)));
		} while (currentIf->getElse() && isa<clang::IfStmt>(currentIf->getElse()) && (currentIf = dyn_cast<clang::IfStmt>(currentIf->getElse())));
		auto _else = mapToControlflowDst(currentIf->getElse(), astCtx);
		return new ControlFlowDomainIfStmtNode(ifParts, _else);
	}
	if (auto whileStmt = dyn_cast<clang::WhileStmt>(stmt))
	{	
		Logger::info("Found WhileStmt");
		auto expr = mapExprToControlflowDst(whileStmt->getCond());
		auto body = mapToControlflowDst(whileStmt->getBody(), astCtx);
		auto result = new ControlFlowDomainWhileStmtNode(whileStmt, expr, body);
		result->calculateComplexity(astCtx);
		return result;
	}
	if (auto doStmt = dyn_cast<clang::DoStmt>(stmt))
	{
		Logger::info("Found DoStmt");
		auto expr = mapExprToControlflowDst(doStmt->getCond());
		auto body = mapToControlflowDst(doStmt->getBody(), astCtx);
		auto result = new ControlFlowDomainDoWhileStmtNode(doStmt, expr, body);
		result->calculateComplexity(astCtx);
		return result;
	}
	if (auto returnStmt = dyn_cast<clang::ReturnStmt>(stmt))
	{
		Logger::info("Found return stmt");
		auto expr = mapExprToControlflowDst(returnStmt->getRetValue());
		return new ControlFlowDomainReturnStmtNode(returnStmt, expr);
	}
	if (auto exprStmt = dyn_cast<clang::Expr>(stmt))
	{
		Logger::info("Found expr stmt");
		return mapExprToControlflowDst(exprStmt);
	}

	Logger::warn("Found undefined stmt with ast");
	string stmtNodeDump;
	raw_string_ostream output(stmtNodeDump);
	stmt->dump(output, astCtx);
	Logger::warn(stmtNodeDump);

	return new ControlFlowDomainUndefinedStmtNode(stmt);
}

std::string toOriginalCppString(ControlFlowDomainFuncDeclNode* func, clang::SourceManager& mgr)
{
	return get_source_text(func->getAstNode()->getSourceRange(), mgr);
}


std::stringstream& printTabs(std::stringstream& ss, int level, bool condition = true)
{
	if (condition)
		ss << string(level * 4, ' ');
	return ss;
}

string getAstRawString(Stmt* node, clang::SourceManager& mgr)
{
	auto s = removeMultipleSpaces(removeNewLines(get_source_text(node->getSourceRange(), mgr)));
	if (s.length() == 0)
	{
		s = removeMultipleSpaces(removeNewLines(get_source_text_raw_tr(node->getSourceRange(), mgr)));
	}
	return s;
}


int printExpr(std::stringstream& ss, ControlFlowDomainExprStmtNode* expr, clang::SourceManager& mgr)
{
	if (expr == nullptr || expr->getAstNode() == nullptr)
		return 0;

	auto s = removeMultipleSpaces(removeNewLines(get_source_text(expr->getAstNode()->getSourceRange(), mgr)));
	if (s.length() == 0)
	{
		s = removeMultipleSpaces(removeNewLines(get_source_text_raw_tr(expr->getAstNode()->getSourceRange(), mgr)));
	}
	if (s.length() == 0)
	{
		s = removeMultipleSpaces(removeNewLines(get_source_text_raw(expr->getAstNode()->getSourceRange(), mgr)));
	}

	ss << s;
	return s.length();
}


void toCustomCppStringInner(std::stringstream& ss, ControlFlowDomainStmtNode* stmt, clang::SourceManager& mgr, ASTContext& astCtx, bool isDebug, int recursionLevel = 0, bool insertSpaces = true)
{
	if (stmt == nullptr)
		return;


	if (auto node = dynamic_cast<ControlFlowDomainUndefinedStmtNode*>(stmt))
	{
		if (isDebug)
		{
			printTabs(ss, recursionLevel, insertSpaces);
			ss << "/* undefined stmt */" << "\n";
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainStmtListNode*>(stmt))
	{		
		printTabs(ss, recursionLevel, insertSpaces);
		ss << "{" << "\n";
		for (auto innerStmt : node->getChilds())
		{
			toCustomCppStringInner(ss, innerStmt, mgr, astCtx, isDebug, recursionLevel + 1);
		}
		printTabs(ss, recursionLevel, insertSpaces) << "}" << "\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainExprStmtNode*>(stmt))
	{		
		printTabs(ss, recursionLevel, insertSpaces);
		printExpr(ss, node, mgr);
		ss << ";\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainIfStmtNode*>(stmt))
	{
		auto ifParts = node->getIfParts();
		for (int i = 0; i < ifParts.size(); ++i)
		{
			if (i == 0)
			{				
				printTabs(ss, recursionLevel, insertSpaces);

				ss << "if (";
				int exprLength = printExpr(ss, ifParts[i]->getExpr(), mgr);
				if (exprLength == 0)
					throw string("Invalid expr in if stmt");
				ss << ")\n";
			}
			else 
			{
				printTabs(ss, recursionLevel, insertSpaces);
				ss << "else if (";
				int exprLength = printExpr(ss, ifParts[i]->getExpr(), mgr);
				if (exprLength == 0)
					throw string("Invalid expr in elseif stmt");
				ss << ")\n";
			}
			toCustomCppStringInner(ss, ifParts[i]->getThenBody(), mgr, astCtx, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(ifParts[i]->getThenBody()) ? recursionLevel : recursionLevel + 1);
		}
		if (node->getElseBody() && node->getElseBody()->getAstNode())
		{			
			printTabs(ss, recursionLevel, insertSpaces) << "else\n";
			toCustomCppStringInner(ss, node->getElseBody(), mgr, astCtx, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getElseBody()) ? recursionLevel : recursionLevel + 1);
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainWhileStmtNode*>(stmt))
	{		
		printTabs(ss, recursionLevel, insertSpaces);
		ss << "while (";
		int exprLength = printExpr(ss, node->getExpr(), mgr);
		if (exprLength == 0)
			throw string("Invalid expr in while stmt");
		ss << ")\n";
		toCustomCppStringInner(ss, node->getBody(), mgr, astCtx, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getBody()) ? recursionLevel : recursionLevel + 1);
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainDoWhileStmtNode*>(stmt))
	{		
		printTabs(ss, recursionLevel, insertSpaces);
		ss << "do\n";
		toCustomCppStringInner(ss, node->getBody(), mgr, astCtx, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getBody()) ? recursionLevel : recursionLevel + 1);
		printTabs(ss, recursionLevel, insertSpaces) << "while (";
		int exprLength = printExpr(ss, node->getExpr(), mgr);
		if (exprLength == 0)
			throw string("Invalid expr in do-while stmt");
		ss << ");\n";
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainForStmtNode*>(stmt))
	{
		printTabs(ss, recursionLevel, insertSpaces);
		ss << "for (";
		toCustomCppStringInner(ss, node->getInit(), mgr, astCtx, isDebug, recursionLevel, false);
		ss << "; ";
		printExpr(ss, node->getExpr(), mgr);
		ss << "; ";
		printExpr(ss, node->getInc(), mgr);
		ss << ")\n";
		toCustomCppStringInner(ss, node->getBody(), mgr, astCtx, isDebug, dynamic_cast<ControlFlowDomainStmtListNode*>(node->getBody()) ? recursionLevel : recursionLevel + 1);
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainReturnStmtNode*>(stmt))
	{
		printTabs(ss, recursionLevel, insertSpaces);
		
		if (node->getExpr() == nullptr || node->getExpr()->getAstNode() == nullptr)
		{
			ss << "return;\n";
		}
		else
		{
			ss << "return ";
			int exprLength = printExpr(ss, node->getExpr(), mgr);
			if (exprLength == 0)
				throw string("Invalid expr");
			ss << ";\n";
		}
		return;
	}
	if (auto node = dynamic_cast<ControlFlowDomainVarDeclStmtNode*>(stmt))
	{		
		printTabs(ss, recursionLevel, insertSpaces);
		auto s = removeNewLines(get_source_text(node->getAstNode()->getSourceRange(), mgr));
		if (s.length() == 0)
			throw string("Invalid expr in var decl stmt");
		ss << s;
		ss << "\n";
		return;
	}

	Logger::warn("Unexpected node detected");

	string nodeDump;
	raw_string_ostream output(nodeDump);
	stmt->getAstNode()->dump(output, astCtx);
	Logger::warn(nodeDump);

	throw std::string("unexpected node");
}


std::string toCustomCppString(ControlFlowDomainFuncDeclNode * func, clang::SourceManager & mgr, ASTContext& astCtx, bool isDebug)
{
	std::stringstream ss;
	//func->getAstNode()->getDeclaredReturnType().getAsString()
	ss << func->getAstNode()->getDeclaredReturnType().getAsString() << " " 
	   << func->getAstNode()->getDeclName().getAsString()
	   << "(" << removeMultipleSpaces(removeNewLines(get_source_text(func->getAstNode()->getParametersSourceRange(), mgr))) << ")\n";

	//ss << removeNewLines(get_source_text(func->getAstNode()->getSourceRange(), mgr));
	toCustomCppStringInner(ss, func->getBody(), mgr, astCtx, isDebug);
	return ss.str();
}


ControlFlowDomainExprRdfNode* mapExprToRdfExprNode(ControlFlowDomainExprStmtNode* node, int& idGenerator, clang::SourceManager& mgr)
{
	if (node == NULL)
		return NULL;

	return new ControlFlowDomainExprRdfNode(++idGenerator, getAstRawString(node->getAstNode(), mgr));
}

ControlFlowDomainStmtRdfNode* mapExprToRdfStmtNode(ControlFlowDomainExprStmtNode* node, int& idGenerator, clang::SourceManager& mgr)
{
	if (node == NULL)
		return NULL;

	return new ControlFlowDomainStmtRdfNode(++idGenerator, getAstRawString(node->getAstNode(), mgr));
}

ControlFlowDomainStmtRdfNode* createUndefinedRdfNodeStmt(int& idGenerator)
{
	return new ControlFlowDomainStmtRdfNode(++idGenerator, "int temp_var_" + to_string(idGenerator) + " = 0;");
}


ControlFlowDomainLinkedRdfNode* mapToRdfNode(ControlFlowDomainStmtNode* node, int& idGenerator, clang::SourceManager& mgr, ASTContext& astCtx, bool forceToSeq = false)
{	
	if (node == NULL)
	{
		return NULL;
	}

	if (auto castedNode = dynamic_cast<ControlFlowDomainUndefinedStmtNode*>(node))
	{
		// TODO validate that
		auto val = createUndefinedRdfNodeStmt(idGenerator);
		if (forceToSeq)
		{
			vector<ControlFlowDomainLinkedRdfNode*> body;
			body.push_back(val);
			val->setFirst();
			val->setLast();
			val->setIndex(0);
			return new ControlFlowDomainSequenceRdfNode(++idGenerator, body);
		}
		else
		{
			return val;
		}
	}

	if (auto castedNode = dynamic_cast<ControlFlowDomainStmtListNode*>(node))
	{
		vector<ControlFlowDomainLinkedRdfNode*>body;
		vector<int> undefinedStmtIdx;
		ControlFlowDomainLinkedRdfNode* prev = NULL;
		auto& stmts = castedNode->getChilds();
		ControlFlowDomainStmtNode* child;
		for (int i = 0; (i < stmts.size()) && (child = stmts[i]); ++i)
		{
			if (IsType<ControlFlowDomainUndefinedStmtNode>(child))
				undefinedStmtIdx.push_back(i);
			auto current = mapToRdfNode(child, idGenerator, mgr, astCtx);
			if (!current)
				continue;
			if (prev)
			{
				prev->setNext(current);
			}
			current->setIndex(i);
			body.push_back(current);
			prev = current;
		}
		
		if (undefinedStmtIdx.size() > 0 && undefinedStmtIdx.size() < body.size())
		{
			std::reverse(undefinedStmtIdx.begin(), undefinedStmtIdx.end());
			for (int i = 0; i < undefinedStmtIdx.size(); ++i) {
				auto val = body[undefinedStmtIdx[i]];
				body.erase(body.begin() + undefinedStmtIdx[i]);
				delete val;
			}
		}
		else if (body.size() > 1 && undefinedStmtIdx.size() == body.size())
		{
			for (int i = 0, iters = body.size() - 1; i < iters; ++i) {
				auto val = body[body.size() - 1];
				body.pop_back();
				delete val;
			}
		}

		if (body.size() > 0)
		{
			body[0]->setFirst();
			body[body.size() - 1]->setLast();
		}

		return new ControlFlowDomainSequenceRdfNode(++idGenerator, body);
	}
	if (auto castedNode = dynamic_cast<ControlFlowDomainExprStmtNode*>(node))
	{
		auto val = new ControlFlowDomainStmtRdfNode(++idGenerator, getAstRawString(node->getAstNode(), mgr) + ";");
		if (forceToSeq)
		{
			vector<ControlFlowDomainLinkedRdfNode*> body;
			body.push_back(val);
			val->setFirst();
			val->setLast();
			val->setIndex(0);
			return new ControlFlowDomainSequenceRdfNode(++idGenerator, body);
		}		
		else
		{
			return val;
		}
	}

	if (auto castedNode = dynamic_cast<ControlFlowDomainIfStmtNode*>(node))
	{
		vector<ControlFlowDomainAlternativeBranchRdfNode*> alternatives;
		ControlFlowDomainAlternativeBranchRdfNode* prevBranchNode = NULL;
		auto ifParts = castedNode->getIfParts();
		int i = 0;
		for (i = 0; i < ifParts.size(); ++i)
		{
			auto seq = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(ifParts[i]->getThenBody(), idGenerator, mgr, astCtx, true);
			if (!seq)
				return NULL;

			if (seq->getBody().size() == 0) 
			{
				Logger::info("Found empty else body - add undefined action");
				seq->getBody().push_back(createUndefinedRdfNodeStmt(idGenerator));
			}

			auto expr = mapExprToRdfExprNode(ifParts[i]->getExpr(), idGenerator, mgr);
			ControlFlowDomainAlternativeBranchRdfNode* branchNode = (i == 0)
				? (ControlFlowDomainAlternativeBranchRdfNode*)new ControlFlowDomainAlternativeIfBranchRdfNode(++idGenerator, expr, vector<ControlFlowDomainLinkedRdfNode*>(seq->getBody()))
				: (ControlFlowDomainAlternativeBranchRdfNode*)new ControlFlowDomainAlternativeElseIfBranchRdfNode(++idGenerator, expr, vector<ControlFlowDomainLinkedRdfNode*>(seq->getBody()));
			if (prevBranchNode)
			{
				prevBranchNode->setNext(branchNode);
			}
			branchNode->setIndex(i);
			alternatives.push_back(branchNode);
			seq->setBody(vector<ControlFlowDomainLinkedRdfNode*>());
			delete seq;
			prevBranchNode = branchNode;
		}
		if (castedNode->getElseBody() && castedNode->getElseBody()->getAstNode())
		{
			auto seq = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(castedNode->getElseBody(), idGenerator, mgr, astCtx, true);
			if (seq->getBody().size() == 0)
			{
				Logger::info("Found empty else body - add undefined action");
				seq->getBody().push_back(createUndefinedRdfNodeStmt(idGenerator));
			}

			auto branchNode = new ControlFlowDomainAlternativeElseBranchRdfNode(++idGenerator, vector<ControlFlowDomainLinkedRdfNode*>(seq->getBody()));
			prevBranchNode->setNext(branchNode);
			branchNode->setIndex(i);
			alternatives.push_back(branchNode);
			seq->setBody(vector<ControlFlowDomainLinkedRdfNode*>());
			delete seq;
		}
		if (alternatives.size() > 0)
		{
			alternatives[0]->setFirst();
			alternatives[alternatives.size() - 1]->setLast();
		}

		return new ControlFlowDomainAlternativeRdfNode(++idGenerator, alternatives);
	}

	if (auto castedNode = dynamic_cast<ControlFlowDomainWhileStmtNode*>(node))
	{
		auto exprRdf = mapExprToRdfExprNode(castedNode->getExpr(), idGenerator, mgr);
		auto bodyRdf = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(castedNode->getBody(), idGenerator, mgr, astCtx, true);
		if (bodyRdf->getBody().size() == 0)
		{
			Logger::info("Found empty cycle body - add undefined action");
			bodyRdf->getBody().push_back(createUndefinedRdfNodeStmt(idGenerator));
		}

		return new ControlFlowDomainWhileDoRdfNode(++idGenerator, castedNode->getComplexity(), exprRdf, bodyRdf);
	}
	if (auto castedNode = dynamic_cast<ControlFlowDomainDoWhileStmtNode*>(node))
	{
		auto exprRdf = mapExprToRdfExprNode(castedNode->getExpr(), idGenerator, mgr);
		auto bodyRdf = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(castedNode->getBody(), idGenerator, mgr, astCtx, true);
		if (bodyRdf->getBody().size() == 0)
		{
			Logger::info("Found empty cycle body - add undefined action");
			bodyRdf->getBody().push_back(createUndefinedRdfNodeStmt(idGenerator));
		}

		return new ControlFlowDomainDoWhileRdfNode(++idGenerator, castedNode->getComplexity(), exprRdf, bodyRdf);
	}
	if (auto castedNode = dynamic_cast<ControlFlowDomainForStmtNode*>(node))
	{
		auto initRdf = (ControlFlowDomainStmtRdfNode*)mapToRdfNode(castedNode->getInit(), idGenerator, mgr, astCtx);
		auto exprRdf = mapExprToRdfExprNode(castedNode->getExpr(), idGenerator, mgr);
		auto incRdf = mapExprToRdfStmtNode(castedNode->getInc(), idGenerator, mgr);
		auto bodyRdf = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(castedNode->getBody(), idGenerator, mgr, astCtx, true);
		if (bodyRdf->getBody().size() == 0)
		{
			Logger::info("Found empty cycle body - add undefined action");
			bodyRdf->getBody().push_back(createUndefinedRdfNodeStmt(idGenerator));
		}

		return new ControlFlowDomainForRdfNode(++idGenerator, castedNode->getComplexity(), initRdf, exprRdf, incRdf, bodyRdf);
	}
	if (auto castedNode = dynamic_cast<ControlFlowDomainReturnStmtNode*>(node))
	{
		auto val = new ControlFlowDomainStmtRdfNode(++idGenerator, getAstRawString(node->getAstNode(), mgr) + ";");
		if (forceToSeq)
		{
			vector<ControlFlowDomainLinkedRdfNode*> body;
			body.push_back(val);
			val->setFirst();
			val->setLast();
			val->setIndex(0);
			return new ControlFlowDomainSequenceRdfNode(++idGenerator, body);
		}
		else
		{
			return val;
		}
	}
	if (auto castedNode = dynamic_cast<ControlFlowDomainVarDeclStmtNode*>(node))
	{
		auto val = new ControlFlowDomainStmtRdfNode(++idGenerator, getAstRawString(node->getAstNode(), mgr));
		if (forceToSeq)
		{
			vector<ControlFlowDomainLinkedRdfNode*> body;
			body.push_back(val);
			val->setFirst();
			val->setLast();
			val->setIndex(0);
			return new ControlFlowDomainSequenceRdfNode(++idGenerator, body);
		}
		else
		{
			return val;
		}
	}

	Logger::warn("Couldnt map node to rdf");
	
	string nodeDump;
	raw_string_ostream output(nodeDump);
	node->getAstNode()->dump(output, astCtx);
	Logger::warn(nodeDump);

	throw std::string("unexpected node");
}




ControlFlowDomainAlgorythmRdfNode* mapToRdfNode(string algUniqueName, ControlFlowDomainFuncDeclNode* node, clang::SourceManager& mgr, ASTContext& astCtx)
{
	int id = 0;
	auto funcBody = mapToRdfNode(node->getBody(), id, mgr, astCtx, true);
	return new ControlFlowDomainAlgorythmRdfNode(algUniqueName, ++id, (ControlFlowDomainSequenceRdfNode*)funcBody);
}

