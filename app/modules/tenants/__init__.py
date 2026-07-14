"""Módulo de Empresas (Tenants) e Filiais.

Base do modelo multiempresa (SaaS). Um *tenant* representa uma locadora; cada
tenant possui uma ou mais filiais/unidades operacionais. O isolamento de dados
entre tenants é garantido por Row-Level Security no PostgreSQL.
"""
