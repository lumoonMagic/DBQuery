import os
import pandas as pd

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # Placeholder if package is not installed

class Neo4jSync:
    def __init__(self, config=None, demo_mode=True):
        """
        config: dict with Neo4j connection info
            {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password": "<password>"
            }
        demo_mode: bool
        """
        self.config = config
        self.demo_mode = demo_mode
        self.driver = None

        if not demo_mode:
            if GraphDatabase is None:
                raise ImportError("neo4j Python driver not installed.")
            self.driver = GraphDatabase.driver(
                self.config.get("uri"),
                auth=(self.config.get("user"), self.config.get("password"))
            )

    # --------------------------
    # Demo mode data
    # --------------------------
    def load_demo_metadata(self):
        """
        Returns a mock DataFrame representing tables and columns
        """
        data = [
            {"table": "vendors", "column": "vendor_id", "type": "STRING"},
            {"table": "vendors", "column": "vendor_name", "type": "STRING"},
            {"table": "vendors", "column": "on_time_rate", "type": "FLOAT"},
            {"table": "vendors", "column": "defect_rate", "type": "FLOAT"},
            {"table": "sales", "column": "vendor_id", "type": "STRING"},
            {"table": "sales", "column": "sales_amount", "type": "FLOAT"},
        ]
        df = pd.DataFrame(data)
        return df

    # --------------------------
    # Query Neo4j for schema/ontology
    # --------------------------
    def get_tables_and_columns(self):
        if self.demo_mode:
            print("[DEMO MODE] Returning mock Neo4j metadata")
            return self.load_demo_metadata()

        query = """
        MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
        RETURN t.name AS table, c.name AS column, c.type AS type
        """
        with self.driver.session() as session:
            result = session.run(query)
            data = [{"table": r["table"], "column": r["column"], "type": r["type"]} for r in result]
            df = pd.DataFrame(data)
            return df

    # --------------------------
    # Placeholder: Push ontology to Neo4j
    # --------------------------
    def push_ontology(self, ontology_data):
        if self.demo_mode:
            print("[DEMO MODE] Simulate ontology push to Neo4j")
            return True

        # REAL mode placeholder
        with self.driver.session() as session:
            # Example: create nodes/relationships
            for table_info in ontology_data:
                session.run(
                    "MERGE (t:Table {name:$table}) MERGE (c:Column {name:$column, type:$type}) MERGE (t)-[:HAS_COLUMN]->(c)",
                    table=table_info["table"],
                    column=table_info["column"],
                    type=table_info["type"]
                )
        return True

    def close(self):
        if self.driver:
            self.driver.close()


# --------------------------
# Example usage
# --------------------------
if __name__ == "__main__":
    # DEMO
    neo_demo = Neo4jSync(demo_mode=True)
    df_demo = neo_demo.get_tables_and_columns()
    print(df_demo)

    # REAL placeholder
    config_real = {
        "uri": "bolt://127.0.0.1:7687",
        "user": "neo4j",
        "password": "<password>"
    }
    # neo_real = Neo4jSync(config=config_real, demo_mode=False)
    # df_real = neo_real.get_tables_and_columns()
    # print(df_real)
