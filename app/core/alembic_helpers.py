from alembic import op
import sqlalchemy as sa


def inspector():
    return sa.inspect(op.get_bind())


def table_exists(table_name: str) -> bool:
    return table_name in inspector().get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False
    return column_name in {column["name"] for column in inspector().get_columns(table_name)}


def index_exists(table_name: str, index_name: str) -> bool:
    if not table_exists(table_name):
        return False
    return index_name in {index["name"] for index in inspector().get_indexes(table_name)}


def unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    return constraint_name in {
        constraint["name"] for constraint in inspector().get_unique_constraints(table_name)
    }


def create_table_if_missing(table_name: str, *columns_or_constraints) -> None:
    if not table_exists(table_name):
        op.create_table(table_name, *columns_or_constraints)


def drop_table_if_exists(table_name: str) -> None:
    if table_exists(table_name):
        op.drop_table(table_name)


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_exists(table_name) and not column_exists(table_name, column.name):
        op.add_column(table_name, column)


def drop_column_if_exists(table_name: str, column_name: str) -> None:
    if table_exists(table_name) and column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if table_exists(table_name) and not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def drop_index_if_exists(index_name: str, table_name: str) -> None:
    if table_exists(table_name) and index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)
