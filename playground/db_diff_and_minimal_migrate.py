## Saving here in the playground -
# to use, move it to root of directory :D
####

import sqlite3
import buddy.db
import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import re
import logging
from textwrap import dedent

# TODO: why the heck does logging.info() not work anymore
logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)
# ----> console info messages require these lines <----
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(level)

# add ch to logger
logger.addHandler(ch)

logger.debug('debug message')
logger.info('info message')
logger.warning('warn message')
logger.error('error message')
logger.critical('critical message')

logging.debug('ing: debug message')
logging.info('ing: info message')
logging.warning('ing: warn message')
logging.error('ing: error message')
logging.critical('ing: critical message')

# inspired by https://david.rothlis.net/declarative-schema-migration-for-sqlite/
# considering it for our migration strategy.
# Some funcs borrowed directly from it.
n_changes = 0
allow_deletions = False

def log_execute(db, msg, sql, args=None):
        global n_changes
        # It's important to log any changes we're making to the database for
        # forensics later
        msg_tmpl = "Database migration: %s with SQL:\n%s"
        msg_argv = (msg, _left_pad(dedent(sql)))
        if args:
            msg_tmpl += " args = %r"
            msg_argv += (args,)
        else:
            args = []
        logger.info(msg_tmpl, *msg_argv)
        db.execute(sql, args)
        n_changes += 1

def _left_pad(text, indent="    "):
    """Maybe I can find a package in pypi for this?"""
    return "\n".join(indent + line for line in text.split('\n'))

def normalise_sql(sql):
    # Remove comments:
    sql = re.sub(r'--[^\n]*\n', "", sql)
    # Normalise whitespace:
    sql = re.sub(r'\s+', " ", sql)
    sql = re.sub(r" *([(),]) *", r"\1", sql)
    # Remove unnecessary quotes
    sql = re.sub(r'"(\w+)"', r"\1", sql)
    return sql.strip()


def test_normalise_sql():
    assert normalise_sql("""\
        CREATE TABLE "Node"( -- This is my table
            -- There are many like it but this one is mine
            A b, C D, "E F G", h)""") == \
        'CREATE TABLE Node(A b,C D,"E F G",h)'

def _migrate_pragma(pristine_db, real_db, pragma):
        pristine_val = pristine_db.execute(
            "PRAGMA %s" % pragma).fetchone()[0]
        val = real_db.execute("PRAGMA %s" % pragma).fetchone()[0]

        if val != pristine_val:
            log_execute(
                 real_db,
                "Set %s to %i from %i" % (pragma, pristine_val, val),
                "PRAGMA %s = %i" % (pragma, pristine_val))

        return pristine_val

# load the pristine DB in memory
IN_MEMORY_SQLITE_CONN_STR = "sqlite:///:memory:"
pristine_db: Engine = sqlalchemy.create_engine(IN_MEMORY_SQLITE_CONN_STR)

buddy.db.DB_ENGINE = pristine_db
buddy.db.create_tables(pristine_db)

pristine_tables = dict(pristine_db.execute('''\
SELECT name, sql FROM sqlite_master
WHERE type = "table" AND name != "sqlite_sequence"''').fetchall())
print('===Pristine Tables====')
for t in pristine_tables:
    print(t)
pristine_indices = dict(pristine_db.execute("""\
            SELECT name, sql FROM sqlite_master
            WHERE type = \"index\"""").fetchall())

WB_DATA_DIR="./workflow-buddy-local/db/"
DB_FILE_NAME = "workflow_buddy.db"
LOCAL_SQLITE_DB = f"{WB_DATA_DIR}{DB_FILE_NAME}"
with sqlite3.connect(LOCAL_SQLITE_DB) as real_db:
    cur = real_db.execute("select count(1) from slack_installations;")
    row_num = cur.fetchone()[0]

    # at some versions, sqlite_master = sqlite_schema
    real_tables = dict(real_db.execute('''\
    SELECT name, sql FROM sqlite_master
    WHERE type = "table" AND name != "sqlite_sequence"''').fetchall())
    print('====\nReal Tables')
    for t in real_tables:
        print(t)

    new_tables = set(pristine_tables.keys()) - set(real_tables.keys())
    removed_tables = set(real_tables.keys()) - set(pristine_tables.keys())
    print('New,Removed', new_tables, removed_tables)

    modified_tables = set(
        name for name, sql in pristine_tables.items()
        if normalise_sql(real_tables.get(name, "")) != normalise_sql(sql))
    print('Modifed', modified_tables)

    for tbl_name in modified_tables:
        # The SQLite documentation insists that we create the new table and
        # rename it over the old rather than moving the old out of the way
        # and then creating the new
        create_table_sql = pristine_tables[tbl_name]
        create_table_sql = re.sub(r"\b%s\b" % re.escape(tbl_name),
                                    tbl_name + "_migration_new",
                                    create_table_sql)
        log_execute(
            real_db,
            "Columns change: Create table %s with updated schema" %
            tbl_name, create_table_sql)

        cols = set([
            x[1] for x in real_db.execute(
                "PRAGMA table_info(%s)" % tbl_name)])
        pristine_cols = set([
            x[1] for x in
            pristine_db.execute("PRAGMA table_info(%s)" % tbl_name)])

        print('Cols, pristine cols', cols, pristine_cols)
        removed_columns = cols - pristine_cols
        print('Removed cols', removed_columns)
        if not allow_deletions and removed_columns:
            logger.warning(
                "Database migration: Refusing to remove columns %r from "
                "table %s.  Current cols are %r attempting migration to %r",
                removed_columns, tbl_name, cols, pristine_cols)
            raise RuntimeError(
                "Database migration: Refusing to remove columns %r from "
                "table %s" % (removed_columns, tbl_name))

        logger.info("cols: %s, pristine_cols: %s", cols, pristine_cols)
        log_execute(
             real_db,
            "Migrate data for table %s" % tbl_name, """\
            INSERT INTO {tbl_name}_migration_new ({common})
            SELECT {common} FROM {tbl_name}""".format(
                tbl_name=tbl_name,
                common=", ".join(cols.intersection(pristine_cols))))

        # Don't need the old table any more
        log_execute(
             real_db,
            "Drop old table %s now data has been migrated" % tbl_name,
            "DROP TABLE %s" % tbl_name)

        log_execute(
             real_db,
            "Columns change: Move new table %s over old" % tbl_name,
            "ALTER TABLE %s_migration_new RENAME TO %s" % (
                tbl_name, tbl_name))

        # Migrate the indices

    logger.info('Checking indices...')
    indices = dict(real_db.execute("""\
        SELECT name, sql FROM sqlite_master
        WHERE type = \"index\"""").fetchall())
    for name in set(indices.keys()) - set(pristine_indices.keys()):
        log_execute(real_db, "Dropping obsolete index %s" % name,
                            "DROP INDEX %s" % name)
    for name, sql in pristine_indices.items():
        if name not in indices:
            log_execute(real_db, "Creating new index %s" % name, sql)
        elif sql != indices[name]:
            log_execute(
                real_db,
                "Index %s changed: Dropping old version" % name,
                "DROP INDEX %s" % name)
            log_execute(
                real_db,
                "Index %s changed: Creating updated version in its place" %
                name, sql)

    logger.info('migrate pragma')
    _migrate_pragma(pristine_db, real_db, 'user_version')

    if pristine_db.execute("PRAGMA foreign_keys").fetchone()[0]:
        if real_db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError(
                "Database migration: Would fail foreign_key_check")
