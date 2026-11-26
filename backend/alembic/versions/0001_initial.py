"""Trust Gate V1 persistence."""
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None
from alembic import op
from backend.app.models import Base
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
