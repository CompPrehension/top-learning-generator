#pragma once
#include <string>
#include <sstream>

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
		ss << "<" << ExpressionDomainRdfNode::uri << "#" << "op__0__" << index << ">" << " rdf:type " << ExpressionDomainRdfNode::type << " ," << "\n";
		if (isFirst)
			ss << ":first \"true\"^^xsd:boolean ;" << "\n";
		if (isLast)
			ss << ":last \"true\"^^xsd:boolean ;" << "\n";
		ss << ":index " << "\"" << index << "\"" << "^^xsd:integer ;" << "\n";
		ss << ":text " << "\"" << text << "\"" << "^^xsd:string ;" << "\n";
		ss << ":token_type " << "\"" << tokenType << "\"" << "^^xsd:string ." ;
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