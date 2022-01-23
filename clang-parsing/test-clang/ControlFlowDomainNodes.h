#pragma once
#include <string>
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/AST/ASTContext.h"
#include <llvm/Support/CommandLine.h>
#include <clang/Lex/Lexer.h>
#include "ControlFlowCycleComplexity.h"
#include "Logger.h"

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


class ControlFlowDomainAbstractCycleStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainAbstractCycleStmtNode(Stmt* astNode, ControlFlowCycleComplexity complexity)
		: ControlFlowDomainStmtNode(astNode), complexity(complexity)
	{
	}

	ControlFlowCycleComplexity getComplexity() {
		return complexity;
	}

	virtual void calculateComplexity(ASTContext & astCtx) = 0;

protected:
	ControlFlowCycleComplexity complexity;
};


class ControlFlowDomainWhileStmtNode : public ControlFlowDomainAbstractCycleStmtNode
{
public:
	ControlFlowDomainWhileStmtNode(WhileStmt* astNode, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainAbstractCycleStmtNode(astNode, ControlFlowCycleComplexity::Undefined()), expr(expr), body(body)
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

	virtual void calculateComplexity(ASTContext& astCtx)
	{
		// not implemented yet
	}

private:
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainStmtNode* body;
};

class ControlFlowDomainDoWhileStmtNode : public ControlFlowDomainAbstractCycleStmtNode
{
public:
	ControlFlowDomainDoWhileStmtNode(DoStmt* astNode, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainAbstractCycleStmtNode(astNode, ControlFlowCycleComplexity::NonZeroTimes()), expr(expr), body(body)
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

	virtual void calculateComplexity(ASTContext& astCtx)
	{
		// not implemented yet
	}

private:
	ControlFlowDomainExprStmtNode* expr;
	ControlFlowDomainStmtNode* body;
};

class ControlFlowDomainForStmtNode : public ControlFlowDomainAbstractCycleStmtNode
{
public:
	ControlFlowDomainForStmtNode(ForStmt* astNode, ControlFlowDomainStmtNode* init, ControlFlowDomainExprStmtNode* expr, ControlFlowDomainExprStmtNode* inc, ControlFlowDomainStmtNode* body)
		: ControlFlowDomainAbstractCycleStmtNode(astNode, ControlFlowCycleComplexity::Undefined()), init(init), expr(expr), inc(inc), body(body)
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

	virtual void calculateComplexity(ASTContext & astCtx)
	{		
		{
			Logger::info("Trying to match pattern for(/*any*/; intVar < const; ++intVar)");

			if (!this->getExpr() || !this->getInc()) {
				Logger::info("Empty expression or inc");
				goto fist_check_end;
			}

			// ensure middle expresiion is "<"
			auto expr = dyn_cast<Expr>(this->getExpr()->getAstNode());
			expr = expr->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto binaryExpr = dyn_cast<BinaryOperator>(expr);
			if (!binaryExpr || binaryExpr->getOpcode() != BinaryOperatorKind::BO_LT) {
				Logger::info("Middle expression is not '<'");
				goto fist_check_end;
			}				
			
			// ensure expression right part is int constant 
			Expr::EvalResult Result;
			auto isRightConst = !binaryExpr->getRHS()->isValueDependent() && binaryExpr->getRHS()->EvaluateAsInt(Result, astCtx);
			if (!isRightConst) {
				Logger::info("Couldnt evaluate right part '<'");
				goto fist_check_end;
			}
			auto rightValue = Result.Val.getInt().getExtValue();

			// ensure expression left part is integer variable
			auto varExpr = dyn_cast<DeclRefExpr>(binaryExpr->getLHS()->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts());
			if (!varExpr || !varExpr->getDecl()->getType().getTypePtr()->isIntegerType()) {
				Logger::info("Couldnt evaluate left part '<' or value isnt integer");
				goto fist_check_end;
			}

			// trying to evaluate var initial value 
			auto vardecl = dyn_cast<VarDecl>(varExpr->getDecl());
			if (!vardecl) {
				Logger::info("Couldnt find var decl info");
				goto fist_check_end;
			}
			auto isVarEvaluated = vardecl->getInit() && !vardecl->getInit()->isValueDependent() && vardecl->getInit()->EvaluateAsInt(Result, astCtx);
			if (!isVarEvaluated) {
				Logger::info("Couldnt find var inital value");
				goto fist_check_end;
			}
			auto variableValue = Result.Val.getInt().getExtValue();

			// ensure last expression is increment
			auto incExpressionAstNode = dyn_cast<Expr>(this->getInc()->getAstNode())->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto incExpression = dyn_cast<UnaryOperator>(incExpressionAstNode);
			if (incExpression->getOpcode() != UnaryOperatorKind::UO_PostInc && incExpression->getOpcode() != UnaryOperatorKind::UO_PreInc) {
				Logger::info("Last expression isn't increment");
				goto fist_check_end;
			}

			Logger::info("Pattern matched");

			if (variableValue < rightValue)
				complexity = ControlFlowCycleComplexity::NTimes(variableValue, true, rightValue, false);
			else
				complexity = ControlFlowCycleComplexity::ZeroTimes();
		
			Logger::info("New complexity - " + complexity.to_string());

			return;		
		}
	fist_check_end:

		{
			Logger::info("Trying to match pattern for(/*any*/; intVar <= const; ++intVar)");

			if (!this->getExpr() || !this->getInc()) {
				Logger::info("Empty expression or inc");
				goto second_check_end;
			}

			// ensure middle expresiion is "<"
			auto expr = dyn_cast<Expr>(this->getExpr()->getAstNode());
			expr = expr->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto binaryExpr = dyn_cast<BinaryOperator>(expr);
			if (!binaryExpr || binaryExpr->getOpcode() != BinaryOperatorKind::BO_LE) {
				Logger::info("Middle expression is not '<='");
				goto second_check_end;
			}

			// ensure expression right part is int constant 
			Expr::EvalResult Result;
			auto isRightConst = !binaryExpr->getRHS()->isValueDependent() && binaryExpr->getRHS()->EvaluateAsInt(Result, astCtx);
			if (!isRightConst) {
				Logger::info("Couldnt evaluate right part '<='");
				goto second_check_end;
			}
			auto rightValue = Result.Val.getInt().getExtValue();

			// ensure expression left part is integer variable
			auto varExpr = dyn_cast<DeclRefExpr>(binaryExpr->getLHS()->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts());
			if (!varExpr || !varExpr->getDecl()->getType().getTypePtr()->isIntegerType()) {
				Logger::info("Couldnt evaluate left part '<=' or value isnt integer");
				goto second_check_end;
			}

			// trying to evaluate var initial value 
			auto vardecl = dyn_cast<VarDecl>(varExpr->getDecl());
			if (!vardecl) {
				Logger::info("Couldnt find var decl info");
				goto second_check_end;
			}
			auto isVarEvaluated = vardecl->getInit() && !vardecl->getInit()->isValueDependent() && vardecl->getInit()->EvaluateAsInt(Result, astCtx);
			if (!isVarEvaluated) {
				Logger::info("Couldnt find var inital value");
				goto second_check_end;
			}
			auto variableValue = Result.Val.getInt().getExtValue();

			// ensure last expression is increment
			auto incExpressionAstNode = dyn_cast<Expr>(this->getInc()->getAstNode())->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto incExpression = dyn_cast<UnaryOperator>(incExpressionAstNode);
			if (incExpression->getOpcode() != UnaryOperatorKind::UO_PostInc && incExpression->getOpcode() != UnaryOperatorKind::UO_PreInc) {
				Logger::info("Last expression isn't increment");
				goto second_check_end;
			}

			Logger::info("Pattern matched");

			if (variableValue <= rightValue)
				complexity = ControlFlowCycleComplexity::NTimes(variableValue, true, rightValue, true);
			else
				complexity = ControlFlowCycleComplexity::ZeroTimes();

			Logger::info("New complexity - " + complexity.to_string());

			return;
		}
	second_check_end:



		return;
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

