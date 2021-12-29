#pragma once
#include <string>
#include "clang/ASTMatchers/ASTMatchers.h"

using namespace std;
using namespace clang;

class ExpressionDomainNode
{
public:
	ExpressionDomainNode(Stmt* astNode)
		: astNode(astNode)
	{		
	}

	virtual ~ExpressionDomainNode()
	{
	}

	virtual void dump(int level = 0) = 0;

	virtual string toString() = 0;	

	Stmt* getAstNode() { return this->astNode; };
private:
	Stmt* astNode;
};


class ExpressionDomainUndefinedNode : public ExpressionDomainNode
{
public:
	ExpressionDomainUndefinedNode(Stmt* astNode)
		: ExpressionDomainNode(astNode)
	{
	}

	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Undefined" << "\n";
	}

	string toString()
	{
		return "<Undefinend node>";
	}
};


class ExpressionDomainBinaryOperatorNode : public ExpressionDomainNode
{
public:
	ExpressionDomainBinaryOperatorNode(clang::BinaryOperator* astNode, string type, ExpressionDomainNode* left, ExpressionDomainNode* right)
		: ExpressionDomainNode(astNode), type(type), leftChild(left), rightChild(right)
	{
		
	}
	virtual ~ExpressionDomainBinaryOperatorNode()
	{
		if (this->leftChild)
			delete this->leftChild;
		if (this->rightChild)
			delete this->rightChild;
	}

	string& getType() { return this->type; }
	ExpressionDomainNode* getLeftChild() { return this->leftChild; }
	ExpressionDomainNode* getRightChild() { return this->rightChild; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "BinaryOperator" << " " << this->type << " " << "\n";
		if (this->leftChild)
			this->leftChild->dump(level + 1);
		if (this->rightChild)
			this->rightChild->dump(level + 1);
	}

	string toString()
	{
		auto leftPart = this->leftChild ? this->leftChild->toString() : "<undefined>";
		auto rightPart = this->rightChild ? this->rightChild->toString() : "<undefined>";
		return leftPart + " " + this->type + " " + rightPart;
	}

private:
	string type;
	ExpressionDomainNode* leftChild;
	ExpressionDomainNode* rightChild;
};

class ExpressionDomainUnaryOperatorNode : public ExpressionDomainNode
{
public:
	ExpressionDomainUnaryOperatorNode(clang::UnaryOperator* astNode, string type, ExpressionDomainNode* child)
		: ExpressionDomainNode(astNode), type(type), child(child)
	{
		this->opCode = astNode->getOpcode();
	}
	virtual ~ExpressionDomainUnaryOperatorNode()
	{
		if (this->child)
			delete this->child;
	}

	string& getType() { return this->type; }
	ExpressionDomainNode* getChild() { return this->child; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "UnaryOperator" << " " << this->type << " " << "\n";
		if (this->child)
			this->child->dump(level + 1);
	}

	string toString()
	{
		auto isPostfix = ((clang::UnaryOperator*)this->getAstNode())->isPostfix();
		return isPostfix ? this->child->toString() + this->type : this->type + this->child->toString();
	}

	bool isPostfix()
	{
		return ((clang::UnaryOperator*)this->getAstNode())->isPostfix();
	}

private:
	string type;
	ExpressionDomainNode* child;
	UnaryOperatorKind opCode;
};


class ExpressionDomainVarNode : public ExpressionDomainNode
{
public:
	ExpressionDomainVarNode(clang::DeclRefExpr* astNode, string name, ExpressionDomainNode* init)
		: ExpressionDomainNode(astNode), name(name), init(init)
	{
	}
	virtual ~ExpressionDomainVarNode()
	{
		if (this->init)
			delete this->init;
	}

	ExpressionDomainNode* getInit() { return this->init; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Var" << " " << this->name << " with initial value:" << "\n";
		if (this->init)
		{
			llvm::outs() << string(level, ' ') << "with initial value:" << "\n";
			this->init->dump(level + 1);
		}
	}

	string getName()
	{
		return this->name;
	}

	string toString()
	{		
		return this->name;
	}

private:
	string name;
	ExpressionDomainNode* init;
};

/*
class ExpressionDomainExplicitCastNode : public ExpressionDomainNode
{
public:
	ExpressionDomainExplicitCastNode(string name, ExpressionDomainNode* init)
		: name(name), init(init)
	{
	}
	~ExpressionDomainExplicitCastNode()
	{
		delete this->init;
	}

	ExpressionDomainNode* getInit() { return this->init; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "ExplicitCast to" << " " << this->name << " with initial value:" << "\n";
		this->subexpr->dump(level + 1);
	}

private:
	string name;
	ExpressionDomainNode* subexpr;
};
*/


class ExpressionDomainFuncCallNode : public ExpressionDomainNode
{
public:
	ExpressionDomainFuncCallNode(clang::CallExpr* astNode, string name, vector<ExpressionDomainNode*> args)
		: ExpressionDomainNode(astNode), name(name), args(args)
	{
	}
	~ExpressionDomainFuncCallNode()
	{
		for (auto* arg : this->args)
		{
			if (arg)
				delete arg;
		}
	}
	
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "FuncCall" << " " << this->name << " with args value:" << "\n";
		for (auto* arg : this->args)
		{
			if (arg)
				arg->dump(level + 1);
		}
	}

	string toString()
	{
		string argsString;
		for (auto* arg : this->args)
		{
			if (arg)
				argsString += ", " + arg->toString();
		}
		if (argsString.size() > 0)
		{
			argsString = argsString.substr(2);
		}

		return this->name + "(" + argsString + ")";
	}

	vector<ExpressionDomainNode*>& getArgs() 
	{
		return this->args;
	}

	string& getName()
	{
		return this->name;
	}

private:
	string name;
	vector<ExpressionDomainNode*> args;
};


class ExpressionDomainConstNode : public ExpressionDomainNode
{
public:
	ExpressionDomainConstNode(Stmt* astNode, string value)
		: ExpressionDomainNode(astNode), value(value)
	{
	}

	string& getValue() { return this->value; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Const" << " " << this->value << " " << "\n";
	}

	string toString()
	{
		return this->value;
	}

private:
	string value;
};


class ExpressionDomainParenExprNode : public ExpressionDomainNode
{
public:
	ExpressionDomainParenExprNode(clang::ParenExpr* astNode, ExpressionDomainNode* expr)
		: ExpressionDomainNode(astNode), expr(expr)
	{
	}
	~ExpressionDomainParenExprNode() 
	{
		if (expr)
			delete expr;
	}

	ExpressionDomainNode* getExpr() { return this->expr; }

	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "ParenExpr " << "\n";
		if (this->expr)
			this->expr->dump(level + 1);
	}

	string toString()
	{
		auto exprS = this->expr->toString();
		return "(" + exprS + ")";
	}

private:
	ExpressionDomainNode* expr;
};

class ExpressionDomainMemberExprNode : public ExpressionDomainNode
{
public:
	ExpressionDomainMemberExprNode(MemberExpr* astNode, ExpressionDomainNode* leftValue, string rightValue)
		: ExpressionDomainNode(astNode), leftValue(leftValue), rightValue(rightValue)
	{
	}
	~ExpressionDomainMemberExprNode()
	{
		if (leftValue)
			delete leftValue;
	}

	//string& getValue() { return this->value; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Member expr from " << "\n";
		if (this->leftValue)
			this->leftValue->dump(level + 1);
		llvm::outs() << string(level, ' ') << " to " << this->rightValue << "\n";
	}

	ExpressionDomainNode* getLeftValue() 
	{
		return this->leftValue;
	}

	string& getRightValue()
	{
		return this->rightValue;
	}

	string toString()
	{
		auto leftPart = leftValue->toString();
		auto op = this->isArrow() ? "->" : ".";
		// todo fix that
		return leftPart + op + this->rightValue;
	}

	bool isArrow()
	{
		return ((MemberExpr*)this->getAstNode())->isArrow();
	}

private:
	ExpressionDomainNode* leftValue;
	string rightValue;
};


class ExpressionDomainArrayBracketNode : public ExpressionDomainNode
{
public:
	ExpressionDomainArrayBracketNode(ArraySubscriptExpr* astNode, ExpressionDomainNode* arrayExpr, ExpressionDomainNode* indexExpr)
		: ExpressionDomainNode(astNode), arrayExpr(arrayExpr), indexExpr(indexExpr)
	{
	}
	~ExpressionDomainArrayBracketNode()
	{
		if (arrayExpr)
			delete arrayExpr;
		if (indexExpr)
			delete indexExpr;
	}

	//string& getValue() { return this->value; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Array brackets for " << "\n";
		if (this->arrayExpr)
			this->arrayExpr->dump(level + 1);
		llvm::outs() << string(level, ' ') << "index expr" << "\n";
		if (this->indexExpr)
			this->indexExpr->dump(level + 1);
	}

	string toString()
	{
		auto leftPart = this->arrayExpr->toString();
		auto rightPart = this->indexExpr->toString();
		// todo fix that
		return leftPart + "[" + rightPart + "]";
	}

	ExpressionDomainNode* getArrayExpr() { return this->arrayExpr; }
	ExpressionDomainNode* getIndexExpr() { return this->indexExpr; }
private:
	ExpressionDomainNode* arrayExpr;
	ExpressionDomainNode* indexExpr;
};

class ExpressionDomainConditionalOperatorNode : public ExpressionDomainNode
{
public:
	ExpressionDomainConditionalOperatorNode(clang::ConditionalOperator* astNode, ExpressionDomainNode* expr, ExpressionDomainNode* left, ExpressionDomainNode* right)
		: ExpressionDomainNode(astNode), expr(expr), left(left), right(right)
	{
	}
	~ExpressionDomainConditionalOperatorNode()
	{
		if (expr)
			delete expr;
		if (left)
			delete left;
		if (right)
			delete right;
	}

	//string& getValue() { return this->value; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "ternary operator " << "\n";
		if (this->expr)
			this->expr->dump(level + 1);
		llvm::outs() << string(level, ' ') << "left branch" << "\n";
		if (this->left)
			this->left->dump(level + 1);
		llvm::outs() << string(level, ' ') << "right branch" << "\n";
		if (this->right)
			this->right->dump(level + 1);
	}

	string toString()
	{
		auto exprS = this->expr->toString();
		auto leftS = this->left ? this->left->toString() : "";
		auto rightS = this->right ? this->right->toString() : "";
		return exprS + " ? " + leftS + " : " + rightS;
	}

	ExpressionDomainNode* getExpr() { return this->expr; }
	ExpressionDomainNode* getLeft() { return this->left; }
	ExpressionDomainNode* getRight() { return this->right; }
private:
	ExpressionDomainNode* expr;
	ExpressionDomainNode* left;
	ExpressionDomainNode* right;
};


