#pragma once
#include <string>
#include <vector>

using namespace std;

class ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainRdfNode(string tokenType, int id)
		: tokenType(tokenType), id(id)
	{
		this->nodeName = this->tokenType + "__" + to_string(id);
	}

	virtual ~ControlFlowDomainRdfNode()
	{
	}

	virtual void toString(stringstream& ss)
	{

	}

	string getNodeName()
	{
		return this->nodeName;
	}

	string getNodeRef()
	{
		return "<" + ControlFlowDomainRdfNode::uri + getNodeName() + ">";
	}

protected:
	inline static string type = "owl:NamedIndividual";
	inline static string uri = "http://vstu.ru/poas/code#";
	
	int id;
	string nodeName;
	string tokenType;
};


class ControlFlowDomainLinkedRdfNode : public ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainLinkedRdfNode(string tokenType, int id)
		: ControlFlowDomainRdfNode(tokenType, id)
	{
		next = NULL;
		_isFirst = false;
		_isLast = false;
	}

	~ControlFlowDomainLinkedRdfNode()
	{
		// we dont delete next because it will be deleted in seq
	}

	ControlFlowDomainLinkedRdfNode* getNext() { return this->next; }
	void setNext(ControlFlowDomainLinkedRdfNode* next)
	{
		this->next = next;
	}

	bool isFirst() { return _isFirst; }
	void setFirst() { _isFirst = true; }


	bool isLast() { return _isLast; }
	void setLast() { _isLast = true; }

private:
	bool _isFirst;
	bool _isLast;
	ControlFlowDomainLinkedRdfNode* next;
};


class ControlFlowDomainSequenceRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainSequenceRdfNode(int id, vector<ControlFlowDomainLinkedRdfNode*> body)
		: ControlFlowDomainLinkedRdfNode("sequence", id), body(body)
	{

	}
	~ControlFlowDomainSequenceRdfNode()
	{
		for (auto c : this->body)
		{
			if (c)
				delete c;
		}
	}

	vector<ControlFlowDomainLinkedRdfNode*>& getBody()
	{
		return this->body;
	}
	void setBody(vector<ControlFlowDomainLinkedRdfNode*> body)
	{
		this->body = body;
	}

private:
	vector<ControlFlowDomainLinkedRdfNode*> body;
};


class ControlFlowDomainAlgorythmRdfNode : public ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainAlgorythmRdfNode(string algorithmName, int id, ControlFlowDomainSequenceRdfNode* sequence)
		: ControlFlowDomainRdfNode("algorithm", id), sequence(sequence), algorithmName(algorithmName)
	{

	}
	~ControlFlowDomainAlgorythmRdfNode()
	{
		if (this->sequence)
			delete this->sequence;
	}

	ControlFlowDomainSequenceRdfNode* getSequence()
	{
		return this->sequence;
	}

private:
	string algorithmName;
	ControlFlowDomainSequenceRdfNode* sequence;
};


class ControlFlowDomainExprRdfNode : public ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainExprRdfNode(int id, string text)
		: ControlFlowDomainRdfNode("expr", id), text(text)
	{
	}

private:
	string text;
};





class ControlFlowDomainStmtRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainStmtRdfNode(int id, string text)
		: ControlFlowDomainLinkedRdfNode("stmt", id), text(text)
	{
	}
private:
	string text;
};

class ControlFlowDomainDoWhileRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainDoWhileRdfNode(int id, ControlFlowDomainExprRdfNode* expr, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainLinkedRdfNode("do_while_loop", id), expr(expr), body(body)
	{
	}
	~ControlFlowDomainDoWhileRdfNode()
	{
		if (this->expr)
			delete this->expr;
		if (this->body)
			delete this->body;
	}

private:
	ControlFlowDomainExprRdfNode* expr;
	ControlFlowDomainSequenceRdfNode* body;
};


class ControlFlowDomainWhileDoRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainWhileDoRdfNode(int id, ControlFlowDomainExprRdfNode* expr, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainLinkedRdfNode("while_loop", id), expr(expr), body(body)
	{
	}
	~ControlFlowDomainWhileDoRdfNode()
	{
		if (this->expr)
			delete this->expr;
		if (this->body)
			delete this->body;
	}

private:
	ControlFlowDomainExprRdfNode* expr;
	ControlFlowDomainSequenceRdfNode* body;
};



class ControlFlowDomainAlternativeBranchRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainAlternativeBranchRdfNode(string tokenType, int id)
		: ControlFlowDomainLinkedRdfNode(tokenType, id)
	{
	}
};

class ControlFlowDomainAlternativeRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainAlternativeRdfNode(int id, vector<ControlFlowDomainAlternativeBranchRdfNode*> alternatives)
		: ControlFlowDomainLinkedRdfNode("alternative", id), alternatives(alternatives)
	{
	}
	~ControlFlowDomainAlternativeRdfNode()
	{
		for (auto alt : this->alternatives)
		{
			if (alt)
				delete alt;
		}
	}

private:
	vector<ControlFlowDomainAlternativeBranchRdfNode*> alternatives;
};


class ControlFlowDomainAlternativeIfBranchRdfNode : public ControlFlowDomainAlternativeBranchRdfNode
{
public:
	ControlFlowDomainAlternativeIfBranchRdfNode(int id, ControlFlowDomainExprRdfNode* expr, vector<ControlFlowDomainLinkedRdfNode*> body)
		: ControlFlowDomainAlternativeBranchRdfNode("if", id), expr(expr), body(body)
	{
	}

	~ControlFlowDomainAlternativeIfBranchRdfNode()
	{
		if (this->expr)
			delete expr;
		for (auto c : this->body)
		{
			if (c)
				delete c;
		}
	}
private:
	ControlFlowDomainExprRdfNode* expr;
	vector<ControlFlowDomainLinkedRdfNode*> body;
};

class ControlFlowDomainAlternativeElseIfBranchRdfNode : public ControlFlowDomainAlternativeBranchRdfNode
{
public:
	ControlFlowDomainAlternativeElseIfBranchRdfNode(int id, ControlFlowDomainExprRdfNode* expr, vector<ControlFlowDomainLinkedRdfNode*> body)
		: ControlFlowDomainAlternativeBranchRdfNode("else-if", id), expr(expr), body(body)
	{
	}

	~ControlFlowDomainAlternativeElseIfBranchRdfNode()
	{
		if (this->expr)
			delete expr;
		for (auto c : this->body)
		{
			if (c)
				delete c;
		}
	}
private:
	ControlFlowDomainExprRdfNode* expr;
	vector<ControlFlowDomainLinkedRdfNode*> body;
};


class ControlFlowDomainAlternativeElseBranchRdfNode : public ControlFlowDomainAlternativeBranchRdfNode
{
public:
	ControlFlowDomainAlternativeElseBranchRdfNode(int id, vector<ControlFlowDomainLinkedRdfNode*> body)
		: ControlFlowDomainAlternativeBranchRdfNode("else", id), body(body)
	{
	}

	~ControlFlowDomainAlternativeElseBranchRdfNode()
	{
		for (auto c : this->body)
		{
			if (c)
				delete c;
		}
	}
private:
	vector<ControlFlowDomainLinkedRdfNode*> body;
};









