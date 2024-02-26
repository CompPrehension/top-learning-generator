# fix_tree_xml.py

import os
import re


var_mark_L = "${val('"
var_mark_R = "','и')}"

replacements = [
    # ('<Outcome value="Found">', '<Outcome value="found">'),
    # ('<Outcome value="Not found">', '<Outcome value="none">'),
    ('"else_if"', '"else-if"'),
    # ('<BranchResultNode value="false"', '<BranchResultNode value="false" _errorNode="true" '),
    ('&lt;sub&gt;' , ''),
    ('&lt;/sub&gt;', ''),

    # <b>ABC</b>  ->  ${val('ABC','и')}
    ('&lt;b&gt; ' , ' '+var_mark_L),
    ('&lt;b&gt;'  , var_mark_L),
    (' &lt;/b&gt;', var_mark_R+' '),
    ('&lt;/b&gt;' , var_mark_R),

    # $ABC  ->  ${val('ABC','и')}
    (re.compile(r'\$(\w+)'), var_mark_L+r'\1'+var_mark_R),
]



filename = r'tree.xml'
src_dir = r'c:/Users/Olduser/Downloads/'
dst_dir = r'c:/D/Work/YDev/CompPr/Max-Person/inputs/input_examples/'
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

    # 1) Дополнить конечные узлы `BranchResultNode` типа Ложь атрибутом `errorNode`
    tree = ET.parse(path)
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

            if elem.attrib['value'] == 'false':
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
                elem.set('_errorNode', errorNode)
                elem.set('_explanation', explanation)


    # 2) Отформатировать
    ET.indent(tree)  # this makes pretty format

    # 3) Сохранить в тот же файл
    tree.write(path, encoding='utf-8')



def main():
    with open(src_dir + filename) as f:
        text = f.read()
    print('read.')

    text = replace_in_text(text)
    print('fix.')

    dst = dst_dir + filename
    with open(dst, 'w') as f:
        f.write(text)
    print('save.')

    update_and_pretty_format_xml_file(dst)
    print('fix xml.')

    # save src file as different name
    old = src_dir + filename
    new = src_dir + filename_back
    if os.path.isfile(new):
        os.remove(new)
    os.rename(old, new)
    print('rename source.')

if __name__ == '__main__':
    main()

