#pragma once
#include <string>

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

	vector<ExpressionDomainNode*>& getArgs() 
	{
		return this->args;
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

private:
	string value;
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

	ExpressionDomainNode* getArrayExpr() { return this->arrayExpr; }
	ExpressionDomainNode* getIndexExpr() { return this->indexExpr; }
private:
	ExpressionDomainNode* arrayExpr;
	ExpressionDomainNode* indexExpr;
};


