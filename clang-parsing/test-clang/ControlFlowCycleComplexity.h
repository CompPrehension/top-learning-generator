#pragma once

#include "enum.h"
#include <string>

using namespace std;

BETTER_ENUM(ControlFlowCycleComplexityType, int, Undefined, NTimes, NonZeroTimes, ZeroTimes, InfiniteTimes)

class ControlFlowCycleComplexity
{
public:
	static ControlFlowCycleComplexity Undefined() {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::Undefined);
	}
	static ControlFlowCycleComplexity NTimes(int times) {
		return ControlFlowCycleComplexity(ControlFlowCycleComplexityType::NTimes, times);
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
			return string(type._to_string()) + " " + ::to_string(valueForNTimes);
		}
		return string(type._to_string());
	}


private:
	ControlFlowCycleComplexity(ControlFlowCycleComplexityType type, int valueForNTimes = -1)	
		: type(type), valueForNTimes(valueForNTimes)
	{
	}


	ControlFlowCycleComplexityType type;
	int valueForNTimes;
};


//
