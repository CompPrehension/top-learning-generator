﻿// Declares clang::SyntaxOnlyAction.
#include "clang/Frontend/FrontendActions.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
// Declares llvm::cl::extrahelp.
//#include "llvm/Support/CommandLine.h"
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include <iostream>
#include <fstream>
#include "expression-domain-functions.h"
#include "helpers.h"
#include "cntrl-flow-domain-funtions.h"
#include <ctime>

using namespace clang::tooling;
using namespace clang::ast_matchers;
using namespace llvm;

// Apply a custom category to all command-line options so that they are the
// only ones displayed.
static llvm::cl::OptionCategory MyToolCategory("my-tool options");

// CommonOptionsParser declares HelpMessage with a description of the common
// command-line options related to the compilation database and input files.
// It's nice to have this help message in all tools.
static cl::extrahelp CommonHelp(CommonOptionsParser::HelpMessage);

// A help message for this specific tool can be added afterwards.
static cl::extrahelp MoreHelp("\nMore help text...\n");


class ExprPrinter : public MatchFinder::MatchCallback {
    int counter = 0;
public:
    virtual void run(const MatchFinder::MatchResult& Result) {
        if (auto node = Result.Nodes.getNodeAs<clang::Expr>("exressionDomain"))
        {
            ExpressionDomainNode* dstNode = NULL;
            __try {
                auto rawExpr = get_source_text_raw_tr(node->getSourceRange(), *Result.SourceManager);
                dstNode = mapToDst(node, Result.SourceManager);

                if (!isValidNode(dstNode))
                    return;

                auto normalizedExpressionStr = dstNode->toString();
                auto rdfTree = mapToExressionDomainRdfNodes(dstNode);
                auto rdfString = rdfTreeToString(rdfTree);
                std::cout << normalizedExpressionStr << "\n";

                auto expressionHash = (unsigned long long)std::hash<std::string>()(normalizedExpressionStr);
                auto time = std::time(0);
                auto fileNamePart = stringRegexReplace(normalizedExpressionStr, "[\\\"\\<\\>\\|\\:\\*\\?\\\\\\/]", "_");
                fileNamePart = fileNamePart.substr(0, 50) + string("__") + to_string(expressionHash);
                
                // if file with this name already exists - skip this function
                string outputDir = "C:\\Users\\Admin\\Desktop\\test-clang\\test-clang\\expressionoutput\\";
                if (fileExists(outputDir, fileNamePart))
                {
                    return;
                }

                string filename = outputDir + fileNamePart + "__" + to_string(time) + "__" + ".ttl";
                std::ofstream file(filename);
                file << "# Original expresson\n";
                file << "# " << stringReplace(stringReplace(stringReplace(normalizedExpressionStr, "\r\n", "\n"), "\n\r", "\n"), "\n", "\n# ") << "\n";
                file << "# " << "hash=" << expressionHash << "\n";
                file << "\n\n";               
                file << "# rdf:\n\n";
                file << "@prefix : <http://vstu.ru/poas/code#> ." << "\n";
                file << "@prefix owl: <http://www.w3.org/2002/07/owl#> ." << "\n";
                file << "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ." << "\n";
                file << "@prefix xml: <http://www.w3.org/XML/1998/namespace> ." << "\n";
                file << "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ." << "\n";
                file << "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ." << "\n";
                file << "@base <http://vstu.ru/poas/code> ." << "\n\n";

                file << rdfString << "\n";
            } __finally {
                if (dstNode)
                    delete dstNode;
            }
        }


        if (auto node = Result.Nodes.getNodeAs<clang::FunctionDecl>("cntrlflowDomain"))
        {
            ControlFlowDomainFuncDeclNode* dstNode = NULL;
            ControlFlowDomainAlgorythmRdfNode* rdfNode = NULL;
            __try {
                //node->dump();

                dstNode = mapToControlflowDst((clang::FunctionDecl*)node);
                if (!dstNode)
                    return;

                auto originalCode = toOriginalCppString(dstNode, *Result.SourceManager);
                auto normalizedCode = toCustomCppString(dstNode, *Result.SourceManager, true);
                                
                std::cout << "\n\n\n\n\n";                
                std::cout << originalCode;
                std::cout << "\n\n\n\n\n";
                std::cout << normalizedCode;
                std::cout << "\n\n\n\n\n";


                auto normalizedCodeHash = (unsigned long long)std::hash<std::string>()(normalizedCode);
                auto time = std::time(0);
                auto functionId = dstNode->getAstNode()->getDeclName().getAsString() + string("__") + to_string(normalizedCodeHash);
                
                // if file with this name already exists - skip this function
                string outputDir = "C:\\Users\\Admin\\Desktop\\test-clang\\test-clang\\cntrflowoutput\\";
                if (fileExists(outputDir, functionId))
                {
                    return;
                }
                
                auto algoName = functionId + string("__") + to_string(time);
                rdfNode = mapToRdfNode(algoName, dstNode, *Result.SourceManager);
                auto rdfString = ((ControlFlowDomainRdfNode*)rdfNode)->toString();

                std::cout << rdfString;
                
                string filename = outputDir + algoName + ".ttl";
                std::ofstream file(filename);
                file << "# Original function\n";
                file << "# " << stringReplace(stringReplace(stringReplace(originalCode, "\r\n", "\n"), "\n\r", "\n"), "\n", "\n# ");
                file << "\n\n";
                file << "# Normalized function\n";
                file << "# " << stringReplace(normalizedCode, "\n", "\n# ");
                file << "\n\n";
                file << "# rdf:\n\n";
                file << "@prefix : <http://vstu.ru/poas/code#> ." << "\n";
                file << "@prefix owl: <http://www.w3.org/2002/07/owl#> ." << "\n";
                file << "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ." << "\n";
                file << "@prefix xml: <http://www.w3.org/XML/1998/namespace> ." << "\n";
                file << "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ." << "\n";
                file << "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ." << "\n";
                file << "@base <http://vstu.ru/poas/code> ." << "\n\n";

                file << rdfString;
            } __finally {
                if (dstNode)
                    delete dstNode;
                if (rdfNode)
                    delete rdfNode;
            }
        }
    }
};



int main(int argc, const char** argv) {
    auto ExpectedParser = CommonOptionsParser::create(argc, argv, MyToolCategory);
    if (!ExpectedParser) {
        // Fail gracefully for unsupported options.
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }
    

    CommonOptionsParser& OptionsParser = ExpectedParser.get();
    ClangTool Tool(OptionsParser.getCompilations(),
        OptionsParser.getSourcePathList());

    auto exressionDomainMatcher = expr(
        anyOf(
            binaryOperator(hasOperatorName("+")),
            binaryOperator(hasOperatorName("-")),
            binaryOperator(hasOperatorName("*")),
            binaryOperator(hasOperatorName("/")),
            unaryOperator(hasOperatorName("-")),
            unaryOperator(hasOperatorName("++")),
            unaryOperator(hasOperatorName("--")),
            binaryOperator(isAssignmentOperator()),
            binaryOperator(isComparisonOperator()),
            cxxMemberCallExpr()
        )
    ).bind("exressionDomain");
    auto cntrlflowDomainMatcher = functionDecl(hasBody(compoundStmt()))
        .bind("cntrlflowDomain");


    ExprPrinter Printer;
    MatchFinder Finder;
    Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, exressionDomainMatcher), &Printer);
    //Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, cntrlflowDomainMatcher), &Printer);

    return Tool.run(newFrontendActionFactory(&Finder).get());
}