#pragma once
#include <string>
#include <sstream>
#include "helpers.h"

using namespace std;


class ExpressionDomainRdfNode
{
public:
	ExpressionDomainRdfNode(string tokenType, string text, int index) 
		: tokenType(tokenType), text(text), index(index)
	{
	}

	string toString()
	{
		std::stringstream ss;
		auto nodeTag = "<" + ExpressionDomainRdfNode::uri + "#" + "op__0__" + to_string(index) + ">";
		int spaces = nodeTag.size() + 4;

		ss << nodeTag << " rdf:type " << ExpressionDomainRdfNode::type << " ;" << "\n";
		if (isFirst)
			ss << string(spaces, ' ') << ":first \"true\"^^xsd:boolean ;" << "\n";
		if (isLast)
			ss << string(spaces, ' ') << ":last \"true\"^^xsd:boolean ;" << "\n";
		ss << string(spaces, ' ') << ":index " << "\"" << index << "\"" << "^^xsd:integer ;" << "\n";
		ss << string(spaces, ' ') << ":text " << "\"" << turtleStringEncode(text) << "\"" << "^^xsd:string ;" << "\n";
		ss << string(spaces, ' ') << ":token_type " << "\"" << tokenType << "\"" << "^^xsd:string ." ;
		return ss.str();
	}

	void setIsFirst() 
	{
		this->isFirst = true;
	}

	void setIsLast()
	{
		this->isLast = true;
	}

private:
	inline static string type = "owl:NamedIndividual";
	inline static string uri = "http://vstu.ru/poas/code";

	string text;
	int index;
	string tokenType;
	bool isFirst = false;
	bool isLast = false;
};