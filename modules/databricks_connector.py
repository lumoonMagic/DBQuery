"""
modules/databricks_connector.py

Databricks connector helper for Streamlit POC.
Provides:
 - test_sql_connection(server_hostname, http_path, access_token)
 - run_sql(query, config) -> pandas.DataFrame
 - run_sql_via_jobs_api(query, config) -> pandas.DataFrame
 - upload_and_submit_python_task(...)

Notes:
 - This module uses the Databricks SQL Connector if http_path is provided and the package is installed.
 - Otherwise it falls back to submitting a small Python task to a cluster using the Jobs API and DBFS.
 - All network calls use `requests` and expect a Databricks workspace URL (https://<domain>). Use a PAT (personal access token).
 - For production, improve error handling, retries, and security for tokens.

Example config dict keys (from app UI or saved config):
{
    'db_host': 'https://<region>.azuredatabricks.net',
    'db_http_path': '/sql/1.0/endpoints/..' or '',
    'db_token': '<PAT>',
    'db_cluster_id': '<cluster-id>'
}

"""

import os
import time
import base64
import json
from typing import Tuple, Optional

import pandas as pd
import requests

# Prefer databricks-sql-connector if available
try:
    from databricks import sql as dbsql
    HAS_DBSQL = True
except Exception:
    dbsql = None
    HAS_DBSQL = False


def test_sql_connection(server_hostname: str, http_path: str, access_token: str, timeout: int = 10) -> Tuple[bool, str]:
    """Test Databricks SQL connection using databricks-sql-connector if available.

    Returns (ok, message_or_row)
    """
    if not HAS_DBSQL:
        return False, "databricks-sql-connector not installed"
    try:
        with dbsql.connect(server_hostname=server_hostname, http_path=http_path, access_token=access_token) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as ok")
                row = cursor.fetchone()
        return True, row
    except Exception as e:
        return False, str(e)


def run_sql(query: str, config: dict) -> pd.DataFrame:
    """Run SQL using the configuration provided.

    If config contains 'db_http_path' and the databricks-sql-connector is installed, it will use that path.
    Otherwise it will attempt to run the query via Jobs API on the cluster specified by 'db_cluster_id'.

    Returns a pandas DataFrame on success or raises RuntimeError on failure.
    """
    host = config.get('db_host')
    http_path = config.get('db_http_path')
    token = config.get('db_token')
    cluster_id = config.get('db_cluster_id')

    if http_path and HAS_DBSQL:
        # Use SQL Connector
        try:
            with dbsql.connect(server_hostname=host, http_path=http_path, access_token=token) as conn:
                df = pd.read_sql(query, conn)
                return df
        except Exception as e:
            raise RuntimeError(f"Databricks SQL connector error: {e}")

    # Fallback: Jobs API pattern
    if not host or not token or not cluster_id:
        raise RuntimeError("Missing Databricks configuration: need host+token+cluster_id for Jobs API path")

    ok, res = run_sql_via_jobs_api(query=query, host=host, token=token, cluster_id=cluster_id)
    if not ok:
        raise RuntimeError(f"Jobs API execution failed: {res}")
    if isinstance(res, pd.DataFrame):
        return res
    # else res may be a JSON-like structure; try to convert to DataFrame
    try:
        df = pd.DataFrame(res)
        return df
    except Exception:
        raise RuntimeError("Unable to parse result into DataFrame")


def run_sql_via_jobs_api(query: str, host: str, token: str, cluster_id: str, poll_interval: int = 3, timeout: int = 300) -> Tuple[bool, Optional[pd.DataFrame]]:
    """Submit a Python task to the Databricks cluster that runs spark.sql(query) and writes CSV to DBFS, then fetch it.

    Returns (True, DataFrame) on success or (False, error message) on failure.

    Note: This function uploads a temporary Python file to DBFS and then submits a run using the Jobs API (2.1).
    """
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # Build python script that runs the SQL on the cluster
    safe_query = query.replace("'''", "''")
    py_code = f"""
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
df = spark.sql('''{safe_query}''')
import time
out_path = '/tmp/streamlit_poc_{int(time.time())}'
df.coalesce(1).write.mode('overwrite').option('header','true').csv('dbfs:' + out_path)
print('WROTE:'+out_path)
"""

    # Upload python file to DBFS
    dbfs_path = f"/tmp/streamlit_poc_task_{int(time.time())}.py"
    put_payload = {
        "path": dbfs_path,
        "contents": base64.b64encode(py_code.encode('utf-8')).decode('utf-8'),
        "overwrite": True
    }
    try:
        put_resp = session.post(f"{host}/api/2.0/dbfs/put", json=put_payload)
        put_resp.raise_for_status()
    except Exception as e:
        return False, f"Failed to upload task to DBFS: {e}"

    # Submit a run with the python file
    payload = {
        "run_name": "streamlit_poc_run",
        "existing_cluster_id": cluster_id,
        "spark_python_task": {
            "python_file": f"dbfs:{dbfs_path}"
        }
    }
    try:
        submit = session.post(f"{host}/api/2.1/jobs/runs/submit", json=payload)
        submit.raise_for_status()
        run_id = submit.json().get('run_id')
        if not run_id:
            return False, f"No run_id returned: {submit.text}"
    except Exception as e:
        return False, f"Failed to submit run: {e}"

    # Poll for completion
    start_ts = time.time()
    while True:
        if time.time() - start_ts > timeout:
            return False, "Timed out waiting for job completion"
        try:
            status = session.get(f"{host}/api/2.1/jobs/runs/get?run_id={run_id}")
            status.raise_for_status()
            j = status.json()
            state = j.get('state', {})
            life = state.get('life_cycle_state')
            result_state = state.get('result_state')
            if life in ('TERMINATED', 'SKIPPED', 'INTERNAL_ERROR') or result_state:
                break
        except Exception as e:
            return False, f"Error polling run status: {e}"
        time.sleep(poll_interval)

    # Check final state
    final = session.get(f"{host}/api/2.1/jobs/runs/get?run_id={run_id}")
    final.raise_for_status()
    fj = final.json()
    if fj.get('state', {}).get('result_state') != 'SUCCESS':
        return False, fj.get('state')

    # List DBFS /tmp and find folder that starts with streamlit_poc_
    try:
        list_resp = session.get(f"{host}/api/2.0/dbfs/list?path=/tmp")
        list_resp.raise_for_status()
        files = list_resp.json().get('files', [])
        candidate = None
        for f in files:
            if f.get('path','').startswith('/tmp/streamlit_poc_'):
                # Look inside
                inner = session.get(f"{host}/api/2.0/dbfs/list?path={f['path']}")
                inner.raise_for_status()
                inner_files = inner.json().get('files', [])
                for it in inner_files:
                    # part-*.csv is the typical file
                    if 'part-' in it.get('path','') and it.get('path','').endswith('.csv'):
                        candidate = it['path']
                        break
                if candidate:
                    break
        if not candidate:
            return False, {'error':'Result CSV not found', 'files': files}

        # Read file via DBFS read
        read_resp = session.get(f"{host}/api/2.0/dbfs/read?path={candidate}")
        read_resp.raise_for_status()
        content_b64 = read_resp.json().get('data')
        content = base64.b64decode(content_b64)
        from io import StringIO
        df = pd.read_csv(StringIO(content.decode('utf-8')))
        return True, df
    except Exception as e:
        return False, f"Failed to fetch result CSV: {e}"


# Lightweight helper: run a simple SQL via SQL endpoint (convenience)
def run_sql_via_http_query(host: str, http_path: str, token: str, query: str) -> pd.DataFrame:
    """Run query using Databricks SQL REST API (if you have an SQL endpoint). This is an optional convenience wrapper.

    For more robust usage, use the databricks-sql-connector client.
    """
    # This implementation is intentionally minimal - Databricks SQL REST usage varies by deployment.
    # Recommend using databricks-sql-connector for production.
    raise NotImplementedError("run_sql_via_http_query is not implemented. Use databricks-sql-connector or Jobs API.")


if __name__ == '__main__':
    print("Databricks connector module. Import run_sql(query, config) in your app.")
