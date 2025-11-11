import pandas as pd
import json
import os

# For REAL mode
try:
    from databricks import sql
except ImportError:
    sql = None  # Placeholder if package is not installed

# --------------------------
# DatabricksConnector Class
# --------------------------
class DatabricksConnector:
    def __init__(self, config=None, demo_mode=True):
        """
        config: dict with Databricks connection info
            {
                "server_hostname": "",
                "http_path": "",
                "access_token": "",
                "cluster_id": ""  # optional
            }
        demo_mode: bool, if True will return mock data
        """
        self.config = config
        self.demo_mode = demo_mode

    # --------------------------
    # Demo data loader
    # --------------------------
    def load_demo_data(self, file_path=None):
        """
        Load a demo CSV/JSON file as a DataFrame.
        """
        if not file_path:
            # Default demo file
            file_path = os.path.join(os.path.dirname(__file__), "../demo_data/supply_chain_sample.csv")
        df = pd.read_csv(file_path)
        return df

    # --------------------------
    # Execute SQL Query
    # --------------------------
    def execute_query(self, query):
        """
        Execute SQL query on Databricks (REAL mode)
        or return mock data (DEMO mode)
        """
        if self.demo_mode:
            print("[DEMO MODE] Returning demo data for query execution.")
            return self.load_demo_data()
        
        # REAL mode
        if sql is None:
            raise ImportError("databricks-sql-connector not installed.")

        if not self.config:
            raise ValueError("Databricks config not set.")

        with sql.connect(
            server_hostname=self.config.get("server_hostname"),
            http_path=self.config.get("http_path"),
            access_token=self.config.get("access_token")
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                df = pd.DataFrame(rows, columns=columns)
                return df

    # --------------------------
    # Optional: Start/Stop Cluster (placeholder)
    # --------------------------
    def start_cluster(self, cluster_id=None):
        # Placeholder: integrate Databricks REST API to start cluster
        cluster_id = cluster_id or self.config.get("cluster_id")
        print(f"[INFO] Start cluster {cluster_id} - Placeholder")

    def stop_cluster(self, cluster_id=None):
        # Placeholder: integrate Databricks REST API to stop cluster
        cluster_id = cluster_id or self.config.get("cluster_id")
        print(f"[INFO] Stop cluster {cluster_id} - Placeholder")


# --------------------------
# Example usage
# --------------------------
if __name__ == "__main__":
    # DEMO
    connector = DatabricksConnector(demo_mode=True)
    df_demo = connector.execute_query("SELECT * FROM vendors LIMIT 5")
    print(df_demo.head())

    # REAL placeholder
    config = {
        "server_hostname": "dbc-xxxx.cloud.databricks.com",
        "http_path": "/sql/1.0/endpoints/xxxx",
        "access_token": "<YOUR_TOKEN>",
        "cluster_id": "abcd-1234"
    }
    connector_real = DatabricksConnector(config=config, demo_mode=False)
    # df_real = connector_real.execute_query("SELECT * FROM your_table LIMIT 5")
