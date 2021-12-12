// Declares clang::SyntaxOnlyAction.
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
            return;
            ExpressionDomainNode* dstNode = NULL;
            __try {
                dstNode = mapToDst(node, Result.SourceManager);

                if (!isValidNode(dstNode))
                    return;

                //std::cout << dstNode->toString();
                //std::cout << "\n";
                auto s = get_source_text_raw(node->getSourceRange(), *Result.SourceManager);

                auto stringRepr = dstNode->toString();
                auto rdfTree = mapToExressionDomainRdfNodes(dstNode);
                auto rdfString = rdfTreeToString(stringRepr, rdfTree);

                cout << stringRepr << endl;

                //string filename = "C:\\Users\\Admin\\Desktop\\test-clang\\test-clang\\output\\expression_" + to_string(++counter) + ".rdf";
                //std::ofstream file(filename);
                //file << rdfString;

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


                auto time = std::time(0);
                auto algoName = to_string(++counter) + string("__") + dstNode->getAstNode()->getDeclName().getAsString() + string("__") + to_string(time);
                rdfNode = mapToRdfNode(algoName, dstNode, *Result.SourceManager);
                auto rdfString = ((ControlFlowDomainRdfNode*)rdfNode)->toString();


                std::cout << rdfString;

                
                string filename = "C:\\Users\\Admin\\Desktop\\test-clang\\test-clang\\cntrflowoutput\\" + algoName + ".rdf";
                std::ofstream file(filename);
                file << "# Original function\n";
                file << "# " << stringReplace(stringReplace(stringReplace(originalCode, "\r\n", "\n"), "\n\r", "\n"), "\n", "\n# ");
                file << "\n\n";
                file << "# Normalized function\n";
                file << "# " << stringReplace(normalizedCode, "\n", "\n# ");
                file << "\n\n";
                file << "# rdf:\n\n";
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
    Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, cntrlflowDomainMatcher), & Printer);

    return Tool.run(newFrontendActionFactory(&Finder).get());
}
