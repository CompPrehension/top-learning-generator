# sqlite_questions_metadata.py

from db_utils.sqlite_orm_classes import *


# write to `_version` column to track data generated with older scripts
PROCESSING_TOOLS_VERSION = 1



def get_or_create(key_fields: dict, set_fields: dict=None, entity=Concepts):
    record, created = entity.get_or_create(**key_fields)
    need_save = False
#     if created:
    if set_fields:
        for k, v in set_fields.items():
            if v != getattr(record, k):
                print('updating %s.%s =>' % (entity.__name__, k), v)
                setattr(record, k, v)
                need_save = True
    if hasattr(record, 'bit') and not record.bit:
        # retrieve max bit value from table and then double it
        max_bit = entity.select(fn.Max(entity.bit)).scalar() or 1/2;  # smallest bit is 1
        record.bit = int(2 * max_bit)  # fill bitmask's bit as desired by my businesslogic
        need_save = True
    if need_save:
        record.save()  # send updates to DB
    return record

	# Tags.get_or_none(Tags.name == 'ordering')
	# t = get_or_create(dict(name='supplementary'), Tags)
	# t = get_or_create(dict(name='loops'), dict(display_name='Циклы'), Concepts)


def names_to_bitmask(names: list[str], entity=Concepts):
    '''gaters bits from records (creating new rows when not exist)'''
    bitmask = 0
    for obj in (get_or_create({'name': name}, entity=entity) for name in names):
        try:
            bit = obj.bit
        except AttributeError:
            raise AttributeError('No `bit` column in entity of type %s: $s' % (type(obj).__name__), str(obj.__data__))
        bitmask |= bit
    return bitmask


