#pragma once

#include <string>
#include <clang/Basic/SourceLocation.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/AST/NestedNameSpecifier.h>
#include <clang/Lex/Lexer.h>
#include <string>
#include <sstream>
#include <regex>


#include <string>
#include <iostream>
#include <filesystem>
#include <chrono>

using namespace std;
namespace fs = std::filesystem;

using std::string;
using std::stringstream;

/**
 * Gets the portion of the code that corresponds to given SourceRange, including the
 * last token. Returns expanded macros.
 *
 * @see get_source_text_raw()
 */
std::string get_source_text(clang::SourceRange range, const clang::SourceManager& sm);

/**
 * Gets the portion of the code that corresponds to given SourceRange exactly as
 * the range is given.
 *
 * @warning The end location of the SourceRange returned by some Clang functions
 * (such as clang::Expr::getSourceRange) might actually point to the first character
 * (the "location") of the last token of the expression, rather than the character
 * past-the-end of the expression like clang::Lexer::getSourceText expects.
 * get_source_text_raw() does not take this into account. Use get_source_text()
 * instead if you want to get the source text including the last token.
 *
 * @warning This function does not obtain the source of a macro/preprocessor expansion.
 * Use get_source_text() for that.
 */
std::string get_source_text_raw(clang::SourceRange range, const clang::SourceManager& sm);

std::string get_source_text_raw_tr(clang::SourceRange range, const clang::SourceManager& sm);


string stringRegexReplace(const string& source, const string& regex, const string& replaceWith);

string stringReplace(const string& source, const string& toReplace, const string& replaceWith);

string removeNewLines(const string& source);

string removeMultipleSpaces(const string& source);

std::string turtleStringEncode(std::string& data);

bool fileExists(string& pathToDir, string& fileNamePart);
    
std::string getTimeStr(chrono::system_clock::time_point& time);

template <class DstType, class SrcType>
bool IsType(const SrcType* src)
{
    return dynamic_cast<const DstType*>(src) != nullptr;
}
