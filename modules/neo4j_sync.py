"""
modules/neo4j_sync.py

Neo4j schema sync utilities for Streamlit POC.
Provides:
 - extract_schema_from_databricks(config, demo=True/False)
 - sync_schema_to_neo4j(schema_obj, config)
 - save_schema_to_file(schema_obj, path)
 - load_schema_from_file(path)

Expectations:
 - `config` is a dict that may contain Databricks and Neo4j connection details. Example:
   {
     'db_host': 'https://<region>.azuredatabricks.net',
     'db_http_path': '...optional sql endpoint...',
     'db_token': '...',
     'db_cluster_id': '...',
     'neo4j_uri': 'bolt://host:7687',
     'neo4j_user': 'neo4j',
     'neo4j_pass': 'secret'
   }

Notes:
 - For Databricks schema extraction this module calls the databricks connector `run_sql` function if available.
 - In DEMO mode it returns a small mock schema object.
 - `sync_schema_to_neo4j` will MERGE Catalog/Schema/Table and Column nodes and create relationships. It is idempotent.

"""

from typing import Dict, Any
import json
import os

# defensive import of neo4j driver
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except Exception:
    GraphDatabase = None
    NEO4J_AVAILABLE = False

# attempt to import databricks connector run_sql if present
try:
    from modules import databricks_connector
    DBX_AVAILABLE = True
except Exception:
    databricks_connector = None
    DBX_AVAILABLE = False


def extract_schema_from_databricks(config: Dict[str, Any], demo: bool = True) -> Dict[str, Any]:
    """
    Extract simple schema information from Databricks.

    Returns a dict in the format:
    {
      'catalog.schema.table': ['col1','col2',...],
      ...
    }

    If demo=True or the databricks connector is missing, returns a mocked schema for demo.
    """
    if demo or not DBX_AVAILABLE:
        # Mock schema for demos
        return {
            'demo.sales.orders': ['order_id', 'customer_id', 'material', 'quantity', 'revenue'],
            'demo.procurement.purchases': ['purchase_id', 'vendor_id', 'material', 'quantity', 'cost'],
            'demo.master.vendors': ['vendor_id', 'vendor_name', 'country', 'on_time_rate', 'defect_rate']
        }

    # Real extraction using the databricks_connector.run_sql function
    cfg = config or {}
    schema_map = {}
    try:
        # get list of tables - using SHOW TABLES might require catalog/schema context
        # We try to run a generic SHOW TABLES across catalogs - adjust to your Databricks setup
        show_tables_q = "SHOW TABLES"
        df_tables = databricks_connector.run_sql(show_tables_q, cfg)
        # Expect df_tables to contain columns like 'database', 'tableName' or similar
        # Try a few column name variants
        for _, row in df_tables.iterrows():
            catalog = row.get('database') or row.get('catalog') or row.get('namespace') or 'default'
            table = row.get('tableName') or row.get('name') or row.get('table')
            if not table:
                continue
            qualified = f"{catalog}.{table}"
            # DESCRIBE TABLE to get columns
            try:
                desc_q = f"DESCRIBE TABLE {catalog}.{table}"
                df_cols = databricks_connector.run_sql(desc_q, cfg)
                cols = []
                # Databricks DESCRIBE TABLE returns rows with columns like col_name,data_type,comment
                for _, crow in df_cols.iterrows():
                    # try common names
                    colname = crow.get('col_name') or crow.get('name') or crow.get('column')
                    if colname:
                        cols.append(colname)
                schema_map[qualified] = cols
            except Exception:
                # skip tables we cannot describe
                continue
        return schema_map
    except Exception as e:
        raise RuntimeError(f"Failed to extract schema from Databricks: {e}")


def sync_schema_to_neo4j(schema_obj: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """
    Push the schema object to Neo4j. For each table (qualified name), create nodes and relationships:
    (Catalog)-[:HAS_SCHEMA]->(Schema)-[:HAS_TABLE]->(Table)-[:HAS_COLUMN]->(Column)

    Returns True on success, False on error.
    """
    if not NEO4J_AVAILABLE:
        raise RuntimeError("neo4j python driver not installed")

    uri = config.get('neo4j_uri')
    user = config.get('neo4j_user')
    pwd = config.get('neo4j_pass')
    if not uri or not user:
        raise RuntimeError("Missing Neo4j configuration (neo4j_uri, neo4j_user, neo4j_pass)")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with driver.session() as session:
            for qualified, cols in schema_obj.items():
                # attempt to split qualified into catalog.schema.table or fallback
                parts = qualified.split('.')
                if len(parts) == 3:
                    catalog, schema, table = parts
                elif len(parts) == 2:
                    catalog = 'default'
                    schema, table = parts
                else:
                    catalog = 'default'
                    schema = 'default'
                    table = qualified

                # Merge Catalog and Schema and Table
                session.run("MERGE (c:Catalog {name:$catalog})", catalog=catalog)
                session.run("MERGE (s:Schema {name:$schema})", schema=schema)
                session.run("MERGE (t:Table {name:$table})", table=table)
                session.run("MATCH (c:Catalog {name:$catalog}), (s:Schema {name:$schema}) MERGE (c)-[:HAS_SCHEMA]->(s)", catalog=catalog, schema=schema)
                session.run("MATCH (s:Schema {name:$schema}), (t:Table {name:$table}) MERGE (s)-[:HAS_TABLE]->(t)", schema=schema, table=table)

                # Columns
                for col in cols:
                    session.run("MERGE (col:Column {name:$col})", col=col)
                    session.run("MATCH (t:Table {name:$table}), (col:Column {name:$col}) MERGE (t)-[:HAS_COLUMN]->(col)", table=table, col=col)
        return True
    except Exception as e:
        print(f"Neo4j sync error: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass


def save_schema_to_file(schema_obj: Dict[str, Any], path: str = 'schema_export.json') -> str:
    with open(path, 'w') as f:
        json.dump(schema_obj, f, indent=2)
    return path


def load_schema_from_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)


if __name__ == '__main__':
    print('neo4j_sync module. Use extract_schema_from_databricks and sync_schema_to_neo4j from your app')
