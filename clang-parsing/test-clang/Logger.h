#pragma once
#include <string>
#include <vector>
#include <iostream>
#include <fstream>
#include <format>
#include <chrono>
#include "helpers.h"
#include <locale>
#include "enum.h"

using namespace std;

BETTER_ENUM(LogLevel, int, INFO, ERROR,	WARNING)

class LogEntity
{
public:
	string message;
	chrono::system_clock::time_point time;
	LogLevel level;
};

class Logger 
{
public:
	static void info(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevel::INFO });
	}

	static void error(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevel::ERROR });
	}

	static void warn(string msg)
	{
		Logger::buffer.push_back(LogEntity{ msg, chrono::system_clock::now(), LogLevel::WARNING });
	}

	static void saveAndClear(string outputFilename)
	{
		try 
		{
			std::ofstream fs(outputFilename);

			for (auto ent : Logger::buffer)
			{
				fs << "[" << getTimeStr(ent.time).c_str() << "] ";
				fs << "[" << ent.level << "] ";
				fs << ent.message << "\n";
			}
		} 
		catch (...) 
		{
        }
		Logger::buffer.clear();
	}

	static void clear()
	{
		Logger::buffer.clear();
	}

private:
	inline static vector<LogEntity> buffer;
};
