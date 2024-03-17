# q_generator_main.py

import argparse
import random  # using seed, sample
import os.path
import shutil
import sys

import fs

from GraphRole import GraphRole
from full_questions import repair_statements_in_graph
import sqlite_questions_metadata as dbmeta
from service import _patch_and_parse_ttl, setQuestionSubgraphDB, getQuestionModelDB, solve_template_with_jena, \
    process_template, generate_data_for_question, read_access_config

sys.path.insert(1, '../../../c_owl/')  # dev location
sys.path.insert(2, 'c_owl/')  # desired deploy location
from common_helpers import Checkpointer


def main(input_templates_dir: str, output_questions_dir: str, questions_origin: str = None, templates_limit: int = 0):
    """
    Loop over template data files in specified location and call generation of question for each template.

    :param input_templates_dir: path to a directory containing .ttl files with template data
    :param output_questions_dir: path to a directory where to store resulting .json files with question data
    :param questions_origin: what to save in "origin" field of question metadata (`None` by default)
    :param templates_limit: maximum templates to process; 0 (by default) means no limit.
    :return:
    """
    ch = Checkpointer()

    file_and_name_list = find_templates(input_templates_dir, limit=templates_limit * 10)

    ch.hit('templates found on disk')

    if templates_limit > 0 and (L := len(file_and_name_list)) > templates_limit:
        # randomly select some of found items
        print(f'Truncating the set of templates from {L} to {templates_limit}.')
        file_and_name_list = random.sample(file_and_name_list, templates_limit)

    templates_used = 0
    questions_count = 0
    skip_count = 0
    limit_total_questions = 0  # 0 is no limit

    for path, name in file_and_name_list:

        # skip if exists in DB
        qt = dbmeta.Templates.get_or_none(dbmeta.Templates.name == name)

        if qt is not None and qt._version >= dbmeta.TOOL_VERSION:
            # Пропускаем шаблоны, уже обработанные текущей версией генератора вопросов
            print('    - DB: skipping EXISTING template which is up-to-date (id=%d):' % qt.id, qt.name)
            continue

        # создать в БД запись для шаблона
        qt = dbmeta.createQuestionTemplateDB(name, src_file_path=path)
        qt.origin = questions_origin

        ok = load_template(qt, input_templates_dir)
        if not ok:
            continue

        # Работаем с шаблоном дальше ...

        ok = solve_template(qt, verbose=True)
        if not ok:
            continue

        # filter_by_concepts = 0
        # # filter_by_concepts = dbmeta.names_to_bitmask(['break', 'continue'])
        # if filter_by_concepts:
        #     if not (qt.concept_bits & filter_by_concepts):
        #         continue

        qtname = qt.name
        questions_made = ()

        print()
        print()
        print("Processing template: ", qtname)
        print("    (skipped so far: %d)" % skip_count)
        print("========")
        try:
            questions_made = process_template(qt, questions_count)
            questions_count += len(questions_made)
            templates_used += 1
            # set stage even if no questions were made, to avoid trying it next time
            qt._stage = dbmeta.STAGE_QT_USED
            qt._version = dbmeta.TOOL_VERSION
            qt.save()
            if questions_made:
                ch.hit('   + 1 template used')
                ch.since_start('[%3d] time elapsed so far:' % (templates_used + skip_count))
        except NotImplementedError as e:
            skip_count += 1
            print()
            print('Error with template: ', qtname)
            print(e)
            print()

        # process the generated questions
        for q in questions_made:
            print("Making JSON for question: ", q.name, "(i: %d)" % (questions_count + skip_count))
            print("========")
            try:
                q = generate_data_for_question(q)
                if q:
                    save_output_question_file(q, output_questions_dir)
            except (NotImplementedError, AssertionError) as e:
                print()
                print('Error with JSON data of question: ', q.name)
                print(e)
                q._stage += 10  # mark the error
                q.save()
                print()

        if limit_total_questions > 0 and questions_count > limit_total_questions:
            continue
    ...


def find_templates(rdf_dir, wanted_ext=".ttl", file_size_filter=(3 * 1024, 40 * 1024), skip_first=0, limit=None) -> list[tuple]:
    """ Find files with extension and of size within the specified range in bytes.
    :return: list of file paths.
    """

    file_and_name_list = []
    files_total = 0
    files_selected = 0

    src_fs = fs.open_fs(rdf_dir)
    for path, info in src_fs.walk.info(namespaces=['details']):
        if not info.is_dir:
            if not info.name.endswith(wanted_ext):
                continue
            files_total += 1

            if skip_first > 0 and files_total < skip_first:
                continue

            if file_size_filter and not (file_size_filter[0] <= info.size <= file_size_filter[1]):
                continue
            files_selected += 1

            if limit and files_selected > limit:
                break

            # cut last section with digits (timestamp), cut last 12 digits from hash
            name = "_".join(info.name.split("__")[:-1])[:-12]
            print('[%3d]' % files_selected, name, '...')

            file_and_name_list.append((
                path, name
            ))

    print("Searching for templates completed.")
    print("Used", files_selected, 'files of', files_total, 'in the directory.')
    return file_and_name_list


def load_template(qt: dbmeta.Templates, base_dir: str) -> bool:
    """ Загрузить данные шаблона для имеющейся записи Template из файла `qt.src_path` """
    path = base_dir + qt.src_path
    with open(path) as f:
        m = _patch_and_parse_ttl(f.read())

    try:
        random.seed(hash(qt.name))  # make random stable
        m = repair_statements_in_graph(m)
    except AssertionError:
        print(f'error with "{qt.name}"')
        # raise
        # mark the error
        qt._stage = 10 + dbmeta.STAGE_QT_CREATED
        qt.save()
        return False

    setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE, dbmeta.STAGE_QT_CREATED, m)
    return True


def solve_template(qt, verbose=True):
    """Invoke Jena to solve the template"""
    m = getQuestionModelDB(qt, GraphRole.QUESTION_TEMPLATE)

    # solve...
    try:
        m = solve_template_with_jena(m, verbose=verbose)
    except Exception:
        print(f'error with template "{qt.name}"')
        # raise
        return False

    setQuestionSubgraphDB(qt, GraphRole.QUESTION_TEMPLATE_SOLVED, dbmeta.STAGE_QT_SOLVED, m)
    return True


def save_output_question_file(q: dbmeta.Questions, output_dir):
    """Copy DATA file of the question directly to the specified directory"""
    file_subpath = q.q_data_graph

    config = read_access_config()
    base_dir = config["ftp_base"]

    if file_subpath and base_dir:
        os.makedirs(output_dir, exist_ok=True)
        shutil.copyfile(
            os.path.join(base_dir, file_subpath),
            # file name only >>
            os.path.join(output_dir, os.path.basename(file_subpath)),
        )
    else:
        raise ValueError('To export DATA of a question, both file_subpath and base_dir must be known, but got:' +
                         str((file_subpath, base_dir)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True,
                        help='input_templates_dir: path to a directory containing .ttl files with template data')
    parser.add_argument('-o', '--output', required=True,
                        help='output_questions_dir: path to a directory where to store resulting .json files with question data')
    parser.add_argument('-g', '--origin', default=None,
                        help='questions_origin: what to save in "origin" field of question metadata (`None`/`null` by default)')
    parser.add_argument('-n', '--limit', type=int, default=0,
                        help='templates_limit: maximum templates to process; 0 (by default) means no limit.')

    args = vars(parser.parse_args())
    ### print(args)

    main(args['input'], args['output'], args["origin"], args['limit'])
    # main("c:/data/compp-gen/control_flow/parsed", "c:/data/compp-gen/control_flow/questions", "ag", 5)

    # example cmd ...
    '''
        python q_generator_main.py -i "c:/data/compp-gen/control_flow/parsed" -o "c:/data/compp-gen/control_flow/questions" -g "ag" -n 5
    '''
