#pragma once
#include <string>
#include <vector>
#include <iostream>
#include "helpers.h"

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

	string toString()
	{
		stringstream ss;
		this->toString(ss);
		return ss.str();
	}

	virtual void toString(stringstream& ss) = 0;

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
		index = -1;
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

	int getIndex() { return index; }
	void setIndex(int idx) { index = idx; }

private:
	bool _isFirst;
	bool _isLast;
	int index;
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":linked_list ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":sequence ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body_item " << this->getBody()[0]->getNodeRef() << " \n";
		for (int i = 1; i < this->getBody().size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->getBody()[i]->getNodeRef();
			ss << ((i != this->getBody().size() - 1) ? " \n" : " ;\n");
		}
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		for (auto ch : this->getBody())
		{
			ch->toString(ss);
		}
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":algorithm ;\n";
		ss << string(attributesOffest, ' ') << ":entry_point " << this->getSequence()->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":global_code " << this->getSequence()->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":algorithm_name \"" << xmlEncode(this->algorithmName) << "\"^^xsd:string; \n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		this->getSequence()->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":expr ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << xmlEncode(this->text) << "\"^^xsd:string .\n";
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":stmt ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << xmlEncode(this->text) << "\"^^xsd:string .\n";
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":do_while_loop ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body " << this->body->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		this->expr->toString(ss);
		this->body->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":while_loop ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body " << this->body->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		this->expr->toString(ss);
		this->body->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":linked_list ,\n";
		ss << string(attributesOffest + 4, ' ') << ":alternative ;\n";
		
		
		ss << string(attributesOffest, ' ') << ":branches_item " << this->alternatives[0]->getNodeRef() << " \n";
		for (int i = 1; i < this->alternatives.size(); ++i)
		{
			ss << string(attributesOffest + 15, ' ') << this->alternatives[i]->getNodeRef();
			ss << ((i != this->alternatives.size() - 1) ? " \n" : " ;\n");
		}
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		for (auto br : alternatives)
		{
			br->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":linked_list ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":if ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << " \n";
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " \n" : " ;\n");
		}
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		expr->toString(ss);
		for (auto ch : this->body)
		{
			ch->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":linked_list ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":else-if ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << " \n";
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " \n" : " ;\n");
		}
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		expr->toString(ss);
		for (auto ch : this->body)
		{
			ch->toString(ss);
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

	virtual void toString(stringstream& ss)
	{
		auto nodeRef = this->getNodeRef();
		auto attributesOffest = nodeRef.size() + 1;

		ss << "\n";
		ss << this->getNodeRef() << " rdf:type " << ControlFlowDomainRdfNode::type + " ,\n";
		ss << string(attributesOffest + 4, ' ') << ":linked_list ,\n";
		if (this->isFirst())
			ss << string(attributesOffest + 4, ' ') << ":first_item ,\n";
		if (this->isLast())
			ss << string(attributesOffest + 4, ' ') << ":last_item ,\n";
		ss << string(attributesOffest + 4, ' ') << ":else ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << " \n";
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " \n" : " ;\n");
		}
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		for (auto ch : this->body)
		{
			ch->toString(ss);
		}
	}

private:
	vector<ControlFlowDomainLinkedRdfNode*> body;
};









