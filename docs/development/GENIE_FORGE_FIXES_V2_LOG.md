# Genie-Forge Fixes V2 Testing Log

**Date:** 2026-01-30
**Profile:** GENIE_PROFILE
**Warehouse ID:** 6c5c02379eea0732
**Catalog:** brij_cat
**Schema:** default
**Workspace:** https://adb-7405611072871894.14.azuredatabricks.net

---

## Fixes Applied

### Fix 1: Restored Variable Substitution in YAML Files

**Files Updated:**
- `conf/spaces/employee_analytics.yaml`
- `conf/spaces/sales_analytics.yaml`
- `conf/spaces/simple_space.yaml`
- `conf/spaces/sample_complete_space.yaml`

**Changes:**
- Replaced `6c5c02379eea0732` with `${warehouse_id}`
- Replaced `brij_cat.default` with `${catalog}.${schema}`
- Replaced `/Workspace/Users/brijendra.raghuwanshi@databricks.com` with `${parent_path}`

**Status:** ✅ COMPLETED

---

### Fix 2: Column Configs Sorting

**File:** `src/genie_forge/serializer.py`

**Change:** Added sorting by column_name alphabetically in `_serialize_data_sources`:
```python
if column_configs:
    # Sort by column_name alphabetically (required by Genie API)
    table_dict["column_configs"] = sorted(column_configs, key=lambda x: x["column_name"])
```

**Status:** ✅ COMPLETED

---

### Fix 3: Multiple Instructions Combined

**File:** `src/genie_forge/cli/space_cmd.py`

**Change:** Combined multiple --instructions into single text_instruction:
```python
if instructions:
    config["instructions"] = config.get("instructions", {})
    # Combine multiple instructions into one (API only allows 1 text_instruction)
    combined_text = "\n\n".join(instructions)
    config["instructions"]["text_instructions"] = [{"text": combined_text}]
```

**Also in:** `src/genie_forge/serializer.py` - Combined text_instructions from config files into one.

**Status:** ✅ COMPLETED

---

### Fix 4: SQL Function UUID Generation

**Files:**
- `src/genie_forge/serializer.py` - Added UUID generation for sql_functions
- `src/genie_forge/models.py` - Added `id` field to `SqlFunction` model

**Change:**
```python
func_dict: dict[str, Any] = {
    "identifier": func.identifier,
    "id": func.id if func.id else uuid.uuid4().hex,  # Generate UUID if missing
}
```

**Status:** ✅ COMPLETED

---

### Fix 5: state-import Alias Options

**File:** `src/genie_forge/cli/state_cmd.py`

**Change:** Added all required options to state-import command:
- `--pattern` / `-n`
- `--env` / `-e`
- `--as` (logical_id)
- `--profile` / `-p`
- `--state-file` / `-s`
- `--output-dir` / `-o`
- `--dry-run`
- `--force` / `-f`

**Status:** ✅ COMPLETED

---

### Fix 6: Import Command String Parsing

**File:** `src/genie_forge/serializer.py`

**Change:** Added handling for serialized_space as JSON string:
```python
raw_serialized = response.get("serialized_space", {})
if isinstance(raw_serialized, str):
    try:
        serialized = json.loads(raw_serialized) if raw_serialized else {}
    except (json.JSONDecodeError, TypeError):
        serialized = {}
else:
    serialized = raw_serialized if raw_serialized else {}
```

**Status:** ✅ COMPLETED

---

### Fix 7: Export Documentation

**File:** `src/genie_forge/cli/space_cmd.py`

**Change:** Added permission note to space-export docstring explaining that --pattern requires "Can Edit" permission.

**Status:** ✅ COMPLETED

---

### Additional Fixes (Found During Testing)

#### Fix 8: Added json import
**File:** `src/genie_forge/serializer.py` - Added `import json`

#### Fix 9: ColumnConfig Model
**File:** `src/genie_forge/models.py` - Added `build_value_dictionary` and `get_example_values` fields

#### Fix 10: JoinSpec Export Format
**File:** `src/genie_forge/cli/import_cmd.py` - Updated to use new JoinSpec format (left.identifier, right.identifier, sql)

#### Fix 11: Environment Config
**File:** `conf/environments/dev.yaml` - Updated with actual values for testing

---

## Test Results

### Test 1: apply (simple_space.yaml)

**Command:**
```bash
genie-forge apply --env dev --config conf/spaces/simple_space.yaml --profile GENIE_PROFILE --auto-approve
```

**Result:** ✅ SUCCESS
```
✓ Created: simple_demo
```

**Space ID:** `01f0fdd2d9bf1628b990ee6f4e967563`

---

### Test 2: space-create with --instructions and --functions

**Command:**
```bash
genie-forge space-create "GF_Test_Full_V2" \
  --warehouse-id 6c5c02379eea0732 \
  --tables "brij_cat.default.sales,brij_cat.default.customers" \
  --description "Full-featured test space with all options" \
  --instructions "Use SUM for revenue calculations" \
  --instructions "Filter completed transactions by default" \
  --instructions "Join sales with customers using customer_id" \
  --functions "brij_cat.default.calculate_tenure_years,brij_cat.default.percent_change" \
  --questions "What is total revenue?" \
  --questions "Who are our top 10 customers?" \
  --parent-path "/Workspace/Users/brijendra.raghuwanshi@databricks.com" \
  --env dev --profile GENIE_PROFILE
```

**Result:** ✅ SUCCESS
```
✓ Space created: 01f0fdd2e16c154b89a73c707f0cf4e6
  URL: https://adb-7405611072871894.14.azuredatabricks.net/#genie/spaces/01f0fdd2e16c154b89a73c707f0cf4e6
✓ Added to state: dev (logical_id: gf_test_full_v2)

Text Instructions: 1 (combined from 3)
SQL Functions: 2
Sample Questions: 2
```

**Space ID:** `01f0fdd2e16c154b89a73c707f0cf4e6`

---

### Test 3: import command

**Command:**
```bash
genie-forge import 01f0f5c0b9b81968b0df658cb5d23ecf --env dev --as brij_imported --output-dir ./exported_spaces --profile GENIE_PROFILE --force
```

**Result:** ✅ SUCCESS
```
✓ Imported: brij_imported → exported_spaces/brij_imported.yaml
Import complete: 1 imported, 0 skipped, 0 failed
```

---

### Test 4: apply sales_analytics.yaml (with join_specs)

**Command:**
```bash
genie-forge apply --env dev --config conf/spaces/sales_analytics.yaml --profile GENIE_PROFILE --auto-approve
```

**Result:** ✅ SUCCESS
```
✓ Created: sales_analytics
```

**Space ID:** `01f0fdd4203e1aa8b50119d5be6f5766`

---

### Test 5: apply employee_analytics.yaml (with join_specs)

**Command:**
```bash
genie-forge apply --env dev --config conf/spaces/employee_analytics.yaml --profile GENIE_PROFILE --auto-approve
```

**Result:** ✅ SUCCESS
```
✓ Created: employee_analytics
```

**Space ID:** `01f0fdd429b715e797a74d436bf51d96`

---

### Test 6: state-import with --pattern

**Command:**
```bash
genie-forge state-import --pattern "Brij*" --env dev --profile GENIE_PROFILE --dry-run
```

**Result:** ✅ SUCCESS
```
Searching for spaces matching 'Brij*'...
  Found 2 matching space(s)

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Databricks ID ┃ Title        ┃ Logical ID   ┃ Config File                   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│               │ Brij_Space_2 │ brij_space_2 │ conf/spaces/brij_space_2.yaml │
│               │ Brij_Space   │ brij_space   │ conf/spaces/brij_space.yaml   │
└───────────────┴──────────────┴──────────────┴───────────────────────────────┘

ℹ Dry run mode - 2 space(s) would be imported
```

---

## Spaces in State (dev environment)

| Logical ID | Title | Databricks ID | Status |
|------------|-------|---------------|--------|
| gf_test_full_space | GF_Test_Full_Space | 01f0fdd06daf166b8ad42b816ef3a99c | APPLIED |
| simple_demo | Simple Demo Space | 01f0fdd2d9bf1628b990ee6f4e967563 | APPLIED |
| gf_test_full_v2 | GF_Test_Full_V2 | 01f0fdd2e16c154b89a73c707f0cf4e6 | APPLIED |
| brij_imported | Brij_Space | (imported) | APPLIED |
| test_join3 | Test Join Space 3 | 01f0fdd3ede914979e23b3d6da67b6fe | APPLIED |
| test_join4 | Test Join Space 4 | 01f0fdd3f42b1000bddaf3f8720b9eca | APPLIED |
| sales_analytics | Sales Analytics Space | 01f0fdd4203e1aa8b50119d5be6f5766 | APPLIED |
| employee_analytics | Employee Analytics Dashboard | 01f0fdd429b715e797a74d436bf51d96 | APPLIED |

---

## Spaces in Workspace

| Space ID | Title | Warehouse ID |
|----------|-------|--------------|
| 01f0fdd2e16c154b89a73c707f0cf4e6 | GF_Test_Full_V2 | 6c5c02379eea0732 |
| 01f0fdd2d9bf1628b990ee6f4e967563 | Simple Demo Space (1) | 6c5c02379eea0732 |
| 01f0fdd06daf166b8ad42b816ef3a99c | GF_Test_Full_Space | 6c5c02379eea0732 |
| 01f0fdd0520a162d96da8eb6d9ca6cd5 | Simple Demo Space | 6c5c02379eea0732 |
| 01f0fdcfd11e1b6298e680d261d19d55 | GF_Test_Brij_Clone | 6c5c02379eea0732 |
| 01f0fdb48cd115e3a2106039dd915d3f | Sales Analytics Demo | 6c5c02379eea0732 |
| 01f0fdb488be1135b3d968b04694c635 | Employee Analytics Demo | 6c5c02379eea0732 |
| 01f0fa611a281874af805b312f532364 | Brij_Space_2 | 6c5c02379eea0732 |
| 01f0f5c0b9b81968b0df658cb5d23ecf | Brij_Space | 6c5c02379eea0732 |

---

## Known Limitations

### 1. Export by Pattern Requires "Can Edit" Permission

The `--pattern` option for `space-export` uses the Databricks list spaces API which requires "Can Edit" permission. Use `--space-id` instead if you only have "Can View" permission.

### 2. Join_specs Require Relationship Type Marker

**CRITICAL:** The Databricks Genie API requires a relationship type marker in the `sql` array for join_specs.

**Error without marker:**
```
Failed to parse export proto: sales.customer_id = customers.customer_id (of class java.lang.String)
```

**Valid relationship types:**
- `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--`
- `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--`
- `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--`
- `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--`

**Correct format:**
```yaml
join_specs:
  - left:
      identifier: catalog.schema.table1
      alias: t1
    right:
      identifier: catalog.schema.table2
      alias: t2
    sql:
      - '`t1`.`column` = `t2`.`column`'
      - '--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--'
    instruction:
      - "Join description here"
```

**Files Updated:**
- `employee_analytics.yaml` - Added relationship type markers, updated sql_functions to use existing functions
- `sales_analytics.yaml` - Added relationship type markers, updated sql_functions to use existing functions

### 3. SQL Functions Must Exist in Unity Catalog

SQL functions referenced in configs must exist in the Unity Catalog. If they don't, the API returns "Failed to retrieve schema from unity catalog."

**Existing functions in brij_cat.default:**
- `calculate_tenure_years`
- `percent_change`

---

## Summary

All original issues have been fixed and tested:

| Issue | Fix | Status |
|-------|-----|--------|
| Hardcoded variables in YAML | Restored ${variable} syntax | ✅ |
| Column configs not sorted | Added alphabetical sorting | ✅ |
| Multiple instructions error | Combined into single instruction | ✅ |
| SQL function ID missing | Added UUID generation | ✅ |
| state-import missing options | Added all options | ✅ |
| Import command str.get() error | Added JSON string parsing | ✅ |
| Export permission documentation | Added permission note | ✅ |
| **Join_specs relationship type** | **Added --rt= markers (CRITICAL)** | ✅ |
| **YAML functions references** | **Updated to existing functions** | ✅ |

### All Spaces Successfully Created

| Space | ID | Via |
|-------|-----|-----|
| Simple Demo Space | 01f0fdd2d9bf1628b990ee6f4e967563 | apply |
| GF_Test_Full_V2 | 01f0fdd2e16c154b89a73c707f0cf4e6 | space-create |
| Sales Analytics Space | 01f0fdd4203e1aa8b50119d5be6f5766 | apply |
| Employee Analytics Dashboard | 01f0fdd429b715e797a74d436bf51d96 | apply |

