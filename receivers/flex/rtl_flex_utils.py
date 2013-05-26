# File with utils for rtl_flex
# Database support for rtl_flex (to insert the messages into a database table)
# Part of this file is GNURadio code

from gnuradio import gr
import gnuradio.gr.gr_threading as _threading
from string import split, join, printable
import time
try:
    import sqlalchemy
except:
    print "No database support"
    pass

def make_trans_table():
    table = 256 * ['.']
    for i in range(256):
        if (i < 32):
            table[i] = '.'
        else:
            table[i] = chr(i)
    return ''.join(table)

_trans_table = make_trans_table()

def make_printable(s):
    return s.translate(_trans_table)

def filter_non_printable(str):
  return ''.join([c for c in str if ord(c) > 31 or ord(c) == 9])

class queue_runner(_threading.Thread):
    def __init__(self, msgq, options):
        _threading.Thread.__init__(self)
        self.msgq = msgq
        self.done = False
        self.options = options
        if options.database != False:
            self.db = sqlalchemy.create_engine(options.database)
            metadata = sqlalchemy.MetaData(self.db)
            self.table = sqlalchemy.Table('messages', metadata, autoload=True)
        self.start()

    def run(self):
        while 1:
            msg = self.msgq.delete_head() # Blocking read
            if msg.type() != 0:
                break

            page = join(split(msg.to_string(), chr(128)), '|')
            data = split(msg.to_string(), chr(128))
            if self.options.database != False:
                i = self.table.insert()
                i.execute(
                    timestamp=int(time.time()), freq=data[0], cap=data[1], type=data[2],message=filter_non_printable(data[3])
                )
            s = make_printable(page)
            print msg.type(), s

    def end(self):
        self.msgq.insert_tail(gr.message(1))
        self.done = True
