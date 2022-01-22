#pragma once
#include <string>
#include <vector>
#include <iostream>
#include <fstream>
#include <format>
#include <chrono>
#include "helpers.h"
#include <locale>

using namespace std;

class LogEntity
{
public:
	string message;
	chrono::system_clock::time_point time;
	char* level;
};

class Logger 
{
public:
	static void info(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevels[0] });
	}

	static void error(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevels[1] });
	}

	static void warn(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevels[2] });
	}

	static void saveAndClear(string outputFilename)
	{
		__try 
		{
			std::ofstream fs(outputFilename);

			for (auto ent : Logger::buffer)
			{
				fs << "[" << getTimeStr(ent.time).c_str() << "] ";
				fs << "[" << ent.level << "] ";
				fs << ent.message << "\n";
			}
		} 
		__finally 
		{
			Logger::buffer.clear();
		}
	}

	static void clear()
	{
		Logger::buffer.clear();
	}

private:
	inline static vector<LogEntity> buffer;

	static constexpr char* LogLevels[]
	{
		"INFO",
		"ERROR",
		"WARNING"
	};
};

//vector<LogEntity> Logger::buffer = {};