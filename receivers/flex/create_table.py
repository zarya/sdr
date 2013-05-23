from sqlalchemy import *
db = create_engine('sqlite:///flex.db')
db.echo = False
metadata = MetaData(db)
messages = Table('messages', metadata,
    Column('message_id', Integer, primary_key=True),
    Column('timestamp',Integer),
    Column('freq', String(10)),
    Column('cap', Integer),
    Column('type', String(4)),
    Column('message', String),
)
messages.create()
