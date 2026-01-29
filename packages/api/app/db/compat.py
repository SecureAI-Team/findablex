"""
Database compatibility layer for SQLite and PostgreSQL.

This module provides type mappings that work with both databases,
allowing SQLite for local development and PostgreSQL for production.
"""
from sqlalchemy import JSON, String, TypeDecorator
from sqlalchemy.dialects import postgresql
import uuid
import json


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36).
    """
    impl = String(36)
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONType(TypeDecorator):
    """
    Platform-independent JSON type.
    
    Uses PostgreSQL's JSONB when available, otherwise uses JSON.
    """
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.JSONB)
        else:
            return dialect.type_descriptor(JSON)


def get_json_type():
    """Get the appropriate JSON type for the current database."""
    return JSONType


def get_uuid_type():
    """Get the appropriate UUID type for the current database."""
    return GUID
