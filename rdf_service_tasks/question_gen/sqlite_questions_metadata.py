# sqlite_questions_metadata.py

# note that path to sqlite file is hardcoded by classes generator
if 1:
    # control flow
    from db_utils.sqlite_orm_classes_cf import *
else:
    # expression
    from db_utils.sqlite_orm_classes import *

# write to `_version` column to track data generated with older scripts
TOOL_VERSION = 10

# some enum-like constants
STAGE_QT_FOUND = 0
STAGE_QT_CREATED = 1
STAGE_QT_SOLVED = 2
STAGE_QT_USED = 3  # to make questions (even if no questions exactly created)

STAGE_Q_CREATED = 1
STAGE_Q_SOLVED = 2
STAGE_Q_DATA_SAVED = 3


def findQuestionOrTemplateByNameDB(name):
    obj = (Questions.get_or_none(Questions.name == name)
           or Templates.get_or_none(Templates.name == name));
    if not obj:
        print("    (DB: No question or template found for name: %s)" % name)
    return obj


def findQuestionsOnStageDB(stage=1, limit=None, version=None):
    query = Questions.select()
    if stage:
        query = query.where(Questions._stage == stage)
    if version:
        query = query.where(Questions._version == version)
    iterator = query.limit(limit).execute()
    return list(iterator)


def findTemplatesOnStageDB(stage=1, limit=None, version=None):
    query = Templates.select()
    if stage:
        query = query.where(Templates._stage == stage)
    if version:
        query = query.where(Templates._version == version)
    iterator = query.limit(limit).execute()
    return list(iterator)


def createQuestionTemplateDB(questionTemplateName, src_file_path=None) -> 'question template instance':
    qt = Templates.get_or_none(Templates.name == questionTemplateName)

    if not qt:
        # qt = create_or_update(
        #   key_fields={'name': questionTemplateName,
        #               'src_path': src_file_path, '_stage': STAGE_QT_FOUND
        #               },
        #   # set_fields={},
        #   entity=Templates
        # )
        qt = Templates.create(**{
            'name': questionTemplateName,
            'src_path': src_file_path,
            '_stage': STAGE_QT_FOUND,
            '_version': TOOL_VERSION,
        })
        print('      DB: created template (id=%d):' % qt.id, qt.name)
    else:
        print()
        print('    ! DB: DUPLICATE of template (id=%d):' % qt.id, qt.name)
        print()

    return qt


# /**
#  * Create metadata representing empty Question, OVERWRITE any existing data.
#  * @param questionName unique Uri-conformant name of question
#  * @return true on success
#  */
def createQuestionDB(questionName, template, q_graph=None, metrics={}) -> 'question URI':
    q = Questions.get_or_none(Questions.name == questionName)

    if not q:
        q = Questions.create(**{
            'name': questionName,
            'template': template,
            'origin': template.origin or "",  # copy origin
            'q_graph': q_graph,
            '_stage': STAGE_Q_CREATED,
            '_version': TOOL_VERSION,
        })
        print('      DB: created question (id=%d):' % q.id, q.name)
    else:
        print()
        print('    ! DB: DUPLICATE of question (id=%d):' % q.id, q.name)
        q.template = template
        q.q_graph = q_graph
        q._stage = STAGE_Q_CREATED
        q._version = TOOL_VERSION
        # print()

    # > add other metadata

    # get template instance (directly, thanks to ORM)
    # to write to it if no appropriate field found in `q`
    qt = q.template

    fields_of_collections = {
        'has_tag': (Tags, 'tag_bits'),
        'has_concept': (Concepts, 'concept_bits'),
        'has_law': (Laws, 'law_bits'),
        'has_violation': (Violations, 'violation_bits'),
    }

    need_save_qt = False

    for name, vals in metrics.items():
        # set value to Question's field
        if isinstance(vals, (list, tuple)):
            if (entity_field := fields_of_collections.get(name)):
                entity, name = entity_field  # note: rewrite `name`
                vals = names_to_bitmask(vals, entity)  # rewrite `vals`
            else:
                raise ValueError(('Bad combination of question data:', (name, vals)))
        if hasattr(q, name):
            if hasattr(qt, name) and name.endswith('_bits'):
                # copy concept bits from template
                vals |= getattr(qt, name) or 0
            setattr(q, name, vals)
        elif hasattr(qt, name):
            # set value to Template's field
            setattr(qt, name, vals)
            need_save_qt = True
        else:
            raise ValueError(('Bad combination of question/template data:', (name, vals)))

    q.save()
    if need_save_qt:
        qt.save()
    # < add other metadata

    print('      DB: updated q & qt metadata.')

    return q


def update_bit_field(row_instance, field_name: str, new_bits: int, replace_mode=False):
    """ add/set bits to instance; do not save it. """
    if not replace_mode:
        prev_value = getattr(row_instance, field_name)  # or 0
        if prev_value:
            new_bits |= prev_value

    setattr(row_instance, field_name, new_bits)


def create_or_update(key_fields: dict, set_fields: dict = None, entity=Concepts, update_always=False):
    """ search record by `key_fields` and update it with `set_fields` """
    record, created = entity.get_or_create(**key_fields)
    need_save = False
    # if created:
    if set_fields and (created or update_always):
        for k, v in set_fields.items():
            if v != getattr(record, k):
                print('updating %s.%s =>' % (entity.__name__, k), v)
                setattr(record, k, v)
                need_save = True
    if hasattr(record, 'bit') and not record.bit:
        # retrieve max bit value from table and then double it
        max_bit = entity.select(fn.Max(entity.bit)).scalar() or 1 / 2  # smallest bit is 1
        record.bit = int(2 * max_bit)  # fill bitmask's bit as desired by my businesslogic
        need_save = True
    if need_save:
        record.save()  # send updates to DB
    return record

    # Tags.get_or_none(Tags.name == 'ordering')
    # t = create_or_update(dict(name='supplementary'), Tags)
    # t = create_or_update(dict(name='loops'), dict(display_name='Циклы'), Concepts)


def names_to_bitmask(names: list[str], entity=Concepts):
    """gather bits from records (creating new rows when not exist)"""
    bitmask = 0
    for obj in (create_or_update({'name': name}, entity=entity) for name in names):
        try:
            bit = obj.bit
        except AttributeError:
            raise AttributeError('No `bit` column in entity of type %s: $s' % (type(obj).__name__), str(obj.__data__))
        bitmask |= bit
    return bitmask


# https://stackoverflow.com/a/8898977/12824563
def bits_on(n):
    """ iterate over set bits (1's) in int, ascending order
        ex. bits_on(109) --> 1 4 8 32 64
    """
    while n:
        b = n & (~n + 1)
        yield b
        n ^= b


def bitmask_to_names(bits: int, entity=Concepts) -> list[str]:
    """read bits from records (skipping values that not exist)"""
    names = []
    for bit in bits_on(bits):
        try:
            names.append(entity.get(entity.bit == bit).name)
        except DoesNotExist:  # peewee.DoesNotExist
            raise AttributeError('Not found entity of type %s with bit: $s' % (entity.__name__), str(bit))
    return names


def fill_db_with_new_entities():

    # 1. obtain entity names that must present in db tables with bitmask assigned

    from analyze_alg import get_reason_to_negative_laws_mappings

    # """ action_class_name -> {reason_name -> [violation names]} """
    reason_to_negative_laws_mappings = get_reason_to_negative_laws_mappings()

    class_names = sorted(set(reason_to_negative_laws_mappings.keys()))
    positive_laws = sorted(set(
        name
        for d in reason_to_negative_laws_mappings.values()
        for name in d.keys()
    ))
    negative_laws = sorted(set(
        name
        for d in reason_to_negative_laws_mappings.values()
        for name_list in d.values()
        for name in name_list
    ))

    # 2. Call bitmask constructor to create missing entries

    names_to_bitmask(class_names, Concepts)
    names_to_bitmask(positive_laws, Laws)
    names_to_bitmask(negative_laws, Violations)

    print('fill_db_with_new_entities() completed.')


if __name__ == "__main__":
    fill_db_with_new_entities()
