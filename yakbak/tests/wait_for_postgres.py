#!/usr/bin/env python
from contextlib import closing
import os
import sys
import time

import psycopg2

postgres_uri = (
    f"postgresql://yakbak:y4kb4k@{os.environ['POSTGRES_HOST']}:"
    f"{os.environ['POSTGRES_5432_TCP_PORT']}/yakbak_tox_test"
)

for _ in range(5):
    try:
        conn = psycopg2.connect(postgres_uri)
        with closing(conn.cursor()) as curs:
            curs.execute("select 1")
            curs.fetchall()
            break
    except Exception:
        pass
    time.sleep(1)
else:
    sys.exit("PostgreSQL did not come up within 5 seconds")
