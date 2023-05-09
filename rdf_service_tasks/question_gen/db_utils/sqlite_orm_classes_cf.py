from peewee import *

database = SqliteDatabase('c:/data/compp/control_flow_work.sqlite3')
# database = SqliteDatabase('c:/data/compp/expression_work.sqlite3')

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class Concepts(BaseModel):
    base_ids = TextField(null=True)
    bit = IntegerField(null=True, unique=True)
    child_ids = TextField(null=True)
    display_name = TextField(null=True)
    flags = IntegerField(null=True)
    name = TextField(null=True)

    class Meta:
        table_name = 'concepts'

class Laws(BaseModel):
    base_ids = TextField(null=True)
    bit = IntegerField(null=True, unique=True)
    child_ids = TextField(null=True)
    display_name = TextField(null=True)
    flags = IntegerField(null=True)
    name = TextField(null=True)

    class Meta:
        table_name = 'laws'

class Templates(BaseModel):
    _stage = IntegerField(null=True)
    _version = IntegerField(null=True)
    actions_count = IntegerField(null=True)
    concept_bits = IntegerField(null=True)
    cyclomatic = IntegerField(null=True)
    max_if_branches = IntegerField(null=True)
    max_loop_nesting_depth = IntegerField(null=True)
    name = TextField(null=True)
    origin = TextField(null=True)
    nesting_depth = IntegerField(null=True)
    qt_graph = TextField(null=True)
    qt_s_graph = TextField(null=True)
    src_path = TextField(null=True)
    structural_complexity = FloatField(null=True)

    class Meta:
        table_name = 'templates'

class Questions(BaseModel):
    _stage = IntegerField(null=True)
    _version = IntegerField(null=True)
    concept_bits = IntegerField(null=True)
    distinct_errors_count = IntegerField(null=True)
    integral_complexity = FloatField(null=True)
    law_bits = IntegerField(null=True)
    name = TextField(null=True)
    origin = TextField(null=True)
    q_data_graph = TextField(null=True)
    q_graph = TextField(null=True)
    solution_steps = IntegerField(null=True)
    solution_structural_complexity = FloatField(null=True)
    tag_bits = IntegerField(null=True)
    template = ForeignKeyField(column_name='template_id', field='id', model=Templates)
    trace_concept_bits = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    ###
    trace_features_json = TextField(constraints=[SQL("DEFAULT '{}'")], null=True)
    ###
    violation_bits = IntegerField(null=True)
    formulation = TextField(constraints=[SQL("DEFAULT ''")], null=True)

    class Meta:
        table_name = 'questions'

class SqliteSequence(BaseModel):
    name = BareField(null=True)
    seq = BareField(null=True)

    class Meta:
        table_name = 'sqlite_sequence'
        primary_key = False

class Tags(BaseModel):
    base_ids = TextField(null=True)
    bit = IntegerField(null=True, unique=True)
    child_ids = TextField(null=True)
    display_name = TextField(null=True)
    flags = IntegerField(null=True)
    name = TextField(null=True)

    class Meta:
        table_name = 'tags'

class Violations(BaseModel):
    base_ids = TextField(null=True)
    bit = IntegerField(null=True, unique=True)
    child_ids = TextField(null=True)
    display_name = TextField(null=True)
    flags = IntegerField(null=True)
    name = TextField(null=True)

    class Meta:
        table_name = 'violations'

