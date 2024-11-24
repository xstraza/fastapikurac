from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3980edabfb38'
down_revision = 'd94cc842e815'
branch_labels = None
depends_on = None


def upgrade():
    # Add the `id` column with a default value generated using `uuid_generate_v4()`
    op.add_column(
        'mri_asset_outputs',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('uuid_generate_v4()'))
    )
    
    # Drop the old primary key constraint
    op.drop_constraint('mri_asset_outputs_pkey', 'mri_asset_outputs', type_='primary')
    
    # Create a new primary key on `id`
    op.create_primary_key('pk_mri_asset_outputs', 'mri_asset_outputs', ['id'])


def downgrade():
    # Remove the `id` column and revert to the original primary key
    op.drop_constraint('pk_mri_asset_outputs', 'mri_asset_outputs', type_='primary')
    op.create_primary_key('mri_asset_outputs_pkey', 'mri_asset_outputs', ['date'])
    op.drop_column('mri_asset_outputs', 'id')
