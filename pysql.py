#################################
#
# Simple script to use within Docker container for querying local SQlite DB
#
#################################

import argparse
import sqlite3
import os

from typing import List

# DEFAULT query - select * from slack_installations limit 5;
LOCAL_DB_FILE_PATH = "workflow-buddy-local/db/workflow_buddy.db"
DOCKER_FILE_PATH = "/usr/app/data/workflow_buddy.db"
def main(args: argparse.Namespace):
    query_stmt = args.sql_query
    print('[*] Running query', query_stmt)
    print("-------------------")
    db_file_path = LOCAL_DB_FILE_PATH if args.local else DOCKER_FILE_PATH
    if not os.path.isfile(db_file_path):
        raise ValueError(f'File doesnt exist!! -> {db_file_path}')
    conn_str = f"file:{db_file_path}?mode=ro"
    with sqlite3.connect(conn_str, uri=True) as conn:
        # https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query
        # conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query_stmt)
        data: List[sqlite3.Row] = cursor.fetchall()
        print(f'[*] Returned {len(data)} rows...')
        for row in data:
            row_as_dict = {cursor.description[i][0]:row[i] for i in range(len(row))}
            print(row_as_dict)
            # print(row)
        print(f'[*] Finished printing {len(data)} rows.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="pysql")
    parser.add_argument("sql_query")
    parser.add_argument('--local', '-l', action='store_true')
    args = parser.parse_args()
    main(args)
