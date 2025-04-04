from harmoniq.db import CRUD
from harmoniq.db.engine import sql_tables


def _format_table_name(table_name):
    """
    Format table name to snake case, keep all uppercase if table name is all uppercase
    """
    table_name_formated = ""
    for i, char in enumerate(table_name):
        if char.isupper() and i != 0:
            table_name_formated += "_"
        table_name_formated += char.lower()

    if table_name == table_name.upper():
        table_name_formated = table_name

    return table_name_formated


def _create_crud_methods(crud_class, table_name, sql_class):
    methods = {
        f"create_{table_name}": lambda db, data: crud_class.create_data(
            db, sql_class, data
        ),
        f"read_all_{table_name}": lambda db: crud_class.read_all_data(db, sql_class),
        f"read_{table_name}_by_id": lambda db, id: crud_class.read_data_by_id(
            db, sql_class, id
        ),
        f"read_multiple_{table_name}_by_id": lambda db, ids: crud_class.read_multiple_by_id(
            db, sql_class, ids
        ),
        f"update_{table_name}": lambda db, id, data: crud_class.update_data(
            db, sql_class, id, data
        ),
        f"delete_{table_name}": lambda db, id: crud_class.delete_data(
            db, sql_class, id
        ),
    }

    for method_name, method in methods.items():
        setattr(crud_class, method_name, method)


for sql_class, pydantic_classes in sql_tables.items():
    """
    Create CRUD methods for each table in sql_tables
    """
    table_name = sql_class.__name__
    table_name_formated = _format_table_name(table_name)
    _create_crud_methods(CRUD, table_name_formated, sql_class)
