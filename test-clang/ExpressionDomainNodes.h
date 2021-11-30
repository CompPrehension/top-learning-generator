#pragma once
#include <string>

using namespace std;

class ExpressionDomainNode
{
public:
	virtual ~ExpressionDomainNode()
	{

	}

	virtual void dump(int level = 0) = 0;
};


class ExpressionDomainEmptyNode : public ExpressionDomainNode
{
public:
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "EmptyNode" << "\n";
	}
};


class ExpressionBinaryOperatorNode : public ExpressionDomainNode
{
public:
	ExpressionBinaryOperatorNode(string type, ExpressionDomainNode* left, ExpressionDomainNode* right) 
		: type(type), leftChild(left), rightChild(right)
	{
	}
	~ExpressionBinaryOperatorNode()
	{
		delete this->leftChild;
		delete this->rightChild;
	}

	string& getType() { return this->type; }
	ExpressionDomainNode* getLeftChild() { return this->leftChild; }
	ExpressionDomainNode* getRightChild() { return this->rightChild; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "BinaryOperator" << " " << this->type << " " << "\n";
		this->leftChild->dump(level + 1);
		this->rightChild->dump(level + 1);
	}

private:
	string type;
	ExpressionDomainNode* leftChild;
	ExpressionDomainNode* rightChild;
};

class ExpressionUnaryOperatorNode : public ExpressionDomainNode
{
public:
	ExpressionUnaryOperatorNode(string type, ExpressionDomainNode* child)
		: type(type), child(child)
	{
	}
	~ExpressionUnaryOperatorNode()
	{
		delete this->child;
	}

	string& getType() { return this->type; }
	ExpressionDomainNode* getChild() { return this->child; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "UnaryOperator" << " " << this->type << " " << "\n";
		this->child->dump(level + 1);
	}

private:
	string type;
	ExpressionDomainNode* child;
};


class ExpressionVarNode : public ExpressionDomainNode
{
public:
	ExpressionVarNode(string name, ExpressionDomainNode* init)
		: name(name), init(init)
	{
	}
	~ExpressionVarNode()
	{
		delete this->init;
	}

	ExpressionDomainNode* getInit() { return this->init; }
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "Var" << " " << this->name << " with initial value:" << "\n";
		this->init->dump(level + 1);
	}

private:
	string name;
	ExpressionDomainNode* init;
};


class ExpressionFuncCallNode : public ExpressionDomainNode
{
public:
	ExpressionFuncCallNode(string name, vector<ExpressionDomainNode*> args)
		: name(name), args(args)
	{
	}
	~ExpressionFuncCallNode()
	{
		for (auto* arg : this->args)
		{
			delete arg;
		}
	}
	
	void dump(int level = 0)
	{
		llvm::outs() << string(level, ' ') << "FuncCall" << " " << this->name << " with args value:" << "\n";
		for (auto* arg : this->args)
		{
			arg->dump(level + 1);
		}
	}

private:
	string name;
	vector<ExpressionDomainNode*> args;
};


class ExpressionConstNode : public ExpressionDomainNode
{
public:
	ExpressionConstNode(string value)
		: value(value)
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



