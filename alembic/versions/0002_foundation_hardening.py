"""Endurecimento da fundação: RLS em auditoria, uniques parciais e associações.

Revision ID: 0002_foundation_hardening
Revises: 0001_foundation
Create Date: 2026-07-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_foundation_hardening"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ASSOCIATION_TABLES = ("role_permissions", "user_roles", "user_filiais")


def _enable_audit_rls() -> None:
    """Aplica RLS em ``audit_logs`` (tenant enxerga apenas os próprios eventos)."""
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON audit_logs
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR (
                tenant_id IS NULL
                AND COALESCE(current_setting('app.current_tenant_id', true), '') = ''
            )
        )
        """
    )


def upgrade() -> None:
    # Associações N:N não usam soft delete — remove a coluna e o risco de unique
    # bloqueando religações após remoção lógica.
    for table in _ASSOCIATION_TABLES:
        op.drop_column(table, "deleted_at")

    # Uniques parciais: soft-deleted não ocupa o índice de negócio.
    op.drop_constraint("uq_users_tenant_id_email", "users", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_tenant_id_email_active
        ON users (tenant_id, email)
        WHERE deleted_at IS NULL
        """
    )

    op.drop_constraint("uq_filiais_tenant_id_code", "filiais", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_filiais_tenant_id_code_active
        ON filiais (tenant_id, code)
        WHERE deleted_at IS NULL
        """
    )

    op.drop_constraint("uq_roles_tenant_id_slug", "roles", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_roles_tenant_id_slug_active
        ON roles (tenant_id, slug)
        WHERE deleted_at IS NULL
        """
    )

    op.drop_constraint("uq_tenants_slug", "tenants", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tenants_slug_active
        ON tenants (slug)
        WHERE deleted_at IS NULL
        """
    )

    # CNPJ de tenant: unique parcial (NULL/soft-deleted não colidem indevidamente).
    op.drop_constraint("uq_tenants_cnpj", "tenants", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tenants_cnpj_active
        ON tenants (cnpj)
        WHERE deleted_at IS NULL AND cnpj IS NOT NULL
        """
    )

    _enable_audit_rls()


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_logs")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS uq_tenants_cnpj_active")
    op.execute("DROP INDEX IF EXISTS uq_tenants_slug_active")
    op.execute("DROP INDEX IF EXISTS uq_roles_tenant_id_slug_active")
    op.execute("DROP INDEX IF EXISTS uq_filiais_tenant_id_code_active")
    op.execute("DROP INDEX IF EXISTS uq_users_tenant_id_email_active")

    op.create_unique_constraint("uq_tenants_cnpj", "tenants", ["cnpj"])
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])
    op.create_unique_constraint("uq_roles_tenant_id_slug", "roles", ["tenant_id", "slug"])
    op.create_unique_constraint("uq_filiais_tenant_id_code", "filiais", ["tenant_id", "code"])
    op.create_unique_constraint("uq_users_tenant_id_email", "users", ["tenant_id", "email"])

    from sqlalchemy import DateTime
    from sqlalchemy import Column

    for table in _ASSOCIATION_TABLES:
        op.add_column(table, Column("deleted_at", DateTime(timezone=True), nullable=True))
