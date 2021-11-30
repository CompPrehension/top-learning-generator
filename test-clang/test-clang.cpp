// Declares clang::SyntaxOnlyAction.
#include "clang/Frontend/FrontendActions.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
// Declares llvm::cl::extrahelp.
//#include "llvm/Support/CommandLine.h"
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "ExpressionDomainNodes.h"

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

ExpressionDomainNode* mapToDst(const clang::Expr* node);


class ExprPrinter : public MatchFinder::MatchCallback {
public:
    virtual void run(const MatchFinder::MatchResult& Result) {

        //auto nodeMap = Result.Nodes.getMap();
        //auto sourceMgr = Result.SourceManager;
        //auto test = (*nodeMap.find("op_plus")).second;
        //Result.SourceManager->getExpansionLoc()

        if (auto node = Result.Nodes.getNodeAs<clang::Expr>("match"))
        {
            auto dstNode = mapToDst(node);
            
            node->dump();
            printf_s("\n");
            dstNode->dump();
            printf_s("\n");
            printf_s("\n");
            printf_s("\n");


            //auto teeemp = FS->getExprLoc();
            //int x = 0;
            //FS->getExprLoc().dump();
            //FS->

            //FS->getType()->dump();
            //FS->dump();
        }
        /*if (auto FS = Result.Nodes.getNodeAs<clang::Expr>("op_mul"))
        {
            FS->getType()->dump();
            FS->dump();
        }*/
    }
};

ExpressionDomainNode* mapToDst(const clang::Expr* node) {
    
    //node->get
    //node->dump();
    //auto opName = string(*internal::getEx(*node));
    
    if (auto binaryOperator = dyn_cast<clang::BinaryOperator>(node))
    {
        auto left = mapToDst(binaryOperator->getLHS());
        auto right = mapToDst(binaryOperator->getRHS());
        return new ExpressionBinaryOperatorNode(string(*internal::getOpName(*binaryOperator)), left, right);
    }
    if (auto unaryOperator = dyn_cast<clang::UnaryOperator>(node))
    {
        auto child = mapToDst(unaryOperator->getSubExpr());
        return new ExpressionUnaryOperatorNode(string(*internal::getOpName(*unaryOperator)), child);
    }
    if (auto intValue = dyn_cast<clang::IntegerLiteral>(node))
    {
        auto value = intValue->getValue().getZExtValue();
        auto valueS = to_string(value);
        return new ExpressionConstNode(valueS);
    }
    if (auto intValue = dyn_cast<clang::FloatingLiteral>(node))
    {
        auto value = intValue->getValue().convertToFloat();
        auto valueS = to_string(value);
        return new ExpressionConstNode(valueS);
    }
    if (auto implCast = dyn_cast<clang::ImplicitCastExpr>(node))
    {
        return mapToDst(implCast->getSubExpr());
    }
    if (auto callExpr = dyn_cast<clang::CallExpr>(node))
    {
        if (auto funcDecl = dyn_cast<clang::FunctionDecl>(callExpr->getCalleeDecl()))
        {
            auto name = funcDecl->getNameAsString();

            auto args = vector<ExpressionDomainNode*>();
            for (auto* arg : callExpr->arguments())
            {
                args.push_back(mapToDst(arg));
            }
            return new ExpressionFuncCallNode(name, args);
        }
    }
    if (auto declRef = dyn_cast<clang::DeclRefExpr>(node))
    {
        if (auto varDecl = dyn_cast<clang::VarDecl>(declRef->getDecl()))
        {
            auto initValue = varDecl->getInit();
            auto name = varDecl->getNameAsString();
            return new ExpressionVarNode(name, mapToDst(initValue));
        }
    }

    //node->dump();
    return new ExpressionDomainEmptyNode();

    //throw string("unsopported node type. rollback");
}

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
    /*
    auto matcher = expr(
        binaryOperator(anyOf(
            hasOperatorName("+"),
            //hasOperatorName("-"),
            //hasOperatorName("*"),
            hasOperatorName("/")
        )).bind("match")
    );
    */

    auto matcher = expr(
        //constantExpr(),
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
    ).bind("match");

    ExprPrinter Printer;
    MatchFinder Finder;
    Finder.addMatcher(matcher, &Printer);

    return Tool.run(newFrontendActionFactory(&Finder).get());
}
