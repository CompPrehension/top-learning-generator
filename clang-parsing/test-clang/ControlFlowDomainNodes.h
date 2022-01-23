#pragma once
#include <string>
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/AST/ASTContext.h"
#include <llvm/Support/CommandLine.h>
#include <clang/Lex/Lexer.h>

using namespace std;
using namespace clang;

class ControlFlowDomainNode
{
public:
	virtual ~ControlFlowDomainNode()
	{
	}
};

class ControlFlowDomainStmtNode : public ControlFlowDomainNode
{
public:
	ControlFlowDomainStmtNode(Stmt* astNode)
		: astNode(astNode)
	{
	}
	Stmt* getAstNode() { return this->astNode; };
private:
	Stmt* astNode;
};

class ControlFlowDomainUndefinedStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainUndefinedStmtNode(Stmt* astNode)
		: ControlFlowDomainStmtNode(astNode)
	{
	}
};

class ControlFlowDomainStmtListNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainStmtListNode(CompoundStmt* astNode, vector<ControlFlowDomainStmtNode*> stmts)
		: ControlFlowDomainStmtNode(astNode), stmts(stmts)
	{
	}
	~ControlFlowDomainStmtListNode()
	{
		for (auto* stmt : this->stmts)
		{
			if (stmt)
				delete stmt;
		}
	}

	vector<ControlFlowDomainStmtNode*>& getChilds() { return this->stmts; }
private:
	vector<ControlFlowDomainStmtNode*> stmts;
};


class ControlFlowDomainExprStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainExprStmtNode(Expr* astNode)
		: ControlFlowDomainStmtNode(astNode)
	{
	}
};


class ControlFlowDomainIfStmtPart
{
public:
	ControlFlowDomainIfStmtPart(IfStmt* astNode, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainStmtNode* thenBody)
		: astNode(astNode), expr(expr), thenBody(thenBody)
	{
	}
	~ControlFlowDomainIfStmtPart()
	{
		if (this->expr)
			delete this->expr;
		if (this->thenBody)
			delete this->thenBody;
	}

	IfStmt* getAstNode() { return this->astNode; }
	ControlFlowDomainExprStmtNode* getExpr() { return this->expr; }
	ControlFlowDomainStmtNode* getThenBody() { return this->thenBody; }

private:
	IfStmt* astNode;
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainStmtNode* thenBody;
};


class ControlFlowDomainIfStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainIfStmtNode(vector<ControlFlowDomainIfStmtPart*> ifParts, ControlFlowDomainStmtNode* elseBody)
		: ControlFlowDomainStmtNode(ifParts[0]->getAstNode()), ifParts(ifParts), elseBody(elseBody)
	{
	}
	~ControlFlowDomainIfStmtNode()
	{
		for (auto part : this->ifParts)
		{
			if (part)
				delete part;
		}
		if (this->elseBody)
			delete this->elseBody;
	}

	ControlFlowDomainExprStmtNode* getOriginalExpr() { return this->ifParts[0]->getExpr(); }
	vector<ControlFlowDomainIfStmtPart*>& getIfParts() { return this->ifParts; }
	ControlFlowDomainStmtNode* getElseBody() { return this->elseBody; }
private:
	vector<ControlFlowDomainIfStmtPart*> ifParts;
	ControlFlowDomainStmtNode* elseBody;
};

class ControlFlowDomainWhileStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainWhileStmtNode(WhileStmt* astNode, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainStmtNode(astNode), expr(expr), body(body)
	{
	}
	~ControlFlowDomainWhileStmtNode() 
	{
		if (this->expr)
			delete this->expr;
		if (this->body)
			delete this->body;
	}


	ControlFlowDomainExprStmtNode* getExpr() { return this->expr; }
	ControlFlowDomainStmtNode* getBody() { return this->body; }
private:
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainStmtNode* body;
};

class ControlFlowDomainDoWhileStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainDoWhileStmtNode(DoStmt* astNode, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainStmtNode(astNode), expr(expr), body(body)
	{
	}
	~ControlFlowDomainDoWhileStmtNode()
	{
		if (this->expr)
			delete this->expr;
		if (this->body)
			delete this->body;
	}

	ControlFlowDomainExprStmtNode* getExpr() { return this->expr; }
	ControlFlowDomainStmtNode* getBody() { return this->body; }
private:
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainStmtNode* body;
};

class ControlFlowDomainForStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainForStmtNode(ForStmt* astNode, ControlFlowDomainStmtNode* init, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainExprStmtNode* inc, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainStmtNode(astNode), init(init), expr(expr), inc(inc), body(body)
	{
	}
	~ControlFlowDomainForStmtNode()
	{
		if (this->init)
			delete this->init;
		if (this->expr)
			delete this->expr;
		if (this->inc)
			delete this->inc;
		if (this->body)
			delete this->body;
	}


	ControlFlowDomainStmtNode* getInit() { return this->init; }
	ControlFlowDomainExprStmtNode* getExpr() { return this->expr; }
	ControlFlowDomainExprStmtNode* getInc() { return this->inc; }
	ControlFlowDomainStmtNode* getBody() { return this->body; }

private:
	ControlFlowDomainStmtNode* init;
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainExprStmtNode* inc;
	ControlFlowDomainStmtNode* body;
};

class ControlFlowDomainReturnStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainReturnStmtNode(ReturnStmt* astNode, ControlFlowDomainExprStmtNode* expr)
		: ControlFlowDomainStmtNode(astNode), expr(expr)
	{
	}
	~ControlFlowDomainReturnStmtNode()
	{
		if (this->expr)
			delete this->expr;
	}

	ControlFlowDomainExprStmtNode* getExpr() { return this->expr; }
private:
	ControlFlowDomainExprStmtNode* expr;
};

class ControlFlowDomainFuncDeclNode
{
public:
	ControlFlowDomainFuncDeclNode(FunctionDecl* astNode, ControlFlowDomainStmtNode* body)
		: astNode(astNode), body(body)
	{
	}
	~ControlFlowDomainFuncDeclNode()
	{
		if (this->body)
			delete this->body;
	}

	ControlFlowDomainStmtNode* getBody() { return this->body; }

	FunctionDecl* getAstNode() { return this->astNode; }

private:
	ControlFlowDomainStmtNode* body;
	FunctionDecl* astNode;
};

class ControlFlowDomainVarDeclStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainVarDeclStmtNode(DeclStmt* astNode)
		: ControlFlowDomainStmtNode(astNode)
	{
	}
};

