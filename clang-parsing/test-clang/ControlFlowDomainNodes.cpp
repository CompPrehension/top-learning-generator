#include "ControlFlowDomainNodes.h"

size_t ControlFlowDomainFuncDeclNodeHash::operator() (ControlFlowDomainFuncDeclNode* const& c) const {
	return std::hash<int>()(c->getAstNode()->getID());
}

bool ControlFlowDomainFuncDeclNodeEq::operator () (ControlFlowDomainFuncDeclNode* const& lhs, ControlFlowDomainFuncDeclNode* const& rhs) const {
	return lhs->getAstNode()->getID() == rhs->getAstNode()->getID();
}
