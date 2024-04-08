#pragma once
#include <string>
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/AST/ASTContext.h"
#include <llvm/Support/CommandLine.h>
#include <clang/Lex/Lexer.h>
#include "ControlFlowConcept.h"
#include "ControlFlowCycleComplexity.h"
#include "Logger.h"
#include <unordered_set>

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

	ControlFlowConceptsSet calcConcepts() {
		ControlFlowConceptsSet result;
		CaclConcepts(astNode, result);
		return result;
	}

private:
	static void CaclConcepts(Stmt* astNode, ControlFlowConceptsSet& concepts) {
		for (auto* ch : astNode->children()) {
			if (!ch)
				continue;

			if (auto expr = dyn_cast<Expr>(ch)) {
				CaclConcepts(expr, concepts);
			}
			else if (auto decl = dyn_cast<DeclStmt>(ch)) {
				CaclConcepts(decl, concepts);
			}

			CaclConcepts(ch, concepts);
		}
	}

	static void CaclConcepts(DeclStmt* astNode, ControlFlowConceptsSet& concepts) {
		for (auto* decl : astNode->decls()) {
			if (auto* varDecl = dyn_cast<VarDecl>(decl)) {
				// auto declString = (varDecl != NULL) ? varDecl->getType().getAsString() : "";
				bool isArray = varDecl->getType().getTypePtr()->isArrayType();
				bool isPointer = varDecl->getType().getTypePtr()->isPointerType();
				if (isArray) {
					concepts.insert(ControlFlowConcept::Array);
				}
				if (isPointer) {
					concepts.insert(ControlFlowConcept::Pointer);
				}
			}
		}
	}

	static void CaclConcepts(Expr* astNode, ControlFlowConceptsSet& concepts) {
		bool containsArrayBrNode = false;
		bool containsMemberAccess = false;
		bool containsPtr = false;
		bool containsFuncCall = false;
		bool containsExplicitCast = false;

		for (auto* ch : astNode->children()) {
			containsArrayBrNode = containsArrayBrNode || dyn_cast<clang::ArraySubscriptExpr>(ch);
			containsMemberAccess = containsMemberAccess || dyn_cast<clang::MemberExpr>(ch);
            containsFuncCall = containsFuncCall || dyn_cast<clang::CallExpr>(ch) && !dyn_cast<clang::CXXOperatorCallExpr>(ch);
			containsExplicitCast = containsExplicitCast || dyn_cast<clang::CStyleCastExpr>(ch);

			auto chAsUnary = dyn_cast<clang::UnaryOperator>(ch);
			containsPtr = containsPtr || (chAsUnary && (chAsUnary->getOpcode() == UnaryOperatorKind::UO_AddrOf || chAsUnary->getOpcode() == UnaryOperatorKind::UO_Deref));
		}

		if (containsArrayBrNode)
		{
			concepts.insert(ControlFlowConcept::Array);
		}
		if (containsMemberAccess)
		{
			concepts.insert(ControlFlowConcept::ClassMemberAccess);
		}
		if (containsFuncCall)
		{
			concepts.insert(ControlFlowConcept::FuncCall);
		}
		if (containsPtr)
		{
			concepts.insert(ControlFlowConcept::Pointer);
		}
		if (containsExplicitCast)
		{
			concepts.insert(ControlFlowConcept::ExplicitCast);
		}
	}

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

class ControlFlowDomainExprWithFuncCallsStmtNode : public ControlFlowDomainExprStmtNode {
public:
    ControlFlowDomainExprWithFuncCallsStmtNode(Expr *astNode, vector<tuple<int, clang::CallExpr*>>& funcCalls)
		: ControlFlowDomainExprStmtNode(astNode), funcCalls(funcCalls)
	{
	}

	vector<tuple<int, clang::CallExpr*>>& getFuncCalls() { return this->funcCalls; }

private:
	vector<tuple<int, clang::CallExpr*>> funcCalls;
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
		{
			Logger::info("Trying to match pattern while(const) { }");

			auto exprAst = dyn_cast<Expr>(this->expr->getAstNode());
			if (!exprAst) {
				Logger::info("Invalid loop expr");
				return;
			}

			bool result;
			if (exprAst->isValueDependent() || !exprAst->EvaluateAsBooleanCondition(result, astCtx, true)) {
				Logger::info("Non constant expr");
				return;
			}

			if (result)
				this->complexity = ControlFlowCycleComplexity::InfiniteTimes();
			else
				this->complexity = ControlFlowCycleComplexity::ZeroTimes();

			Logger::info("Pattern matched - new complexity = " + this->complexity.to_string());

			return;
		}
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
		{
			Logger::info("Trying to match pattern do { } while (const)");

			auto exprAst = dyn_cast<Expr>(this->expr->getAstNode());
			if (!exprAst) {
				Logger::info("Invalid loop expr");
				return;
			}

			bool result;
			if (exprAst->isValueDependent() || !exprAst->EvaluateAsBooleanCondition(result, astCtx, true)) {
				Logger::info("Non constant expr");
				return;
			}

			if (result)
				this->complexity = ControlFlowCycleComplexity::InfiniteTimes();
			else
				this->complexity = ControlFlowCycleComplexity::OneTime();

			Logger::info("Pattern matched - new complexity = " + this->complexity.to_string());

			return;
		}
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
			Logger::info("Trying to match pattern for(/*any*/; ; /* any */)");

			if (this->getExpr() && this->getExpr()->getAstNode()) {
				Logger::info("Condition exists");
				goto empty_cond_check_end;
			}

			Logger::info("Patern matched successfully");
			this->complexity = ControlFlowCycleComplexity::InfiniteTimes();
			Logger::info("New complexity = " + this->complexity.to_string());
			return;
		}
		empty_cond_check_end:
		
		
		{
			Logger::info("Trying to match pattern for(/*any*/; const ; /*any*/)");

			if (!this->getExpr() || !this->getExpr()->getAstNode()) {
				Logger::info("Empty AST node");
				goto constant_cond_check_end;
			}

			auto exprAst = dyn_cast<Expr>(this->expr->getAstNode());
			if (!exprAst) {
				Logger::info("Invalid loop expr");
				goto constant_cond_check_end;
			}

			bool result;
			if (exprAst->isValueDependent() || !exprAst->EvaluateAsBooleanCondition(result, astCtx, true)) {
				Logger::info("Non constant expr");
				goto constant_cond_check_end;
			}

			if (result)
				this->complexity = ControlFlowCycleComplexity::InfiniteTimes();
			else
				this->complexity = ControlFlowCycleComplexity::ZeroTimes();

			Logger::info("Patern matched successfully"); 
			Logger::info("New complexity = " + this->complexity.to_string());
		}
		constant_cond_check_end:
		
		
		
		{
			Logger::info("Trying to match pattern for(intVar = const /* or 'int intVar = const' */; intVar < const /* or 'intVar <= const' */; ++intVar)");

			if (!this->getExpr() || !this->getInc() || !this->getInit()) {
				Logger::info("Empty expression or inc or init");
				goto constant_iteration_check_end;
			}

			// ensure middle expresiion is "<"
			auto expr = dyn_cast<Expr>(this->getExpr()->getAstNode());
			expr = expr->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto binaryExpr = dyn_cast<BinaryOperator>(expr);
			if (!binaryExpr || (binaryExpr->getOpcode() != BinaryOperatorKind::BO_LT && binaryExpr->getOpcode() != BinaryOperatorKind::BO_LE)) {
				Logger::info("Middle expression is not '<' or '<='");
				goto constant_iteration_check_end;
			}				
			
			// ensure expression right part is int constant 
			Expr::EvalResult Result;
			auto isRightConst = !binaryExpr->getRHS()->isValueDependent() && binaryExpr->getRHS()->EvaluateAsInt(Result, astCtx);
			if (!isRightConst) {
				Logger::info("Couldnt evaluate right part of '<'('<=') operator");
				goto constant_iteration_check_end;
			}
			auto rightValue = Result.Val.getInt().getExtValue();

			// ensure expression left part is integer variable
			auto varExpr = dyn_cast<DeclRefExpr>(binaryExpr->getLHS()->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts());
			if (!varExpr || !varExpr->getDecl()->getType().getTypePtr()->isIntegerType()) {
				Logger::info("Couldnt evaluate left part '<'('<=') or value isnt integer");
				goto constant_iteration_check_end;
			}

			// trying to evaluate var initial value 			
			auto vardeclFromExpr = dyn_cast<VarDecl>(varExpr->getDecl());
			uint64_t variableInitValue;
			// 1) first option - cycle init stmt contains cycle var declaration
			if (auto declStmt = dyn_cast<DeclStmt>(this->getInit()->getAstNode()))
			{
				bool containsVarDecl = false;
				for (auto childDecl : declStmt->getDeclGroup())
				{
					containsVarDecl = containsVarDecl || (vardeclFromExpr == childDecl);
				}
				if (!containsVarDecl) {
					Logger::info("No loop variable declaration found");
					goto constant_iteration_check_end;
				}

				auto isVarEvaluated = vardeclFromExpr->getInit() && !vardeclFromExpr->getInit()->isValueDependent() && vardeclFromExpr->getInit()->EvaluateAsInt(Result, astCtx);
				if (!isVarEvaluated) {
					Logger::info("Couldnt find var inital value");
					goto constant_iteration_check_end;
				}
				variableInitValue = Result.Val.getInt().getExtValue();
			}
			// 2) second option - cycle contains cycle-var assisgment(s)
			else if (auto binaryExpr = dyn_cast<BinaryOperator>(this->getInit()->getAstNode()))
			{
				vector<BinaryOperator*> assigments;
				if (binaryExpr->getOpcode() == BinaryOperatorKind::BO_Assign) {
					assigments.push_back(binaryExpr);
				} else {
					auto temp = binaryExpr;
					while (temp && temp->getOpcode() == BinaryOperatorKind::BO_Comma) {
						auto castedRight = dyn_cast<BinaryOperator>(temp->getRHS());
						if (castedRight && castedRight->getOpcode() == BinaryOperatorKind::BO_Assign) {
							assigments.push_back(castedRight);
						}
						auto castedLeft = dyn_cast<BinaryOperator>(temp->getLHS());
						if (castedLeft && castedLeft->getOpcode() == BinaryOperatorKind::BO_Assign) {
							assigments.push_back(castedLeft);
						}
						temp = castedLeft;
					}
				}

				if (assigments.size() == 0) {
					Logger::info("No var assigments found");
					goto constant_iteration_check_end;
				} else {
					Logger::info("Found " + to_string(assigments.size()) + " assigments");
				}

				bool isFound = false;
				for (auto assgmgnt : assigments) {
					auto assLeft = dyn_cast<DeclRefExpr>(assgmgnt->getLHS()->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts());
					if (assLeft->getDecl() != varExpr->getDecl())
						continue;

					Logger::info("Found var init assigment");
					isFound = true;

					auto isRightPartEvaluated = assgmgnt->getRHS() && !assgmgnt->getRHS()->isValueDependent() && assgmgnt->getRHS()->EvaluateAsInt(Result, astCtx);
					if (!isRightPartEvaluated) {
						Logger::info("Couldnt evaluate right part of assigment");
						goto constant_iteration_check_end;
					}
					variableInitValue = Result.Val.getInt().getExtValue();
					break;
				}
				
				if (!isFound) {
					Logger::info("Couldnt find cycle var assigment");
					goto constant_iteration_check_end;
				}
			}

			// ensure last expression is increment
			auto incExpressionAstNode = dyn_cast<Expr>(this->getInc()->getAstNode())->IgnoreImplicit()->IgnoreImplicitAsWritten()->IgnoreImpCasts()->IgnoreParens();
			auto incExpression = dyn_cast<UnaryOperator>(incExpressionAstNode);
			if (!incExpression || incExpression->getOpcode() != UnaryOperatorKind::UO_PostInc && incExpression->getOpcode() != UnaryOperatorKind::UO_PreInc) {
				Logger::info("Last expression isn't increment");
				goto constant_iteration_check_end;
			}

			Logger::info("Pattern matched");

			if (variableInitValue < rightValue)
				complexity = ControlFlowCycleComplexity::NTimes(variableInitValue, true, rightValue, binaryExpr->getOpcode() == BinaryOperatorKind::BO_LE);
			else
				complexity = ControlFlowCycleComplexity::ZeroTimes();
		
			Logger::info("New complexity - " + complexity.to_string());

			return;		
		}
		constant_iteration_check_end:


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

class ControlFlowDomainBreakStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainBreakStmtNode(BreakStmt* astNode)
		: ControlFlowDomainStmtNode(astNode)
	{
	}
	~ControlFlowDomainBreakStmtNode()
	{		
	}
};

class ControlFlowDomainContinueStmtNode : public ControlFlowDomainStmtNode
{
public:
	ControlFlowDomainContinueStmtNode(ContinueStmt* astNode)
		: ControlFlowDomainStmtNode(astNode)
	{
	}
	~ControlFlowDomainContinueStmtNode()
	{
	}
};


class ControlFlowDomainFuncDeclNode;
struct ControlFlowDomainFuncDeclNodeHash {
	size_t operator() (ControlFlowDomainFuncDeclNode* const& c) const;
};
struct ControlFlowDomainFuncDeclNodeEq {
	bool operator () (ControlFlowDomainFuncDeclNode* const& lhs, ControlFlowDomainFuncDeclNode* const& rhs) const;
};
#define ControlFlowDomainFuncDeclNodeMap std::unordered_map<int, ControlFlowDomainFuncDeclNode*>
#define ControlFlowDomainFuncDeclNodeSet std::unordered_set<ControlFlowDomainFuncDeclNode*, ControlFlowDomainFuncDeclNodeHash, ControlFlowDomainFuncDeclNodeEq>
class ControlFlowDomainFuncDeclNode
{
public:
	ControlFlowDomainFuncDeclNode(FunctionDecl* astNode, ControlFlowDomainStmtNode* body, ControlFlowDomainFuncDeclNodeMap& calledFunctions)
		: astNode(astNode), body(body), calledFunctions(calledFunctions)
	{
	}
	~ControlFlowDomainFuncDeclNode()
	{
		if (this->body)
			delete this->body;
		// TODO mey be deleted twice
		//for (auto func : this->calledFunctions)
		//	delete func; 
	}

	ControlFlowDomainStmtNode* getBody() { return this->body; }

	FunctionDecl* getAstNode() { return this->astNode; }

	ControlFlowDomainFuncDeclNodeMap& getCalledFunctions() { return this->calledFunctions; }

private:
	ControlFlowDomainStmtNode* body;
	ControlFlowDomainFuncDeclNodeMap calledFunctions;
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

class ControlFlowDomainAlgo
{

public:
	ControlFlowDomainAlgo(ControlFlowDomainFuncDeclNodeMap& functions, ControlFlowDomainFuncDeclNode* root)
		: functions(functions), root(root) {
	}
	virtual ~ControlFlowDomainAlgo() {
		for (auto [_, x] : this->functions) {
			delete x;
		}
	}

	ControlFlowDomainFuncDeclNode* getRoot() { return this->root; }

	ControlFlowDomainFuncDeclNodeMap& getFunctions() {
		return this->functions;
	}

private:
	ControlFlowDomainFuncDeclNodeMap functions;
	ControlFlowDomainFuncDeclNode* root = nullptr;
};



