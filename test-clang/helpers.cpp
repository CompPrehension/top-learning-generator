#include "helpers.h"
#include <clang/AST/NestedNameSpecifier.h>
#include <clang/Lex/Lexer.h>

/**
 * Gets the portion of the code that corresponds to given SourceRange, including the
 * last token. Returns expanded macros.
 *
 * @see get_source_text_raw()
 */
std::string get_source_text(clang::SourceRange range, const clang::SourceManager& sm) {
    clang::LangOptions lo;

    // NOTE: sm.getSpellingLoc() used in case the range corresponds to a macro/preprocessed source.
    auto start_loc = sm.getSpellingLoc(range.getBegin());
    auto last_token_loc = sm.getSpellingLoc(range.getEnd());
    auto end_loc = clang::Lexer::getLocForEndOfToken(last_token_loc, 0, sm, lo);
    auto printable_range = clang::SourceRange{ start_loc, end_loc };
    return get_source_text_raw(printable_range, sm);
}

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
std::string get_source_text_raw(clang::SourceRange range, const clang::SourceManager& sm) {
    return clang::Lexer::getSourceText(clang::CharSourceRange::getCharRange(range), sm, clang::LangOptions()).str();
}

std::string get_source_text_raw_tr(clang::SourceRange range, const clang::SourceManager& sm) {
    return clang::Lexer::getSourceText(clang::CharSourceRange::getTokenRange(range), sm, clang::LangOptions()).str();
}

string stringReplace(const string& source, const string& toReplace, const string& replaceWith)
{
    size_t pos = 0;
    size_t cursor = 0;
    int repLen = toReplace.length();
    stringstream builder;

    do
    {
        pos = source.find(toReplace, cursor);

        if (string::npos != pos)
        {
            //copy up to the match, then append the replacement
            builder << source.substr(cursor, pos - cursor);
            builder << replaceWith;

            // skip past the match 
            cursor = pos + repLen;
        }
    } while (string::npos != pos);

    //copy the remainder
    builder << source.substr(cursor);

    return (builder.str());
}

string removeNewLines(const string& source)
{
    return stringReplace(stringReplace(source, "\n", ""), "\r", "");
}

std::regex re("\\s{2,}");
string removeMultipleSpaces(const string& source)
{
    stringstream builder;
    std::regex_replace(std::ostreambuf_iterator<char>(builder), source.begin(), source.end(), re, " ");
    return builder.str();
}

std::string xmlEncode(std::string& data) {
    std::string buffer;
    for (size_t pos = 0; pos != data.size(); ++pos) {
        switch (data[pos]) {
        case '&':  buffer.append("&amp;");       break;
        case '\"': buffer.append("&quot;");      break;
        case '\'': buffer.append("&apos;");      break;
        case '<':  buffer.append("&lt;");        break;
        case '>':  buffer.append("&gt;");        break;
        default:   buffer.append(&data[pos], 1); break;
        }
    }
    return buffer;
}
