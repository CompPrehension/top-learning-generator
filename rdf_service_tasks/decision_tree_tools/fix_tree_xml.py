# fix_tree_xml.py

import os
import re
import shutil


replacements = [
    # ('<Outcome value="Found">', '<Outcome value="found">'),
    # ('<Outcome value="Not found">', '<Outcome value="none">'),
    ('"else_if"', '"else-if"'),
    # ('<BranchResultNode value="false"', '<BranchResultNode value="false" _errorNode="true" '),

    ('&lt;sub&gt;' , ''),
    ('&lt;/sub&gt;', ''),

    # # <b>ABC</b>  ->  ${val('ABC','и')}
    # ('&lt;b&gt; ' , ' '+var_mark_L),
    # ('&lt;b&gt;'  , var_mark_L),
    # (' &lt;/b&gt;', var_mark_R+' '),
    # ('&lt;/b&gt;' , var_mark_R),

    # # $ABC  ->  ${val('ABC','и')}
    # (re.compile(r'\$(\w+)'), var_mark_L+r'\1'+var_mark_R),
]


var_mark_L = "${val('"
var_mark_R_tpl = "','%s')}"

var_mark_R = var_mark_R_tpl % "и"
class_mark_L = "${class('"
class_mark_R = var_mark_R

outcome_text_replacements = [
    # убираем подстрочный стиль
    ('<sub>' , ''),
    ('</sub>', ''),

    # собственные замены для получения команд для описания переменных дерева:
    # 	* взятые в жирный стиль или с приставкой $   —  просто обращение к имени объекта в данной переменной
    # 	* взятые в жирный стиль после слова "Действие" или с приставкой %   —  взятие типа И имени объекта в данной переменной (через пробел)

    # Действие <b>ABC</b>  ->  ${class('ABC','и')} ${val('ABC','и')}
    (re.compile(r'Действие\s+\<b\>\s*(\w+?)\s*\<\/b\>', re.I),    # matches `Действие ...` or `действие ...`
        class_mark_L+r'\1'+class_mark_R +' '+ var_mark_L+r'\1'+var_mark_R),

    # <b>ABC</b>  ->  ${val('ABC','и')}
    ('<b> ' , ' '+var_mark_L),
    ('<b>'  , var_mark_L),
    (' </b>', var_mark_R+' '),
    ('</b>' , var_mark_R),

    # $ABC  ->  ${val('ABC','и')}
    (re.compile(r'\$(\w+)'), var_mark_L+r'\1'+var_mark_R),

    # %(ABC, р)  ->  ${class('ABC','р')} ${val('ABC','и')}
    (re.compile(r'\%\(\s*(\w+)\s*,\s*(\w)\s*\)'), class_mark_L+r'\1'+(var_mark_R_tpl % r'\2')+' '+ var_mark_L+r'\1'+var_mark_R),

    # %ABC  ->  ${class('ABC','и')} ${val('ABC','и')}
    (re.compile(r'\%(\w+)'), class_mark_L+r'\1'+class_mark_R+' '+ var_mark_L+r'\1'+var_mark_R),
]



filename = r'tree.xml'
src_dir = r'c:/Users/Olduser/Downloads/'
dst_dir = r'c:/D/Work/YDev/CompPr/Max-Person/inputs/input_examples/'
dst_dir2 = r'c:/D/Work/YDev/CompPr/CompPrehension/modules/core/src/main/resources/org/vstu/compprehension/models/businesslogic/domains/control-flow-statements-domain-model/'
filename_back = r'tree_back.xml'


def replace_in_text(text: str, replacements: list[tuple]=replacements):
    for before, after in replacements:
        if isinstance(before, str):
            text = text.replace(before, after)
        else:
            # before is re:
            text = before.sub(after, text)
    return text


def update_and_pretty_format_xml_file(path):
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)

    # 1) Обновить/исправить атрибуты узлов
    # 1.2) Заменить обозначения переменных специальной разметкой для формирования объяснений: Дополнить конечные узлы `BranchResultNode` типа Ложь атрибутом `errorNode`
    for elem in tree.iter():
        if elem.tag != 'BranchResultNode':
            continue
        # if elem.text:
        #     print('my text:')
        #     print('\t'+(elem.text).strip())
        if elem.attrib.items():
            # print('my attributes:')
            # for key, value in elem.items():
            #     print('\t\t'+key +' : '+value)

            if elem.attrib['value'] == 'false' and '_alias' in elem.attrib:
                node_text = elem.attrib['_alias']
                if node_text.startswith(('[', '(')):
                    continue

                # add `errorNode` attribute!
                # elem.set('_errorNode', 'true')
                if ':' in node_text:
                    law, explanation = node_text.split(':', maxsplit=1)
                    errorNode = law.strip()
                    explanation = explanation.strip()
                else:
                    errorNode = 'true'
                    explanation = node_text

                # Заменить обозначения переменных
                explanation = replace_in_text(explanation, outcome_text_replacements)
                # Добавить атрибуты в узел
                elem.set('_errorNode', errorNode)
                elem.set('_explanation', explanation)

    # 1.3) Заменить свойства узлов, созданные в редакторе для наводящих вопросов, локализованными копиями (_*  —→  _RU_* и _EN_*)

    # Taken from: its/questions/gen/formulations/TemplatingUtils.kt
    # Found usages (in the code) like: `${localizationCode}.explanation`.
    atributes_to_expand = set('_explanation _nextStepBranchResult _nextStepExplanation _nextStepQuestion _question _text _triviality'.split())
    locale_codes = ('_RU', '_EN', )

    for elem in tree.iter():
        for key, val in dict(elem.attrib).items():
            # print('my attributes:')
            # for key, value in elem.items():
            #     print('\t\t'+key +' : '+value)

            if key in atributes_to_expand:

                # Заменить обозначения переменных
                val = replace_in_text(val, outcome_text_replacements)

                # # Удалить старый атрибут из узла
                # del elem.attrib[key]

                # Добавить новые атрибуты в узел
                for loc in locale_codes:
	                elem.set(loc + key, val)


    # 2) Отформатировать
    ET.indent(tree)  # this makes pretty format

    # 3) Сохранить в тот же файл
    tree.write(path, encoding='utf-8')



def main():
    with open(src_dir + filename) as f:
        text = f.read()
    print(f'read {filename}.')

    text = replace_in_text(text)
    print('fixed content.')

    dst = dst_dir + filename
    with open(dst, 'w') as f:
        f.write(text)
    print('saved into input_examples/.')

    update_and_pretty_format_xml_file(dst)
    print('fixed xml within the file.')

    # make a copy
    dst2 = dst_dir2 + filename
    shutil.copy(dst, dst2)
    # with open(dst2, 'w') as f2:
    #     with open(dst) as f:
    #         f2.write(f.read)
    print('saved a copy into CompPrehension → domain resouces.')


    # debug exit.
    if 0:
        return

    # save src file as different name
    old = src_dir + filename
    new = src_dir + filename_back
    if os.path.isfile(new):
        os.remove(new)
    os.rename(old, new)
    print('renamed source file in Downloads.')

if __name__ == '__main__':
    main()

