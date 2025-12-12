"""add website scraping support

Revision ID: 540a518e2b30
Revises: c8d7004725a4
Create Date: 2025-11-13 08:01:26.801682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '540a518e2b30'
down_revision: Union[str, Sequence[str], None] = 'c8d7004725a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support website scraping."""

    # 1. Create source_type enum
    source_type_enum = postgresql.ENUM('kindle', 'website', 'pdf', name='source_type')
    source_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add source_type column with default 'kindle' (for existing rows)
    op.add_column('books', sa.Column('source_type', source_type_enum, nullable=False, server_default='kindle'))

    # 3. Add new metadata columns for website scraping
    op.add_column('books', sa.Column('source_url', sa.String(), nullable=True))  # Generic source URL
    op.add_column('books', sa.Column('source_domain', sa.String(255), nullable=True))  # Website domain
    op.add_column('books', sa.Column('published_date', sa.DateTime(), nullable=True))  # Website publish date
    op.add_column('books', sa.Column('word_count', sa.Integer(), nullable=True))  # Total word count
    op.add_column('books', sa.Column('page_count', sa.Integer(), nullable=True))  # Generic page count (Kindle pages OR web pages)

    # 4. Make Kindle-specific fields nullable (websites won't have these)
    op.alter_column('books', 'kindle_url', nullable=True)
    op.alter_column('books', 'total_screenshots', nullable=True, server_default=None)
    op.alter_column('books', 'capture_date', nullable=True)

    # 5. Populate source_url from kindle_url for existing records
    op.execute("UPDATE books SET source_url = kindle_url WHERE source_type = 'kindle'")

    # 6. Add indexes for performance
    op.create_index('idx_books_source_type', 'books', ['source_type'])
    op.create_index('idx_books_source_domain', 'books', ['source_domain'])
    op.create_index('idx_books_published_date', 'books', ['published_date'])

    # 7. Create failed_scrapes table for retry functionality
    op.create_table(
        'failed_scrapes',
        sa.Column('id', sa.Uuid(), nullable=False, primary_key=True),
        sa.Column('book_id', sa.Uuid(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_failed_scrapes_book_id', 'failed_scrapes', ['book_id'])
    op.create_index('idx_failed_scrapes_url', 'failed_scrapes', ['url'])


def downgrade() -> None:
    """Downgrade schema to remove website scraping support."""

    # Drop failed_scrapes table
    op.drop_index('idx_failed_scrapes_url', table_name='failed_scrapes')
    op.drop_index('idx_failed_scrapes_book_id', table_name='failed_scrapes')
    op.drop_table('failed_scrapes')

    # Drop indexes
    op.drop_index('idx_books_published_date', table_name='books')
    op.drop_index('idx_books_source_domain', table_name='books')
    op.drop_index('idx_books_source_type', table_name='books')

    # Restore Kindle-specific fields to NOT NULL
    op.alter_column('books', 'capture_date', nullable=True)  # Keep nullable
    op.alter_column('books', 'total_screenshots', nullable=False, server_default='0')
    op.alter_column('books', 'kindle_url', nullable=False)

    # Drop new columns
    op.drop_column('books', 'page_count')
    op.drop_column('books', 'word_count')
    op.drop_column('books', 'published_date')
    op.drop_column('books', 'source_domain')
    op.drop_column('books', 'source_url')
    op.drop_column('books', 'source_type')

    # Drop enum type
    source_type_enum = postgresql.ENUM('kindle', 'website', 'pdf', name='source_type')
    source_type_enum.drop(op.get_bind())
