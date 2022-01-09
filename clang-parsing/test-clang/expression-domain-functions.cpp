
#include "expression-domain-functions.h"
#include "helpers.h"


//using namespace clang::tooling;
using namespace clang::ast_matchers;
using namespace llvm;


void isValidNodeInner(ExpressionDomainNode* node, bool& _isValid, int& operatorsCount)
{
    if (node == nullptr || !_isValid)
        return;

    if (auto tmp = dynamic_cast<ExpressionDomainUndefinedNode*>(node))
    {
        _isValid = false;
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainParenExprNode*>(node))
    {
        isValidNodeInner(tmp->getExpr(), _isValid, operatorsCount);
        ++operatorsCount;
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
    if (auto tmp = dynamic_cast<ExpressionDomainConditionalOperatorNode*>(node))
    {
        isValidNodeInner(tmp->getExpr(), _isValid, operatorsCount);
        isValidNodeInner(tmp->getLeft(), _isValid, operatorsCount);
        isValidNodeInner(tmp->getRight(), _isValid, operatorsCount);
        ++operatorsCount;
        return;
    }
}

bool isValidNode(ExpressionDomainNode* node)
{
    bool isValid = true;
    int operatorsCount = 0;
    isValidNodeInner(node, isValid, operatorsCount);
    return isValid && operatorsCount >= 2;
}

ExpressionDomainNode* mapToDst(const clang::Expr* node, clang::SourceManager* sourceMgr) {

    if (node == nullptr)
        return nullptr;
    if (auto parenOperator = dyn_cast<clang::ParenExpr>(node))
    {
        auto expr = mapToDst(parenOperator->getSubExpr(), sourceMgr);
        return new ExpressionDomainParenExprNode((clang::ParenExpr*)parenOperator, expr);
    }
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
        auto value = intValue->getValue().convertToDouble();
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
    if (auto ternar_expr = dyn_cast<clang::ConditionalOperator>(node))
    {
        auto expr = mapToDst(ternar_expr->getCond(), sourceMgr);
        auto left = mapToDst(ternar_expr->getTrueExpr(), sourceMgr);
        auto right = mapToDst(ternar_expr->getFalseExpr(), sourceMgr);
        return new ExpressionDomainConditionalOperatorNode((clang::ConditionalOperator*)ternar_expr, expr, left, right);
    }
    /*
    if (auto funcDecl = dyn_cast<clang::FunctionDecl>(node))
    {

    }
    */
    //auto sourceRange = node->getSourceRange();
    const string text = Lexer::getSourceText(clang::CharSourceRange::getTokenRange(node->getSourceRange()), *sourceMgr, clang::LangOptions()).str();
    auto undefinedsource = get_source_text_raw(node->getSourceRange(), *sourceMgr);
    return new ExpressionDomainUndefinedNode((clang::Stmt*)node);
}

string rdfTreeToString( vector<ExpressionDomainRdfNode>& nodes)
{
    std::stringstream ss;
    for (auto& node : nodes)
    {
        ss << "\n\n" << node.toString();
    }
    ss << "\n";
    return ss.str();
}



void mapToExressionDomainRdfNodes(ExpressionDomainNode* node, vector<ExpressionDomainRdfNode>& acc, int& index)
{
    if (node == nullptr)
        return;

    if (auto tmp = dynamic_cast<ExpressionDomainUndefinedNode*>(node))
    {
        return;
    }
    if (auto tmp = dynamic_cast<ExpressionDomainParenExprNode*>(node))
    {
        acc.push_back(ExpressionDomainRdfNode("operator", "()", ++index));
        mapToExressionDomainRdfNodes(tmp->getExpr(), acc, index);
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
        for (auto* arg : tmp->getArgs())
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
        acc.push_back(ExpressionDomainRdfNode("operator", tmp->isArrow() ? "->" : ".", ++index));
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
    if (auto tmp = dynamic_cast<ExpressionDomainConditionalOperatorNode*>(node))
    {
        mapToExressionDomainRdfNodes(tmp->getExpr(), acc, index);
        acc.push_back(ExpressionDomainRdfNode("operator", "?:", ++index));
        mapToExressionDomainRdfNodes(tmp->getLeft(), acc, index);
        mapToExressionDomainRdfNodes(tmp->getRight(), acc, index);
        return;
    }
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
