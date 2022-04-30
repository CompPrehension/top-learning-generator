from enum import Enum

from NamespaceUtil import NamespaceUtil

''' Made with docs:
https://docs.python.org/3/library/enum.html
'''

class NoValue(Enum):
    "Hide numeric value from Enum's string representation"
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)

class AutoNumber(NoValue):
    def __new__(cls, *args):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

class JavaEnum(AutoNumber):
    def ordinal(self):
        return self.value

    @classmethod
    def values(cls):
        return cls.__members__.values()


class GraphRole(JavaEnum):
    SCHEMA = ("schema#")  # all static assertions important for reasoning
    SCHEMA_SOLVED = ("schema_s#")  # inferences from schema itself

    QUESTION_TEMPLATE = ("qt#")  # template - a backbone for a question
    QUESTION_TEMPLATE_SOLVED = ("qt_s#")  # inferences from template itself

    QUESTION = ("q#"),  # data complementing template to complete question
    QUESTION_SOLVED = ("q_s#")  # inferences from whole question

    QUESTION_DATA = ("q_data#")  # data required to create a question


    def __init__(self, prefix):  #  num,
        # self.num = num
        self.prefix = prefix;

    def ns(self, basePrefix=''):
        'Convert to NamespaceUtil instance based on prefix if provided'
        return NamespaceUtil(basePrefix + self.prefix);

    @classmethod
    def getNext(self, role):
        ordIndex = role.ordinal() + 1;
        for other in GraphRole.values():
            if (other.ordinal() == ordIndex):
                return other;

        return None;

    @classmethod
    def getPrevious(self, role):
        ordIndex = role.ordinal() - 1;
        for other in GraphRole.values():
            if (other.ordinal() == ordIndex):
                return other;

        return None;



if __name__ == '__main__':
    print(GraphRole.SCHEMA)
