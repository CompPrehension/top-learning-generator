# copy_ttl.py

import re

# shutil.copy2(src, dest)



filename = r'judged-f.ttl'
src_dir = r'c:/Temp/'
dst_dir = r'c:/D/Work/YDev/CompPr/Max-Person/inputs/input_examples/'
# filename_back = r'judged-f_back.xml'


replacements = [
    # re: whole line with trailing \n
    (re.compile(r'^.+not-for-reasoner:expr_values.+$\s*', re.I | re.M), ''),
    # (re.compile(r'\#else\-if\>'), '#else_if>'),
]

# <http://vstu.ru/poas/code#job->pid != -1> <not-for-reasoner:expr_values> "1,0" .


def replace_in_text(text: str, replacements: list[tuple]=replacements):
    for before, after in replacements:
        # text = text.replace(before, after)
        # before is re:
        text = before.sub(after, text)
    return text

def print_current_time():
    import datetime
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime('%H:%M:%S')
    print(formatted_time)

def main():
    with open(src_dir + filename) as f:
        text = f.read()
    print('read.')

    text = replace_in_text(text)
    print('fix.')

    with open(dst_dir + filename, 'w') as f:
        f.write(text)
    print('save.')

    print_current_time()

if __name__ == '__main__':
    main()

