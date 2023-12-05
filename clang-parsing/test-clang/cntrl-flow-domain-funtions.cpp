#include "cntrl-flow-domain-funtions.h"
using namespace llvm;

void findFunctionCalls(
    Stmt *stmt, 
    clang::SourceManager &mgr,
    vector<clang::CallExpr *>& calls,
    int depth = 0) {
  
  if (stmt == nullptr)
    return;
  for (auto *ch : stmt->children()) {
    auto *callExpr = dyn_cast<clang::CallExpr>(ch);
    if (!callExpr || dyn_cast<clang::CXXOperatorCallExpr>(ch)) {
        findFunctionCalls(ch, mgr, calls, depth + 1);
        continue;
    }

    calls.push_back(callExpr);
  }
}

vector<clang::CallExpr *> findFunctionCalls(Stmt *stmt, clang::SourceManager &mgr) {
  vector<clang::CallExpr *> calls;
  findFunctionCalls(stmt, mgr, calls);
  
  auto fullExprSr = stmt->getSourceRange();
  auto fullExpr = get_source_text(fullExprSr, mgr);
  Logger::info("Source expr with fun calls " + fullExpr);
  Logger::info("Source Range " + fullExprSr.printToString(mgr));

  for (auto *call : calls) {

    auto callExprSr = call->getSourceRange();
    auto callExpr = get_source_text(call->getSourceRange(), mgr);
    
    Logger::info("Found func call " + callExpr);
    Logger::info("Source Range " + callExprSr.printToString(mgr));
  }

  return calls;
}

ControlFlowDomainExprStmtNode *mapExprToControlflowDst(Expr *expr, ASTContext& astCtx, clang::SourceManager &mgr, int funcDepth, ControlFlowDomainFuncDeclNodeSet& calledFunctions) {
    if (expr == nullptr)
        return nullptr;

    // TODO analyze expr for fun calls
    // пройтись по всем узлам выражения (вероятно от листьев к корню)
    // искать подвыражения с вызовом, фиксировать их подстроки??????
    // количестро аргументов при вызове
    // вероятно в функции нужно хранить список вызываемых ункций в теле
    auto calls = findFunctionCalls(expr, mgr);
    if (calls.size() > 0) {
        for (auto call: calls) {
            auto decl = call->getDirectCallee();

            // TODO check for recursion
            if (decl) {
                auto mappedDecl = mapToControlflowDst(decl, astCtx, mgr, funcDepth + 1);
				calledFunctions.insert(mappedDecl);
            }
        }

        return new ControlFlowDomainExprWithFuncCallsStmtNode(expr);
    }
    return new ControlFlowDomainExprStmtNode(expr);
}

ControlFlowDomainAlgo* mapToControlflowDst(FunctionDecl* funcDecl, ASTContext& astCtx, clang::SourceManager& mgr)
{
	auto rootF = mapToControlflowDst(funcDecl, astCtx, mgr, 0);
	
    ControlFlowDomainFuncDeclNodeSet allFunctions;
    vector<ControlFlowDomainFuncDeclNode*> stack = { rootF };    
    while (stack.size() > 0) {
		auto f = stack.back();
        stack.pop_back();

		if (allFunctions.find(f) != allFunctions.end()) {
			continue;
		}

		allFunctions.insert(f);
		stack.insert(stack.end(), f->getCalledFunctions().begin(), f->getCalledFunctions().end());
    }

	return new ControlFlowDomainAlgo(allFunctions, rootF);
}

ControlFlowDomainFuncDeclNode* mapToControlflowDst(FunctionDecl* funcDecl, ASTContext& astCtx, clang::SourceManager &mgr, int funcDepth)
{
    if (funcDecl == nullptr || !funcDecl->getBody() || (isa<clang::CompoundStmt>(funcDecl->getBody()) && dyn_cast<clang::CompoundStmt>(funcDecl->getBody())->body().empty()))
        return nullptr;

    ControlFlowDomainFuncDeclNodeSet calledFunctions;
    auto body = mapToControlflowDst(funcDecl->getBody(), astCtx, mgr, funcDepth, calledFunctions);
    return new ControlFlowDomainFuncDeclNode(funcDecl, body, calledFunctions);
}

ControlFlowDomainStmtNode *mapToControlflowDst(Stmt *stmt, ASTContext &astCtx, clang::SourceManager &mgr, int funcDepth, ControlFlowDomainFuncDeclNodeSet& calledFunctions) {
    if (stmt == nullptr)
        return nullptr;

    /*
    if (stmt->getSourceRange().getBegin().isMacroID() || stmt->getSourceRange().getEnd().isMacroID())
    {
        Logger::warn("Found macro stmt with ast below");
        goto dump_and_return_undefined;
    }
    */

    if (auto compoundStmt = dyn_cast<clang::CompoundStmt>(stmt))
    {
        Logger::info("Found CompoundStmt");
        vector<ControlFlowDomainStmtNode*> childs;
        for (auto stmt : compoundStmt->body())
        {
            childs.push_back(mapToControlflowDst(stmt, astCtx, mgr, funcDepth, calledFunctions));
        }
        return new ControlFlowDomainStmtListNode(compoundStmt, childs);
    }		
    if (auto declStmt = dyn_cast<clang::DeclStmt>(stmt))
    {
        Logger::info("Found DeclStmt");
        bool isAllVarDecl = true;
        for (auto childDecl : declStmt->getDeclGroup())
        {
            isAllVarDecl = isAllVarDecl && (isa<clang::VarDecl>(childDecl) || isa<clang::RecordDecl>(childDecl));
        }
        if (isAllVarDecl)
            return new ControlFlowDomainVarDeclStmtNode(declStmt);
    }
    if (auto forStmt = dyn_cast<clang::ForStmt>(stmt))
    {
        Logger::info("Found ForStmt");

        auto init = mapToControlflowDst(forStmt->getInit(), astCtx, mgr, funcDepth, calledFunctions);
        auto expr = mapExprToControlflowDst(forStmt->getCond(), astCtx, mgr, funcDepth, calledFunctions);
        auto inc = mapExprToControlflowDst(forStmt->getInc(), astCtx, mgr, funcDepth, calledFunctions);
        auto body = mapToControlflowDst(forStmt->getBody(), astCtx, mgr, funcDepth, calledFunctions);

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
            ifParts.push_back(new ControlFlowDomainIfStmtPart(currentIf, mapExprToControlflowDst(currentIf->getCond(), astCtx, mgr, funcDepth, calledFunctions), mapToControlflowDst(currentIf->getThen(), astCtx, mgr, funcDepth, calledFunctions)));
        } while (currentIf->getElse() && isa<clang::IfStmt>(currentIf->getElse()) && (currentIf = dyn_cast<clang::IfStmt>(currentIf->getElse())));
        auto _else = mapToControlflowDst(currentIf->getElse(), astCtx, mgr, funcDepth, calledFunctions);
        return new ControlFlowDomainIfStmtNode(ifParts, _else);
    }
    if (auto whileStmt = dyn_cast<clang::WhileStmt>(stmt))
    {	
        Logger::info("Found WhileStmt");
        auto expr = mapExprToControlflowDst(whileStmt->getCond(), astCtx, mgr, funcDepth, calledFunctions);
        auto body = mapToControlflowDst(whileStmt->getBody(), astCtx, mgr, funcDepth, calledFunctions);
        auto result = new ControlFlowDomainWhileStmtNode(whileStmt, expr, body);
        result->calculateComplexity(astCtx);
        return result;
    }
    if (auto doStmt = dyn_cast<clang::DoStmt>(stmt))
    {
        Logger::info("Found DoStmt");
        auto expr = mapExprToControlflowDst(doStmt->getCond(), astCtx, mgr, funcDepth, calledFunctions);
        auto body = mapToControlflowDst(doStmt->getBody(), astCtx, mgr, funcDepth, calledFunctions);
        auto result = new ControlFlowDomainDoWhileStmtNode(doStmt, expr, body);
        result->calculateComplexity(astCtx);
        return result;
    }
    if (auto returnStmt = dyn_cast<clang::ReturnStmt>(stmt))
    {
        Logger::info("Found return stmt");
        auto expr = mapExprToControlflowDst(returnStmt->getRetValue(), astCtx, mgr, funcDepth, calledFunctions);
        return new ControlFlowDomainReturnStmtNode(returnStmt, expr);
    }
    if (auto breakStmt = dyn_cast<clang::BreakStmt>(stmt))
    {
        Logger::info("Found break stmt");
        return new ControlFlowDomainBreakStmtNode(breakStmt);
    }
    if (auto continueStmt = dyn_cast<clang::ContinueStmt>(stmt))
    {
        Logger::info("Found continue stmt");
        return new ControlFlowDomainContinueStmtNode(continueStmt);
    }
    if (auto exprStmt = dyn_cast<clang::Expr>(stmt))
    {
        Logger::info("Found expr stmt");
        return mapExprToControlflowDst(exprStmt, astCtx, mgr, funcDepth, calledFunctions);
    }

    Logger::warn("Found undefined stmt with ast");

dump_and_return_undefined:
    string stmtNodeDump;
    raw_string_ostream output(stmtNodeDump);
    stmt->dump(output, astCtx);
    Logger::warn(stmtNodeDump);
    return new ControlFlowDomainUndefinedStmtNode(stmt);
}

std::string toOriginalCppString(ControlFlowDomainAlgo* algo, clang::SourceManager& mgr)
{
    std::stringstream ss;
    for (auto func: algo->getFunctions()) {
        ss << get_source_text(func->getAstNode()->getSourceRange(), mgr);
		ss << "\n\n";
    }
	return ss.str();
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
        auto &ifParts = node->getIfParts();
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
    if (auto node = dynamic_cast<ControlFlowDomainBreakStmtNode*>(stmt))
    {
        printTabs(ss, recursionLevel, insertSpaces);
        ss << "break;\n";
        return;
    }
    if (auto node = dynamic_cast<ControlFlowDomainContinueStmtNode*>(stmt))
    {
        printTabs(ss, recursionLevel, insertSpaces);
        ss << "continue;\n";
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


std::string toCustomCppString(ControlFlowDomainAlgo* algo, clang::SourceManager & mgr, ASTContext& astCtx, bool isDebug)
{
    std::stringstream ss;
	for (auto func : algo->getFunctions())
	{
        //func->getAstNode()->getDeclaredReturnType().getAsString()
        ss << func->getAstNode()->getDeclaredReturnType().getAsString() << " "
            << func->getAstNode()->getDeclName().getAsString()
            << "(" << removeMultipleSpaces(removeNewLines(get_source_text(func->getAstNode()->getParametersSourceRange(), mgr))) << ")\n";

        //ss << removeNewLines(get_source_text(func->getAstNode()->getSourceRange(), mgr));
        toCustomCppStringInner(ss, func->getBody(), mgr, astCtx, isDebug);

        ss << "\n\n";
	}
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
        ControlFlowDomainLinkedRdfNode* prev = NULL;
        auto& stmts = castedNode->getChilds();
        ControlFlowDomainStmtNode* child;
        for (int i = 0; (i < stmts.size()) && (child = stmts[i]); ++i)
        {
            if (IsType<ControlFlowDomainUndefinedStmtNode>(child))
                continue;
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
        
        if (body.size() == 0)
        {
            auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
            undefinedStmt->setIndex(0);
            body.push_back(undefinedStmt);
        }
        
        body[0]->setFirst();
        body[body.size() - 1]->setLast();

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
        auto &ifParts = castedNode->getIfParts();
        int i = 0;
        for (i = 0; i < ifParts.size(); ++i)
        {
            auto seq = (ControlFlowDomainSequenceRdfNode*)mapToRdfNode(ifParts[i]->getThenBody(), idGenerator, mgr, astCtx, true);
            if (!seq)
                return NULL;

            if (seq->getBody().size() == 0) 
            {
                Logger::info("Found empty else body - add undefined action");
                auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
                undefinedStmt->setFirst();
                undefinedStmt->setLast();
                undefinedStmt->setIndex(0);
                seq->getBody().push_back(undefinedStmt);
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
                auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
                undefinedStmt->setFirst();
                undefinedStmt->setLast();
                undefinedStmt->setIndex(0);
                seq->getBody().push_back(undefinedStmt);
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
            auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
            undefinedStmt->setFirst();
            undefinedStmt->setLast();
            undefinedStmt->setIndex(0);
            bodyRdf->getBody().push_back(undefinedStmt);
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
            auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
            undefinedStmt->setFirst();
            undefinedStmt->setLast();
            undefinedStmt->setIndex(0);
            bodyRdf->getBody().push_back(undefinedStmt);
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
            auto undefinedStmt = createUndefinedRdfNodeStmt(idGenerator);
            undefinedStmt->setFirst();
            undefinedStmt->setLast();
            undefinedStmt->setIndex(0);
            bodyRdf->getBody().push_back(undefinedStmt);
        }

        return new ControlFlowDomainForRdfNode(++idGenerator, castedNode->getComplexity(), initRdf, exprRdf, incRdf, bodyRdf);
    }
    if (auto castedNode = dynamic_cast<ControlFlowDomainBreakStmtNode*>(node))
    {
        auto val = new ControlFlowDomainBreakStmtRdfNode(++idGenerator);
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
    if (auto castedNode = dynamic_cast<ControlFlowDomainContinueStmtNode*>(node))
    {
        auto val = new ControlFlowDomainContinueStmtRdfNode(++idGenerator);
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
    if (auto castedNode = dynamic_cast<ControlFlowDomainReturnStmtNode*>(node))
    {
        auto exprStr = castedNode->getExpr() && castedNode->getExpr()->getAstNode() ? getAstRawString(castedNode->getExpr()->getAstNode(), mgr) : "";
        auto val = new ControlFlowDomainReturnStmtRdfNode(++idGenerator, exprStr);
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
    return new ControlFlowDomainAlgorythmRdfNode(algUniqueName, ++id, (ControlFlowDomainSequenceRdfNode*)funcBody, node->getBody()->calcConcepts());
}

