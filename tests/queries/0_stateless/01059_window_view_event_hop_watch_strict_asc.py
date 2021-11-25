#!/usr/bin/env python3
import os
import sys
import signal

CURDIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(CURDIR, 'helpers'))

from client import client, prompt, end_of_block

log = None
# uncomment the line below for debugging
#log=sys.stdout

with client(name='client1>', log=log) as client1, client(name='client2>', log=log) as client2:
    client1.expect(prompt)
    client2.expect(prompt)

    client1.send('SET allow_experimental_window_view = 1')
    client1.expect(prompt)
    client1.send('SET window_view_heartbeat_interval = 1')
    client1.expect(prompt)

    client1.send('DROP TABLE IF EXISTS test.mt')
    client1.expect(prompt)
    client1.send('DROP TABLE IF EXISTS test.wv NO DELAY')
    client1.expect(prompt)

    client1.send('CREATE TABLE test.mt(a Int32, timestamp DateTime) ENGINE=MergeTree ORDER BY tuple()')
    client1.expect(prompt)
    client1.send("CREATE WINDOW VIEW test.wv WATERMARK=STRICTLY_ASCENDING AS SELECT count(a) AS count, HOP_END(wid) as w_end FROM test.mt GROUP BY HOP(timestamp, INTERVAL '2' SECOND, INTERVAL '3' SECOND, 'US/Samoa') AS wid;")
    client1.expect(prompt)

    client1.send('WATCH test.wv')

    client2.send("INSERT INTO test.mt VALUES (1, '1990/01/01 12:00:00');")
    client2.expect("Ok.")
    client2.send("INSERT INTO test.mt VALUES (1, '1990/01/01 12:00:05');")
    client2.expect("Ok.")
    client1.expect('1*1990-01-01 12:00:02' + end_of_block)
    client1.expect('Progress: 1.00 rows.*\)')

    client2.send("INSERT INTO test.mt VALUES (1, '1990/01/01 12:00:10');")
    client2.expect("Ok.")
    client1.expect('1*1990-01-01 12:00:06' + end_of_block)
    client1.expect('1*1990-01-01 12:00:08' + end_of_block)
    client1.expect('Progress: 3.00 rows.*\)')

    # send Ctrl-C
    client1.send('\x03', eol='')
    match = client1.expect('(%s)|([#\$] )' % prompt)
    if match.groups()[1]:
        client1.send(client1.command)
        client1.expect(prompt)
