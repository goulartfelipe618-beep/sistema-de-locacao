"""Fundação: multiempresa, identidade/RBAC e auditoria (com RLS).

Revision ID: 0001_foundation
Revises:
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tabelas escopadas por tenant que recebem Row-Level Security.
_TENANT_SCOPED_TABLES = (
    "filiais",
    "roles",
    "users",
    "role_permissions",
    "user_roles",
    "user_filiais",
)


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _enable_rls(table: str) -> None:
    """Habilita e força RLS, criando a política de isolamento por tenant."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )


def upgrade() -> None:
    # ------------------------------------------------------------- tenants
    op.create_table(
        "tenants",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("trade_name", sa.String(200), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(50), nullable=False, server_default="standard"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.UniqueConstraint("cnpj", name="uq_tenants_cnpj"),
    )

    # ------------------------------------------------------------- filiais
    op.create_table(
        "filiais",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_headquarters", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("zip_code", sa.String(8), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("number", sa.String(20), nullable=True),
        sa.Column("complement", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_filiais"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_filiais_tenant_id_tenants",
                                ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_filiais_tenant_id_code"),
    )
    op.create_index("ix_filiais_tenant_id", "filiais", ["tenant_id"])

    # --------------------------------------------------------- permissions
    op.create_table(
        "permissions",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("code", sa.String(150), nullable=False),
        sa.Column("module", sa.String(60), nullable=False),
        sa.Column("resource", sa.String(60), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    # --------------------------------------------------------------- roles
    op.create_table(
        "roles",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_roles_tenant_id_tenants",
                                ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_roles_tenant_id_slug"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])

    # --------------------------------------------------------------- users
    op.create_table(
        "users",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_users_tenant_id_tenants",
                                ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ---------------------------------------------------- role_permissions
    op.create_table(
        "role_permissions",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_role_permissions"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],
                                name="fk_role_permissions_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"],
                                name="fk_role_permissions_role_id_roles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"],
                                name="fk_role_permissions_permission_id_permissions",
                                ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_perm"),
    )
    op.create_index("ix_role_permissions_tenant_id", "role_permissions", ["tenant_id"])
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ----------------------------------------------------------- user_roles
    op.create_table(
        "user_roles",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],
                                name="fk_user_roles_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                name="fk_user_roles_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"],
                                name="fk_user_roles_role_id_roles", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_tenant_id", "user_roles", ["tenant_id"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # --------------------------------------------------------- user_filiais
    op.create_table(
        "user_filiais",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_filiais"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],
                                name="fk_user_filiais_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                name="fk_user_filiais_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["filial_id"], ["filiais.id"],
                                name="fk_user_filiais_filial_id_filiais", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "filial_id", name="uq_user_filiais_user_filial"),
    )
    op.create_index("ix_user_filiais_tenant_id", "user_filiais", ["tenant_id"])
    op.create_index("ix_user_filiais_user_id", "user_filiais", ["user_id"])
    op.create_index("ix_user_filiais_filial_id", "user_filiais", ["filial_id"])

    # ---------------------------------------------------------- audit_logs
    op.create_table(
        "audit_logs",
        _uuid_pk(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"])
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ------------------------------------------------- Row-Level Security
    for table in _TENANT_SCOPED_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in _TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_table("audit_logs")
    op.drop_table("user_filiais")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("filiais")
    op.drop_table("tenants")
