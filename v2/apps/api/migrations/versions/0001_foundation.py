"""Private application schema. No browser Data API grants."""
from alembic import op
from sqlalchemy import text
from plutus.db import metadata
revision='0001_foundation'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    conn=op.get_bind()
    metadata.create_all(conn)
    if conn.dialect.name=='postgresql':
        # Dedicated backend DB role must own tables or have explicit policies. Browser roles have no access.
        for table in metadata.sorted_tables:
            op.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
            op.execute(text(f'REVOKE ALL ON TABLE "{table.name}" FROM PUBLIC, anon, authenticated'))

def downgrade():
    raise RuntimeError('Destructive automatic downgrade disabled; use reviewed backup restoration.')
