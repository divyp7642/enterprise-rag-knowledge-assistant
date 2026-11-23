
"""add multi tenant organization and user models

Revision ID: ae253962ef19
Revises:
Create Date: 2026-11-20 18:33:24.663486
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ae253962ef19"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations.
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("name"),
    )

    op.create_index(
        "ix_organizations_id",
        "organizations",
        ["id"],
    )

    # 2. Create users.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("email"),
    )

    op.create_index("ix_users_id", "users", ["id"])
    op.create_index(
        "ix_users_organization_id",
        "users",
        ["organization_id"],
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 3. Add nullable ownership columns temporarily.
    op.add_column(
        "documents",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "documents",
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
    )

    connection = op.get_bind()

    # 4. Create ownership records only if legacy documents exist.
    existing_documents = connection.execute(
        sa.text("SELECT COUNT(*) FROM documents")
    ).scalar_one()

    if existing_documents > 0:
        organization_id = connection.execute(
            sa.text(
                """
                INSERT INTO organizations (name)
                VALUES ('Legacy Documents Organization')
                RETURNING id
                """
            )
        ).scalar_one()

        user_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (
                    organization_id,
                    email,
                    password_hash
                )
                VALUES (
                    :organization_id,
                    :email,
                    :password_hash
                )
                RETURNING id
                """
            ),
            {
                "organization_id": organization_id,
                "email": "legacy-import@invalid.example",
                "password_hash": "!disabled-legacy-account",
            },
        ).scalar_one()

        connection.execute(
            sa.text(
                """
                UPDATE documents
                SET organization_id = :organization_id,
                    uploaded_by = :user_id
                WHERE organization_id IS NULL
                """
            ),
            {
                "organization_id": organization_id,
                "user_id": user_id,
            },
        )

    # 5. Require ownership for all documents.
    op.alter_column(
        "documents",
        "organization_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "documents",
        "uploaded_by",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 6. Add foreign keys and indexes.
    op.create_foreign_key(
        "fk_documents_organization_id",
        "documents",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_documents_uploaded_by",
        "documents",
        "users",
        ["uploaded_by"],
        ["id"],
    )

    op.create_index(
        "ix_documents_organization_id",
        "documents",
        ["organization_id"],
    )

    op.create_index(
        "ix_documents_uploaded_by",
        "documents",
        ["uploaded_by"],
    )


def downgrade() -> None:
    # Reverses schema changes, but does not restore
    # the original ownership information.
    op.drop_index("ix_documents_uploaded_by", "documents")
    op.drop_index("ix_documents_organization_id", "documents")

    op.drop_constraint(
        "fk_documents_uploaded_by",
        "documents",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_documents_organization_id",
        "documents",
        type_="foreignkey",
    )

    op.drop_column("documents", "uploaded_by")
    op.drop_column("documents", "organization_id")

    op.drop_index("ix_users_email", "users")
    op.drop_index("ix_users_organization_id", "users")
    op.drop_index("ix_users_id", "users")
    op.drop_table("users")

    op.drop_index("ix_organizations_id", "organizations")
    op.drop_table("organizations")
