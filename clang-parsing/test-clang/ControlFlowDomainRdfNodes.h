#pragma once
#include <string>
#include <vector>
#include <iostream>
#include "helpers.h"
#include "ControlFlowCycleComplexity.h"

using namespace std;

class ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainRdfNode(string nodeNamePrefix, int id)
		: id(id) {
		this->nodeName = nodeNamePrefix + "_" + to_string(id);
		this->nodeRef = "<" + ControlFlowDomainRdfNode::uri + this->nodeName + ">";
	}

	virtual ~ControlFlowDomainRdfNode()	{
	}

	string toString() {
		stringstream ss;
		this->toString(ss);
		return ss.str();
	}

	virtual void toString(stringstream& ss) = 0;

	string& getNodeName() {
		return this->nodeName;
	}

	string& getNodeRef() {
		return this->nodeRef;
	}

protected:
	inline static string type = "owl:NamedIndividual";
	inline static string uri = "http://vstu.ru/poas/code#";

	int id;

private:
	string nodeRef;
	string nodeName;
};


class ControlFlowDomainLinkedRdfNode : public ControlFlowDomainRdfNode
{
public:
	ControlFlowDomainLinkedRdfNode(string nodeNamePrefix, int id)
		: ControlFlowDomainRdfNode(nodeNamePrefix, id)
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
		: ControlFlowDomainLinkedRdfNode("B" /* aka block */, id), body(body)
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
		ss << string(attributesOffest, ' ') << ":body_item " << this->getBody()[0]->getNodeRef() << (this->body.size() == 1 ? " ;\n" : " ,\n");
		for (int i = 1; i < this->getBody().size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->getBody()[i]->getNodeRef();
			ss << ((i != this->getBody().size() - 1) ? " ,\n" : " ;\n");
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
		ss << string(attributesOffest, ' ') << ":algorithm_name \"" << turtleStringEncode(this->algorithmName) << "\"^^xsd:string; \n";
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
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << turtleStringEncode(this->text) << "\"^^xsd:string .\n";
	}

	string& getText() {
		return text;
	}

private:
	string text;
};





class ControlFlowDomainStmtRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainStmtRdfNode(int id, string text, vector<string> additionalClasses = {})
		: ControlFlowDomainLinkedRdfNode("stmt", id), text(text), additionalClasses(additionalClasses)
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
		for (auto& cl : additionalClasses) {
			ss << string(attributesOffest + 4, ' ') << cl << " \n";
		}
		ss << string(attributesOffest + 4, ' ') << ":stmt ;\n";		
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << turtleStringEncode(this->text) << "\"^^xsd:string .\n";
	}

protected:
	string text;
	vector<string> additionalClasses;
};


class ControlFlowDomainCycleRdfNode : public ControlFlowDomainLinkedRdfNode
{
public:
	ControlFlowDomainCycleRdfNode(int id, ControlFlowCycleComplexity complexity, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainLinkedRdfNode("L" /* aka loop */, id), complexity(complexity), body(body)
	{

	}

	~ControlFlowDomainCycleRdfNode() {
		if (this->body)
			delete this->body;
	}

	ControlFlowCycleComplexity getComplexity() {
		return complexity;
	}

	ControlFlowDomainSequenceRdfNode* getBody() {
		return body;
	}

private:
	ControlFlowCycleComplexity complexity;
	ControlFlowDomainSequenceRdfNode* body;
};



class ControlFlowDomainDoWhileRdfNode : public ControlFlowDomainCycleRdfNode
{
public:
	ControlFlowDomainDoWhileRdfNode(int id, ControlFlowCycleComplexity complexity, ControlFlowDomainExprRdfNode* expr, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainCycleRdfNode(id, complexity, body), expr(expr)
	{
	}
	~ControlFlowDomainDoWhileRdfNode()
	{
		if (this->expr)
			delete this->expr;		
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
		ss << string(attributesOffest, ' ') << ":body " << this->getBody()->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":loop_complexity \"" << this->getComplexity().to_string() << "\"^^xsd:string ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		this->expr->toString(ss);
		this->getBody()->toString(ss);
	}

private:
	ControlFlowDomainExprRdfNode* expr;
};


class ControlFlowDomainWhileDoRdfNode : public ControlFlowDomainCycleRdfNode
{
public:
	ControlFlowDomainWhileDoRdfNode(int id, ControlFlowCycleComplexity complexity, ControlFlowDomainExprRdfNode* expr, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainCycleRdfNode(id, complexity, body), expr(expr)
	{
	}
	~ControlFlowDomainWhileDoRdfNode()
	{
		if (this->expr)
			delete this->expr;
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
		ss << string(attributesOffest, ' ') << ":body " << this->getBody()->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":loop_complexity \"" << this->getComplexity().to_string() << "\"^^xsd:string ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		this->expr->toString(ss);
		this->getBody()->toString(ss);
	}

private:
	ControlFlowDomainExprRdfNode* expr;
};


class ControlFlowDomainForRdfNode : public ControlFlowDomainCycleRdfNode
{
public:
	ControlFlowDomainForRdfNode(int id, ControlFlowCycleComplexity complexity, ControlFlowDomainStmtRdfNode* init,	ControlFlowDomainExprRdfNode* expr, ControlFlowDomainStmtRdfNode* inc, ControlFlowDomainSequenceRdfNode* body)
		: ControlFlowDomainCycleRdfNode(id, complexity, body), init(init), expr(expr), inc(inc)
	{
	}
	~ControlFlowDomainForRdfNode()
	{
		if (this->init)
			delete this->init;
		if (this->expr)
			delete this->expr;
		if (this->inc)
			delete this->inc;
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
		ss << string(attributesOffest + 4, ' ') << ":for_loop ;\n";
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":body " << this->getBody()->getNodeRef() << " ;\n";
		if (this->init)
			ss << string(attributesOffest, ' ') << ":init " << this->init->getNodeRef() << " ;\n";
		if (this->expr)
			ss << string(attributesOffest, ' ') << ":cond " << this->expr->getNodeRef() << " ;\n";
		if (this->inc)
			ss << string(attributesOffest, ' ') << ":update " << this->inc->getNodeRef() << " ;\n";
		ss << string(attributesOffest, ' ') << ":loop_complexity \"" << this->getComplexity().to_string() << "\"^^xsd:string ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << this->getNodeName() << "\"^^xsd:string .\n";

		if (this->init)
			this->init->toString(ss);
		if (this->expr)
			this->expr->toString(ss);
		if (this->inc)
			this->inc->toString(ss);
		this->getBody()->toString(ss);
	}

private:
	ControlFlowDomainStmtRdfNode* init;
	ControlFlowDomainExprRdfNode* expr;
	ControlFlowDomainStmtRdfNode* inc;
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
		: ControlFlowDomainLinkedRdfNode("A" /* aka alternative */, id), alternatives(alternatives)
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
		ss << string(attributesOffest, ' ') << ":branches_item " << this->alternatives[0]->getNodeRef() << (this->alternatives.size() == 1 ? " ;\n" : " ,\n");
		for (int i = 1; i < this->alternatives.size(); ++i)
		{
			ss << string(attributesOffest + 15, ' ') << this->alternatives[i]->getNodeRef();
			ss << ((i != this->alternatives.size() - 1) ? " ,\n" : " ;\n");
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
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << (this->body.size() == 1 ? " ;\n" : " ,\n");
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " ,\n" : " ;\n");
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
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << (this->body.size() == 1 ? " ;\n" : " ,\n");
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " ,\n" : " ;\n");
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
		ss << string(attributesOffest, ' ') << ":body_item " << this->body[0]->getNodeRef() << (this->body.size() == 1 ? " ;\n" : " ,\n");
		for (int i = 1; i < this->body.size(); ++i)
		{
			ss << string(attributesOffest + 11, ' ') << this->body[i]->getNodeRef();
			ss << ((i != this->body.size() - 1) ? " ,\n" : " ;\n");
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


class ControlFlowDomainBreakStmtRdfNode : public ControlFlowDomainStmtRdfNode
{
public:
	ControlFlowDomainBreakStmtRdfNode(int id)
		: ControlFlowDomainStmtRdfNode(id, "break", { ":break" })
	{
	}
};

class ControlFlowDomainContinueStmtRdfNode : public ControlFlowDomainStmtRdfNode
{
public:
	ControlFlowDomainContinueStmtRdfNode(int id)
		: ControlFlowDomainStmtRdfNode(id, "continue", { ":continue" })
	{
	}
};

class ControlFlowDomainReturnStmtRdfNode : public ControlFlowDomainStmtRdfNode
{
public:
	ControlFlowDomainReturnStmtRdfNode(int id, string exprText)
		: ControlFlowDomainStmtRdfNode(id, exprText.size() ? ("return " + exprText) : "return", {":return"}), exprText(exprText)
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
		for (auto& cl : additionalClasses) {
			ss << string(attributesOffest + 4, ' ') << cl << " \n";
		}
		ss << string(attributesOffest + 4, ' ') << ":stmt ;\n";		
		if (this->getNext())
			ss << string(attributesOffest, ' ') << ":next " << this->getNext()->getNodeRef() << " ;\n";
		if (this->getIndex() >= 0)
			ss << string(attributesOffest, ' ') << ":item_index " << this->getIndex() << " ;\n";
		ss << string(attributesOffest, ' ') << ":id " << this->id << " ;\n";
		ss << string(attributesOffest, ' ') << ":return_expr \"" << turtleStringEncode(exprText) << "\"^^xsd:string ;\n";
		ss << string(attributesOffest, ' ') << ":stmt_name \"" << turtleStringEncode(this->text) << "\"^^xsd:string .\n";
	}

private:
	string exprText;
};




