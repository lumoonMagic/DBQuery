$(sed -n '1,400p' /workspaces/DBQuery/modules/databricks_connector.py 2>/dev/null || cat <<'PY'
# If sed fails (file not yet written), re-create from assistant content:
"""modules/databricks_connector.py
...assistant provided content...
"""
PY
)
