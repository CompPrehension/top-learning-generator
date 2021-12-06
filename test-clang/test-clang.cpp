// Declares clang::SyntaxOnlyAction.
#include "clang/Frontend/FrontendActions.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
// Declares llvm::cl::extrahelp.
//#include "llvm/Support/CommandLine.h"
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "ExpressionDomainNodes.h"
#include "helpers.h"
#include <iostream>
#include "ExpressionDomainRdfNode.h"

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


bool isValidNode(ExpressionDomainNode* node);
void isValidNodeInner(ExpressionDomainNode* node, bool& _isValid, int& operatorsCount);
ExpressionDomainNode* mapToDst(const clang::Expr* node, clang::SourceManager* sourceMgr);
void mapToExressionDomainRdfNodes(ExpressionDomainNode* node, vector<ExpressionDomainRdfNode>& acc, int& index);
vector<ExpressionDomainRdfNode> mapToExressionDomainRdfNodes(ExpressionDomainNode* node);


class ExprPrinter : public MatchFinder::MatchCallback {
public:
    virtual void run(const MatchFinder::MatchResult& Result) {
        if (auto node = Result.Nodes.getNodeAs<clang::Expr>("exressionDomain"))
        {
            ExpressionDomainNode* dstNode;
            __try {
                dstNode = mapToDst(node, Result.SourceManager);

                if (!isValidNode(dstNode))
                    return;

                std::cout << dstNode->toString();
                std::cout << "\n";

                auto rdfTree = mapToExressionDomainRdfNodes(dstNode);
                int x = 0;

            } __finally {
                if (dstNode)
                    delete dstNode;
            }
        }
    }
};


bool isValidNode(ExpressionDomainNode* node)
{
    bool isValid = true;
    int operatorsCount = 0;
    isValidNodeInner(node, isValid, operatorsCount);
    return isValid && operatorsCount >= 2;
}


void isValidNodeInner(ExpressionDomainNode* node, bool& _isValid, int& operatorsCount)
{
    if (node == nullptr || !_isValid)
        return;

    if (auto tmp = dynamic_cast<ExpressionDomainUndefinedNode*>(node))
    {
        _isValid = false;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainBinaryOperatorNode*>(node))
    {
        isValidNodeInner(tmp->getLeftChild(), _isValid, operatorsCount);
        isValidNodeInner(tmp->getRightChild(), _isValid, operatorsCount);
        ++operatorsCount;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainUnaryOperatorNode*>(node))
    {
        isValidNodeInner(tmp->getChild(), _isValid, operatorsCount);
        ++operatorsCount;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainVarNode*>(node))
    {
        isValidNodeInner(tmp->getInit(), _isValid, operatorsCount);
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainFuncCallNode*>(node))
    {
        for (auto* arg : tmp->getArgs())
        {
            isValidNodeInner(arg, _isValid, operatorsCount);
        }
        ++operatorsCount;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainConstNode*>(node))
    {        
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainMemberExprNode*>(node))
    {
        isValidNodeInner(tmp->getLeftValue(), _isValid, operatorsCount);
        ++operatorsCount;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainArrayBracketNode*>(node))
    {
        isValidNodeInner(tmp->getArrayExpr(), _isValid, operatorsCount);
        isValidNodeInner(tmp->getIndexExpr(), _isValid, operatorsCount);
        ++operatorsCount;
        return;
    }
}

ExpressionDomainNode* mapToDst(const clang::Expr* node, clang::SourceManager* sourceMgr) {
    
    if (node == nullptr)
        return nullptr;
    
    if (auto binaryOperator = dyn_cast<clang::BinaryOperator>(node))
    {
        auto left = mapToDst(binaryOperator->getLHS(), sourceMgr);
        auto right = mapToDst(binaryOperator->getRHS(), sourceMgr);
        return new ExpressionDomainBinaryOperatorNode((clang::BinaryOperator*)binaryOperator, string(*internal::getOpName(*binaryOperator)), left, right);
    }
    if (auto unaryOperator = dyn_cast<clang::UnaryOperator>(node))
    {
        auto child = mapToDst(unaryOperator->getSubExpr(), sourceMgr);
        return new ExpressionDomainUnaryOperatorNode((clang::UnaryOperator*)unaryOperator, string(*internal::getOpName(*unaryOperator)), child);
    }
    if (auto intValue = dyn_cast<clang::IntegerLiteral>(node))
    {
        auto value = intValue->getValue().getZExtValue();
        auto valueS = to_string(value);
        return new ExpressionDomainConstNode((clang::Stmt*)node, valueS);
    }
    if (auto intValue = dyn_cast<clang::FloatingLiteral>((clang::Stmt*)node))
    {
        auto value = intValue->getValue().convertToFloat();
        auto valueS = to_string(value);
        return new ExpressionDomainConstNode((clang::Stmt*)node, valueS);
    }
    if (auto implCast = dyn_cast<clang::ImplicitCastExpr>(node))
    {
        return mapToDst(implCast->getSubExpr(), sourceMgr);
    }
    if (auto explicitCast = dyn_cast<clang::ExplicitCastExpr>(node))
    {
        return mapToDst(explicitCast->getSubExpr(), sourceMgr);
    }
    if (auto explicitCast = dyn_cast<clang::CStyleCastExpr>(node))
    {
        return mapToDst(explicitCast->getSubExpr(), sourceMgr);
    }
    if (auto callExpr = dyn_cast<clang::CallExpr>(node))
    {
        //auto temp = mapToDst(callExpr->getCallee(), sourceMgr);

        if (auto funcDecl = dyn_cast<clang::FunctionDecl>(callExpr->getCalleeDecl()))
        {
            auto name = funcDecl->getNameAsString();

            auto args = vector<ExpressionDomainNode*>();
            for (auto* arg : callExpr->arguments())
            {
                args.push_back(mapToDst(arg, sourceMgr));
            }
            return new ExpressionDomainFuncCallNode((clang::CallExpr*)node, name, args);
        }
        int x = 0;
    }
    if (auto declRef = dyn_cast<clang::DeclRefExpr>(node))
    {
        if (auto varDecl = dyn_cast<clang::VarDecl>(declRef->getDecl()))
        {
            auto initValue = varDecl->getInit();
            auto name = varDecl->getNameAsString();
            return new ExpressionDomainVarNode((clang::DeclRefExpr*)node, name, initValue != nullptr ? mapToDst(initValue, sourceMgr) : nullptr);
        }
    }
    if (auto membExpr = dyn_cast<clang::MemberExpr>(node))
    {
        auto left = mapToDst(membExpr->getBase(), sourceMgr);
        auto right = membExpr->getMemberDecl()->getNameAsString();
        
        return new ExpressionDomainMemberExprNode((clang::MemberExpr*)membExpr, left, right);
    }
    if (auto arr_sub_expr = dyn_cast<clang::ArraySubscriptExpr>(node))
    {
        auto left = mapToDst(arr_sub_expr->getBase(), sourceMgr);
        auto right = mapToDst(arr_sub_expr->getIdx(), sourceMgr);
        return new ExpressionDomainArrayBracketNode((clang::ArraySubscriptExpr*)arr_sub_expr, left, right);
    }
    /*
    if (auto funcDecl = dyn_cast<clang::FunctionDecl>(node))
    {

    }
    */

    auto undefinedsource = get_source_text_raw(node->getSourceRange(), *sourceMgr);
    return new ExpressionDomainUndefinedNode((clang::Stmt*)node);
}

vector<ExpressionDomainRdfNode> mapToExressionDomainRdfNodes(ExpressionDomainNode* node)
{
    vector<ExpressionDomainRdfNode> result;
    int index = 0;
    mapToExressionDomainRdfNodes(node, result, index);
    if (result.size() > 0) 
    {
        result[0].setIsFirst();
        result[result.size() - 1].setIsLast();
    }

    return result;
}


void mapToExressionDomainRdfNodes(ExpressionDomainNode* node, vector<ExpressionDomainRdfNode>& acc, int& index)
{
    if (node == nullptr)
        return;

    if (auto tmp = dynamic_cast<ExpressionDomainUndefinedNode*>(node))
    {
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainBinaryOperatorNode*>(node))
    {
        mapToExressionDomainRdfNodes(tmp->getLeftChild(), acc, index);
        acc.push_back(ExpressionDomainRdfNode("operator", tmp->getType(), ++index));
        mapToExressionDomainRdfNodes(tmp->getRightChild(), acc, index);        
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainUnaryOperatorNode*>(node))
    {
        if (tmp->isPostfix())
        {
            mapToExressionDomainRdfNodes(tmp->getChild(), acc, index);
            acc.push_back(ExpressionDomainRdfNode("operator", tmp->getType(), ++index));
        }
        else
        {
            acc.push_back(ExpressionDomainRdfNode("operator", tmp->getType(), ++index));
            mapToExressionDomainRdfNodes(tmp->getChild(), acc, index);
        }        
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainVarNode*>(node))
    {
        acc.push_back(ExpressionDomainRdfNode("variable", tmp->getName(), ++index));
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainFuncCallNode*>(node))
    {
        acc.push_back(ExpressionDomainRdfNode("function", tmp->getName(), ++index));
        acc.push_back(ExpressionDomainRdfNode("function_open_bracket", "(", ++index));        
        int idx = 0;
        for (auto * arg : tmp->getArgs())
        {
            mapToExressionDomainRdfNodes(arg, acc, index);
            if (idx++ < tmp->getArgs().size() - 1)
            {
                acc.push_back(ExpressionDomainRdfNode("comma", ",", ++index));
            }
        }
        acc.push_back(ExpressionDomainRdfNode("function_close_bracket", ")", ++index));
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainConstNode*>(node))
    {
        acc.push_back(ExpressionDomainRdfNode("const", tmp->getValue(), ++index));
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainMemberExprNode*>(node))
    {
        mapToExressionDomainRdfNodes(tmp->getLeftValue(), acc, index);
        acc.push_back(ExpressionDomainRdfNode("operator", "->", ++index));
        acc.push_back(ExpressionDomainRdfNode("variable", tmp->getRightValue(), ++index));
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainArrayBracketNode*>(node))
    {
        mapToExressionDomainRdfNodes(tmp->getArrayExpr(), acc, index);
        acc.push_back(ExpressionDomainRdfNode("array_open_bracket", "[", ++index));
        mapToExressionDomainRdfNodes(tmp->getIndexExpr(), acc, index);
        acc.push_back(ExpressionDomainRdfNode("array_close_bracket", "]", ++index));
        return;
    }
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
    ).bind("exressionDomain");

    ExprPrinter Printer;
    MatchFinder Finder;
    Finder.addMatcher(matcher, &Printer);

    return Tool.run(newFrontendActionFactory(&Finder).get());
}
