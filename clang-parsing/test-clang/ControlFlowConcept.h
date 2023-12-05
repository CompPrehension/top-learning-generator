#pragma once

#include "enum.h"
#include <string>
#include <strstream>

using namespace std;

BETTER_ENUM(ControlFlowConcept, int, Array, Pointer, ClassMemberAccess, FuncCall, ExplicitCast);

struct ControlFlowConceptHash
{
    size_t operator()(const ControlFlowConcept& point) const
    {
        return std::hash<int>()(point);
    }
};
#define ControlFlowConceptsSet unordered_set<ControlFlowConcept, ControlFlowConceptHash>

inline string toRdfString(ControlFlowConcept cfConcept) {
    switch (cfConcept) {
        case ControlFlowConcept::Array:
            return "expr:array";
        case ControlFlowConcept::Pointer:
            return "expr:pointer";
        case ControlFlowConcept::ClassMemberAccess:
            return "expr:class_member_access";
        case ControlFlowConcept::FuncCall:
            return "expr:func_call";
        case ControlFlowConcept::ExplicitCast:
            return "expr:explicit_cast";
    }
    return cfConcept._to_string();
}
