#pragma once

#include "enum.h"
#include <string>
#include <strstream>

using namespace std;

BETTER_ENUM(ControlFlowCycleComplexityType, int, Undefined, NTimes, NonZeroTimes, ZeroTimes, InfiniteTimes)

struct Range
{
	int from;
	bool isFromIncluding;
	int to;
	bool isToIncluding;
};

class ControlFlowCycleComplexity
{
public:
	static ControlFlowCycleComplexity Undefined() {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::Undefined);
	}
	static ControlFlowCycleComplexity NTimes(int from, bool isFromIncluding, int to, bool isToIncluding) {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::NTimes, Range{ from, isFromIncluding, to, isToIncluding });
	}
	static ControlFlowCycleComplexity NonZeroTimes() {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::NonZeroTimes);
	}
	static ControlFlowCycleComplexity ZeroTimes() {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::ZeroTimes);
	}
	static ControlFlowCycleComplexity InfiniteTimes() {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::InfiniteTimes);
	}

	string to_string() {
		if (type._to_index() == ControlFlowCycleComplexityType::NTimes)
		{
			stringstream ss;
			ss << type._to_string() << " ";
			ss << (rangeNTimes.isFromIncluding ? "[" : "(");
			ss << ::to_string(rangeNTimes.from) << ",";
			ss << ::to_string(rangeNTimes.to);
			ss << (rangeNTimes.isToIncluding ? "]" : ")");
			return ss.str();
		}
		return string(type._to_string());
	}


private:
	ControlFlowCycleComplexity(ControlFlowCycleComplexityType type, Range rangeNTimes = {})
		: type(type), rangeNTimes(rangeNTimes)
	{
	}


	ControlFlowCycleComplexityType type;
	Range rangeNTimes;
};


//
