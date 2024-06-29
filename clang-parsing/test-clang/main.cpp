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
#include "json.hpp"

using namespace clang;
using namespace clang::tooling;
using namespace clang::ast_matchers;
using namespace llvm;
using json = nlohmann::json;

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
private:
    string outputDir;

public:
    ExprPrinter(string outputDir) {
        if (!outputDir.empty() && outputDir.back() != '\\' && outputDir.back() != '/')
            outputDir += '/';
        this->outputDir = outputDir;
    }


    virtual void run(const MatchFinder::MatchResult& Result) {		
        if (auto node = Result.Nodes.getNodeAs<clang::Expr>("exressionDomain"))
        {
            runForExpressionDomain(node, Result);
            return;
        }

        if (auto node = Result.Nodes.getNodeAs<clang::FunctionDecl>("cntrlflowDomain"))
        {
            runForCntrlFlowDomain(node, Result);
            return;
        }
    }

private:
    void runForExpressionDomain(const clang::Expr* node, const MatchFinder::MatchResult& Result) {
        ExpressionDomainNode* dstNode = NULL;
        try {
            auto rawExpr = get_source_text_raw_tr(node->getSourceRange(), *Result.SourceManager);
            dstNode = mapToDst(node, Result.SourceManager);

            if (!isValidNode(dstNode))
                return;

            auto normalizedExpressionStr = dstNode->toString();
            // cout << normalizedExpressionStr << endl;
            auto rdfTree = mapToExressionDomainRdfNodes(dstNode);
            auto rdfString = rdfTreeToString(rdfTree);

            auto expressionHash = stable_hash(normalizedExpressionStr);
            auto time = std::time(0);
            auto fileNamePart = stringRegexReplace(normalizedExpressionStr, "[^a-zA-Z0-9_=+-]", "");
            fileNamePart = fileNamePart.substr(0, 50) + string("__") + to_string(expressionHash);

            // if file with this name already exists - skip this function
            if (fileExists(outputDir, fileNamePart))
            {
                return;
            }

            string filename = outputDir + fileNamePart + "__" + to_string(time) + ".ttl";
            std::ofstream file(filename);
            //file << "# Original expresson\n";
            //file << "# " << stringReplace(stringReplace(stringReplace(rawExpr, "\r\n", "\n"), "\n\r", "\n"), "\n", "\n# ") << "\n";
            file << "# Normalized expression\n";
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
        } catch (const std::bad_cast &badCastEx) {
            std::cerr << badCastEx.what();
		} catch (...) {
			cout << "Unexpected error found" << endl;
			Logger::error("Unexpected error found");
        }
        if (dstNode)
            delete dstNode;
    }

    void runForCntrlFlowDomain(const clang::FunctionDecl* node, const MatchFinder::MatchResult& Result) {
        ControlFlowDomainFuncDeclNode* dstNode = NULL;
        ControlFlowDomainAlgorythmRdfNode* rdfNode = NULL;
        string functionName;
        string shortFilename = "";
        string logsDir = outputDir;
        bool isSuccess = false;

        try {
            functionName = node->getDeclName().getAsString();

            string astNodeDump;
            raw_string_ostream output(astNodeDump);
            node->dump(output);
            //node->dump();

            Logger::info("AST representation:");
            Logger::info(astNodeDump);

            Logger::info("Trying map to dst");
            dstNode = mapToControlflowDst((clang::FunctionDecl*)node, *Result.Context);
            if (!dstNode)
                return;
            Logger::info("Mapped successfully");

            auto originalCode = toOriginalCppString(dstNode, *Result.SourceManager);
            Logger::info("Original code:");
            Logger::info(originalCode);

            auto normalizedCode = toCustomCppString(dstNode, *Result.SourceManager, *Result.Context, true);
			
            Logger::info("Normalized code:");
            Logger::info(normalizedCode);

            // calculate output file name            
            auto normalizedCodeHash = stable_hash(normalizedCode);
            auto functionId = functionName + string("__") + to_string(normalizedCodeHash);

            // if file with this name already exists - skip this function
            if (fileExists(outputDir, functionId))
            {
                goto finally_lbl;
            }

            auto time = std::time(0);
            auto algoName = functionId + string("__") + to_string(time);
            rdfNode = mapToRdfNode(algoName, dstNode, *Result.SourceManager, *Result.Context);
            auto rdfString = ((ControlFlowDomainRdfNode*)rdfNode)->toString();
            Logger::info("Successfully converted to rdf");

            shortFilename = algoName + ".ttl";
            auto absolutePath = outputDir + shortFilename;
            std::ofstream file(absolutePath);
            file << "# rdf:\n\n";
            file << "@prefix : <http://vstu.ru/poas/code#> ." << "\n";
            file << "@prefix owl: <http://www.w3.org/2002/07/owl#> ." << "\n";
            file << "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ." << "\n";
            file << "@prefix xml: <http://www.w3.org/XML/1998/namespace> ." << "\n";
            file << "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ." << "\n";
            file << "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ." << "\n";
            file << "@base <http://vstu.ru/poas/code> ." << "\n\n";
            file << rdfString;
            
            Logger::info("RDF Successfully saved to file");
            isSuccess = true;
        } catch (string& err) {
			cout << "error: " << err << endl;
            Logger::error(err);
        } catch (...) {
			cout << "Unexpected error found"<< endl;
            Logger::error("Unexpected error found");
        }

        if (dstNode)
            delete dstNode;
        if (rdfNode)
            delete rdfNode;

        if (isSuccess && shortFilename.length() > 0)
            Logger::saveAndClear(logsDir + shortFilename + ".log.txt");
        else
            Logger::saveAndClear(logsDir + "_______ERROR__" + functionName + "__" + to_string(std::time(0)) + ".log.txt");

    finally_lbl:
        cout << "Processed function " << functionName << endl;
        Logger::clear();
    }
};



int main(int argc, const char** argv) {
    std::cout << typeid(int).name() << std::endl;

    auto domainName = string(argv[argc - 2]);    
    if (domainName != "expression" && domainName != "ctrl_flow" && domainName != "control_flow") {
        cout << "Invalid domain name - expected 'expression' or 'ctrl_flow'" << endl;
        return -1;
    }
    cout << "domain = " << domainName << endl;

    auto outputDir = string(argv[argc - 1]);
    if (!std::filesystem::exists(outputDir)) {
		cout << "The last arg should be valid output folder path" << endl;
        return -1;
	}
    cout << "outputPath = " << outputDir << endl;

    auto ExpectedParser = CommonOptionsParser::create(argc, argv, MyToolCategory);
    if (!ExpectedParser) {
        // Fail gracefully for unsupported options.
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }

    CommonOptionsParser& OptionsParser = ExpectedParser.get();
    ClangTool Tool(OptionsParser.getCompilations(),
        OptionsParser.getSourcePathList());
    ExprPrinter Printer(outputDir);
    MatchFinder Finder;

    if (domainName == "expression") {
        auto exressionDomainMatcher =
            expr(anyOf(binaryOperator(hasOperatorName("&&")),
                       binaryOperator(hasOperatorName("||")),
                       unaryOperator(hasOperatorName("!")),
                       binaryOperator(hasOperatorName("+")),
                       binaryOperator(hasOperatorName("-")),
                       binaryOperator(hasOperatorName("*")),
                       binaryOperator(hasOperatorName("/")),
                       unaryOperator(hasOperatorName("-")),
                       unaryOperator(hasOperatorName("++")),
                       unaryOperator(hasOperatorName("--")),
                       binaryOperator(isAssignmentOperator()),
                       binaryOperator(isComparisonOperator()),
                       cxxMemberCallExpr(), 
                       memberExpr(),
                       conditionalOperator()))
                .bind("exressionDomain");
        Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, exressionDomainMatcher), &Printer);
    } else {
        auto cntrlflowDomainMatcher = functionDecl(hasBody(compoundStmt())).bind("cntrlflowDomain");
        Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, cntrlflowDomainMatcher), &Printer);
    }    

    return Tool.run(newFrontendActionFactory(&Finder).get());
}
