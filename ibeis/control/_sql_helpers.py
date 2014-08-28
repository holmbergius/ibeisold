from __future__ import absolute_import, division, print_function
import utool
import re
from . import __SQLITE3__ as lite

(print, print_, printDBG, rrr, profile) = utool.inject(
    __name__, '[sql-helpers]')

# =======================
# Helper Functions
# =======================
PRINT_SQL = utool.get_flag(('--print-sql', '--verbose-sql'))
AUTODUMP = utool.get_flag('--auto-dump')
NOT_QUIET = not (utool.QUIET or utool.get_flag('--quiet-sql'))


def _results_gen(cur, get_last_id=False):
    """ HELPER - Returns as many results as there are.
    Careful. Overwrites the results once you call it.
    Basically: Dont call this twice.
    """
    if get_last_id:
        # The sqlite3_last_insert_rowid(D) interface returns the
        # <b> rowid of the most recent successful INSERT </b>
        # into a rowid table in D
        cur.execute('SELECT last_insert_rowid()', ())
    # Wraping fetchone in a generator for some pretty tight calls.
    while True:
        result = cur.fetchone()
        if not result:
            raise StopIteration()
        else:
            # Results are always returned wraped in a tuple
            result = result[0] if len(result) == 1 else result
            #if get_last_id and result == 0:
            #    result = None
            yield result


def _unpacker(results_):
    """ HELPER: Unpacks results if unpack_scalars is True """
    results = None if len(results_) == 0 else results_[0]
    assert len(results_) < 2, 'throwing away results! { %r }' % (results_)
    return results


# =======================
# SQL Context Class
# =======================


class SQLExecutionContext(object):
    """ A good with context to use around direct sql calls
    """
    def __init__(context, db, operation, num_params=None, auto_commit=True,
                 start_transaction=False, verbose=PRINT_SQL):
        context.auto_commit = auto_commit
        context.db = db  # Reference to sqldb
        context.operation = operation
        context.num_params = num_params
        context.start_transaction = start_transaction
        #context.__dict__.update(locals())  # Too mystic?
        context.operation_type = get_operation_type(operation)  # Parse the optype
        context.verbose = verbose

    def __enter__(context):
        """ Checks to see if the operating will change the database """
        #utool.printif(lambda: '[sql] Callers: ' + utool.get_caller_name(range(3, 6)), DEBUG)
        if context.num_params is not None:
            context.operation_lbl = ('[sql] execute num_params=%d optype=%s: '
                                       % (context.num_params, context.operation_type))
        else:
            context.operation_lbl = '[sql] executeone optype=%s: ' % (context.operation_type)
        # Start SQL Transaction
        context.cur = context.db.connection.cursor()  # HACK in a new cursor
        if context.start_transaction:
            # http://stackoverflow.com/questions/9573768/understanding-python-sqlite-mechanics-in-multi-module-enviroments
            context.cur.execute('BEGIN', ())
        if context.verbose or PRINT_SQL:
            print(context.operation_lbl)
            if context.verbose:
                print('[sql] operation=\n' + context.operation)
        # Comment out timeing code
        if __debug__:
            if NOT_QUIET and (PRINT_SQL or context.verbose):
                context.tt = utool.tic(context.operation_lbl)
        return context

    # --- with SQLExecutionContext: statment code happens here ---

    def execute_and_generate_results(context, params):
        """ HELPER FOR CONTEXT STATMENT """
        try:
            context.cur.execute(context.operation, params)
        except lite.Error as ex:
            print('[sql.Error] %r' % (type(ex),))
            print('[sql.Error] params=<%r>' % (params,))
            raise
        is_insert = context.operation_type.startswith('INSERT')
        return _results_gen(context.cur, get_last_id=is_insert)

    def __exit__(context, type_, value, trace):
        if __debug__:
            if NOT_QUIET and (PRINT_SQL or context.verbose):
                utool.toc(context.tt)
        if trace is not None:
            # An SQLError is a serious offence.
            print('[sql] FATAL ERROR IN QUERY CONTEXT')
            print('[sql] operation=\n' + context.operation)
            context.db.dump()  # Dump on error
            print('[sql] Error in context manager!: ' + str(value))
            return False  # return a falsey value on error
        else:
            # Commit the transaction
            if context.auto_commit:
                context.db.connection.commit()
                #context.db.commit(verbose=False)


@profile
def get_operation_type(operation):
    """
    Parses the operation_type from an SQL operation
    """
    operation = ' '.join(operation.split('\n')).strip()
    operation_type = operation.split(' ')[0].strip()
    if operation_type.startswith('SELECT'):
        operation_args = utool.str_between(operation, operation_type, 'FROM').strip()
    elif operation_type.startswith('INSERT'):
        operation_args = utool.str_between(operation, operation_type, '(').strip()
    elif operation_type.startswith('UPDATE'):
        operation_args = utool.str_between(operation, operation_type, 'FROM').strip()
    elif operation_type.startswith('DELETE'):
        operation_args = utool.str_between(operation, operation_type, 'FROM').strip()
    elif operation_type.startswith('CREATE'):
        operation_args = utool.str_between(operation, operation_type, '(').strip()
    else:
        operation_args = None
    operation_type += ' ' + operation_args.replace('\n', ' ')
    return operation_type.upper()


@profile
def sanatize_sql(db, tablename, columns=None):
    """ Sanatizes an sql tablename and column. Use sparingly """
    tablename = re.sub('[^a-z_0-9]', '', tablename)
    valid_tables = db.get_table_names()
    if tablename not in valid_tables:
        raise Exception('UNSAFE TABLE: tablename=%r' % tablename)
    if columns is None:
        return tablename
    else:
        def _sanitize_sql_helper(column):
            column = re.sub('[^a-z_0-9]', '', column)
            valid_columns = db.get_column_names(tablename)
            if column not in valid_columns:
                raise Exception('UNSAFE COLUMN: tablename=%r column=%r' %
                                (tablename, column))
                return None
            else:
                return column

        columns = [_sanitize_sql_helper(column) for column in columns]
        columns = [column for column in columns if columns is not None]

        return tablename, columns
