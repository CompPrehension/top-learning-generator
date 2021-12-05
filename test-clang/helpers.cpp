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