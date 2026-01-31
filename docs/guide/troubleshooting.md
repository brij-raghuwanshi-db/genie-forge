# Troubleshooting

Common issues and solutions when using Genie-Forge.

## Authentication Issues

### "Unable to authenticate" or Connection Errors

**Check available profiles:**

```bash
genie-forge profiles
```

**Verify profile configuration:**

```bash
cat ~/.databrickscfg | grep -A3 "YOUR_PROFILE"
```

**Check for overriding environment variables:**

```bash
echo "DATABRICKS_HOST: $DATABRICKS_HOST"
echo "DATABRICKS_TOKEN: $DATABRICKS_TOKEN"
```

**Solution**: Unset environment variables to use profile:

```bash
unset DATABRICKS_HOST DATABRICKS_TOKEN
genie-forge find --name "*" --workspace --profile YOUR_PROFILE
```

### Connecting to Wrong Workspace

Environment variables may be overriding your profile.

**Solution**:

```bash
# Unset any environment variables
unset DATABRICKS_HOST DATABRICKS_TOKEN

# Verify you're connecting to the right workspace
genie-forge find --name "*" --workspace --profile YOUR_PROFILE
```

### Profile Not Found

**Error**: `Profile 'MY_PROFILE' not found in ~/.databrickscfg`

**Solution**: Add the profile to your config file:

```ini
# ~/.databrickscfg
[MY_PROFILE]
host = https://your-workspace.azuredatabricks.net
token = dapi123456789...
```

---

## Configuration Issues

### Validation Errors

**Get detailed validation info:**

```bash
genie-forge validate --config conf/spaces/ --strict
```

**Common issues**:

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing required field: space_id` | Space config missing `space_id` | Add unique `space_id` to each space |
| `Missing required field: warehouse_id` | No warehouse specified | Add `warehouse_id` or use variable `${warehouse_id}` |
| `Invalid variable: ${unknown}` | Variable not defined in environment | Add variable to `conf/environments/{env}.yaml` |

### Variable Substitution Not Working

**Check your environment config exists:**

```bash
ls conf/environments/
cat conf/environments/dev.yaml
```

**Verify variables are defined:**

```yaml
# conf/environments/dev.yaml
variables:
  warehouse_id: "abc123"
  catalog: "my_catalog"
  schema: "my_schema"
```

**Use the correct `--env` flag:**

```bash
genie-forge plan --env dev --profile MY_PROFILE
#             ^^^ must match filename: dev.yaml
```

---

## Deployment Issues

### Tables Not Found

**Error**: `Table 'catalog.schema.table' does not exist`

**Check tables exist in Unity Catalog:**

```sql
-- In Databricks SQL Editor
SHOW TABLES IN my_catalog.my_schema;
```

**Create demo tables if needed:**

```bash
genie-forge setup-demo \
  --catalog my_catalog \
  --schema my_schema \
  --warehouse-id abc123 \
  --profile MY_PROFILE
```

### Permission Denied

**Error**: `User does not have permission to access warehouse`

**Solutions**:

1. Verify you have access to the SQL warehouse
2. Check Unity Catalog permissions on tables
3. Ensure your token has the required scopes

### Apply Fails After Plan Succeeds

**Possible causes**:

1. **Concurrent modification**: Someone else modified the space
2. **API rate limiting**: Too many requests in short time
3. **Transient network error**: Retry usually fixes this

**Solution**: Run apply again:

```bash
genie-forge apply --env dev --profile MY_PROFILE
```

---

## State Issues

### State File Corrupted

**Symptoms**: JSON parse errors, unexpected behavior

**Solution**: Backup and reset state:

```bash
# Backup existing state
cp .genie-forge.json .genie-forge.json.backup

# Remove corrupted state
rm .genie-forge.json

# Re-run plan to see current vs desired state
genie-forge plan --env dev --profile MY_PROFILE
```

### State Out of Sync with Workspace

**Symptoms**: Plan shows "CREATE" for spaces that already exist

**This happens when**:
- Spaces were created manually in the UI
- State file was deleted
- Different state file was used

**Solution**: Use `find` to check what exists, then update or destroy:

```bash
# See what's actually in the workspace
genie-forge find --name "*" --workspace --profile MY_PROFILE

# If spaces exist but shouldn't, destroy them
genie-forge destroy --env dev --target "space_name" --profile MY_PROFILE
```

---

## Performance Issues

### Slow Operations

**For many spaces**, use parallel operations:

```bash
# Apply with auto-approve for faster execution
genie-forge apply --env dev --profile MY_PROFILE --auto-approve
```

**Expected performance**:

| Operation | 10 spaces | 50 spaces | 100 spaces |
|-----------|-----------|-----------|------------|
| Create    | ~0.5s     | ~2s       | ~3s        |
| Update    | ~0.5s     | ~2s       | ~3s        |
| Delete    | ~0.5s     | ~2s       | ~3s        |

### API Rate Limiting

**Symptoms**: 429 errors, requests failing

**Solution**: The CLI has built-in rate limiting, but you can slow down bulk operations:

```python
# In Python API, set rate limit
client.bulk_create(configs, rate_limit=5.0)  # 5 ops/second
```

---

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Workspace client not initialized` | Authentication failed | Check profile/env vars |
| `Space not found in state` | Trying to destroy non-tracked space | Use `find --workspace` to locate |
| `Invalid configuration` | YAML syntax or schema error | Run `validate --strict` |
| `Warehouse not accessible` | SQL warehouse permission issue | Check warehouse permissions |
| `Table does not exist` | Referenced table not in Unity Catalog | Create tables first |

---

## Getting Help

### Debug Output

Set environment variable for verbose output:

```bash
export GENIE_FORGE_DEBUG=1
genie-forge plan --env dev --profile MY_PROFILE
```

### Check Version

```bash
genie-forge --version
```

### Report Issues

When reporting issues, include:

1. Genie-Forge version (`genie-forge --version`)
2. Python version (`python --version`)
3. Full error message
4. Command that caused the error
5. Relevant config files (redact sensitive info)
