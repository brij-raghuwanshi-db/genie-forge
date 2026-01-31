# Genie-Forge Test Gap Analysis

## Executive Summary

This document identifies missing test cases, edge cases, and antipatterns in the Genie-Forge test suite. The analysis is based on:
- Databricks Genie REST API documentation
- Source code review of all modules
- Best practices for IaC tools (Terraform-like patterns)
- Security considerations for credential management

---

## 1. Client Module (`client.py`) - Missing Tests

### 1.1 HTTP Error Handling
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_rate_limit_429_handling` | Handle 429 Too Many Requests with retry-after header | HIGH |
| `test_400_bad_request_error` | Handle malformed request errors | HIGH |
| `test_401_unauthorized_error` | Handle authentication failures | HIGH |
| `test_403_forbidden_error` | Handle permission denied errors | HIGH |
| `test_404_not_found_error` | Handle space not found (separate from get_space) | MEDIUM |
| `test_500_internal_server_error` | Handle server errors with retry | HIGH |
| `test_502_bad_gateway_error` | Handle proxy errors with retry | MEDIUM |
| `test_503_service_unavailable` | Handle service unavailable with retry | HIGH |

### 1.2 Network Edge Cases
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_connection_timeout` | Handle slow/unresponsive server | HIGH |
| `test_read_timeout` | Handle timeout during response read | HIGH |
| `test_dns_resolution_failure` | Handle DNS lookup failures | MEDIUM |
| `test_ssl_certificate_error` | Handle SSL/TLS verification failures | MEDIUM |
| `test_connection_reset` | Handle RST packets mid-request | MEDIUM |
| `test_partial_response` | Handle incomplete JSON responses | MEDIUM |

### 1.3 Concurrent Operations
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_bulk_create_thread_safety` | Ensure thread-safe bulk operations | HIGH |
| `test_bulk_delete_with_failures` | Handle mixed success/failure in bulk | HIGH |
| `test_concurrent_read_write` | Handle read during write operations | MEDIUM |
| `test_max_workers_boundary` | Test with 1 worker and 100+ workers | MEDIUM |

### 1.4 API Response Edge Cases
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_create_returns_empty_response` | Handle empty API response | HIGH |
| `test_list_spaces_returns_malformed_json` | Handle invalid JSON | MEDIUM |
| `test_get_space_with_include_serialized` | Test include_serialized parameter | MEDIUM |
| `test_update_space_empty_body` | Should raise ValueError | MEDIUM |
| `test_list_spaces_max_pages_boundary` | Test pagination at max_pages limit | LOW |

---

## 2. Genie REST API Compliance Tests

### 2.1 Space Management (Currently Missing)
Based on Databricks Genie REST API documentation:

| Test Case | API Endpoint | Description | Priority |
|-----------|-------------|-------------|----------|
| `test_create_space_v2_format` | POST /api/2.0/genie/spaces | Create space with version 2 format | HIGH |
| `test_update_space_partial` | PATCH /api/2.0/genie/spaces/{id} | Partial updates (only title) | HIGH |
| `test_trash_space` | DELETE (trash) | Test soft delete behavior | MEDIUM |
| `test_list_spaces_with_filters` | GET with query params | Filter by parent_path, etc. | MEDIUM |

### 2.2 Conversation API (Currently NOT Tested)
The Genie Conversation API is NOT currently tested but may be needed for future features:

| Test Case | API Endpoint | Description | Priority |
|-----------|-------------|-------------|----------|
| `test_start_conversation` | POST /spaces/{id}/start-conversation | Start a conversation | LOW |
| `test_create_message` | POST /conversations/{id}/messages | Send message | LOW |
| `test_get_message` | GET /messages/{id} | Get message response | LOW |
| `test_execute_attachment_query` | Execute SQL attachment | Execute generated SQL | LOW |
| `test_send_message_feedback` | POST feedback | Like/dislike responses | LOW |

### 2.3 serialized_space Format Tests
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_serialized_space_must_be_json_string` | API requires JSON string, not dict | HIGH |
| `test_serialized_space_version_mismatch` | Handle version 1 vs 2 differences | HIGH |
| `test_sample_questions_require_uuid` | All sample_questions need unique IDs | HIGH |
| `test_join_specs_require_id` | All join_specs need unique IDs | HIGH |
| `test_arrays_must_be_sorted_by_id` | API requires sorted arrays | MEDIUM |

---

## 3. Security Tests (NEW - Not Currently Present)

### 3.1 Credential Protection
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_token_not_in_logs` | Tokens should be masked in logs | CRITICAL |
| `test_token_not_in_error_messages` | Tokens should not appear in exceptions | CRITICAL |
| `test_state_file_no_secrets` | State file should not contain tokens | CRITICAL |
| `test_config_file_no_secrets` | Config YAML should not have credentials | HIGH |

### 3.2 Input Validation
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_sql_injection_in_example_sql` | Malicious SQL in example_question_sqls | HIGH |
| `test_path_traversal_in_parent_path` | Prevent ../../../etc/passwd | HIGH |
| `test_yaml_bomb_prevention` | Prevent billion laughs attack | HIGH |
| `test_extremely_long_strings` | Prevent DoS via huge strings | MEDIUM |
| `test_unicode_null_byte_injection` | Handle \x00 in strings | MEDIUM |

### 3.3 YAML Security
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_yaml_safe_load_used` | Ensure yaml.safe_load not yaml.load | CRITICAL |
| `test_yaml_recursive_alias_limit` | Limit anchor expansion | HIGH |
| `test_yaml_arbitrary_code_execution_blocked` | No !!python/object execution | CRITICAL |

---

## 4. Parser Module - Missing Tests

### 4.1 Variable Resolution Edge Cases
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_circular_variable_reference` | ${a} -> ${b} -> ${a} should error | HIGH |
| `test_variable_with_special_chars` | ${my-var}, ${my.var}, ${my:var} | MEDIUM |
| `test_undefined_variable_warning` | Warn but don't fail on ${undefined} | MEDIUM |
| `test_variable_in_variable` | ${prefix_${suffix}} nested vars | LOW |

### 4.2 File Handling Edge Cases
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_yaml_with_bom` | Handle UTF-8 BOM | MEDIUM |
| `test_yaml_different_encodings` | UTF-16, Latin-1 | LOW |
| `test_symlink_handling` | Follow or reject symlinks | MEDIUM |
| `test_directory_vs_file` | Error on directory path for file | HIGH |
| `test_file_too_large` | Reject > 10MB config files | MEDIUM |

---

## 5. State Management - Missing Tests

### 5.1 Concurrent Access
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_concurrent_state_write` | Two processes writing simultaneously | HIGH |
| `test_state_file_locked` | Handle file lock errors | MEDIUM |
| `test_atomic_state_save` | State should be atomic (temp + rename) | HIGH |

### 5.2 State Recovery
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_corrupted_state_file` | Handle invalid JSON in state | HIGH |
| `test_state_file_truncated` | Handle partially written state | HIGH |
| `test_state_version_migration` | Upgrade state file schema | MEDIUM |

### 5.3 Drift Detection Edge Cases
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_drift_space_recreated_with_same_id` | Same ID, different content | HIGH |
| `test_drift_api_returns_different_structure` | API schema changes | MEDIUM |
| `test_drift_with_pending_state` | Drift on space that failed to apply | MEDIUM |

---

## 6. CLI Edge Cases - Missing Tests

### 6.1 Interactive Behavior
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_apply_confirmation_yes` | User types 'yes' | MEDIUM |
| `test_apply_confirmation_no` | User types 'no', should abort | MEDIUM |
| `test_keyboard_interrupt_handling` | Ctrl+C should cleanup gracefully | HIGH |
| `test_pipe_mode_no_prompts` | Detect non-TTY and skip prompts | MEDIUM |

### 6.2 Output Formats
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_json_output_format` | --format json should be valid JSON | HIGH |
| `test_table_output_unicode` | Unicode in table columns | MEDIUM |
| `test_progress_bar_disabled_in_pipe` | No progress bar when piped | LOW |

---

## 7. Model Validation - Missing Tests

### 7.1 Table Identifier Validation
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_identifier_two_parts_invalid` | "schema.table" should fail | HIGH |
| `test_identifier_four_parts_invalid` | "a.b.c.d" should fail | HIGH |
| `test_identifier_with_spaces` | "cat. schema.table" should fail | HIGH |
| `test_identifier_with_quotes` | "`cat`.`schema`.`table`" handling | MEDIUM |
| `test_identifier_case_sensitivity` | Are identifiers case-sensitive? | LOW |

### 7.2 Benchmark Questions
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_benchmark_not_sent_to_api` | Benchmarks are local-only | HIGH |
| `test_benchmark_sql_validation` | Invalid SQL in expected_sql | MEDIUM |

---

## 8. Integration Tests - Missing Scenarios

### 8.1 End-to-End Workflows
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_full_lifecycle_plan_apply_destroy` | Complete IaC cycle | CRITICAL |
| `test_apply_with_no_changes` | Idempotency | HIGH |
| `test_apply_after_manual_ui_change` | Drift + re-apply | HIGH |
| `test_import_then_modify_then_apply` | Import flow | HIGH |

### 8.2 Cross-Workspace Migration
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_export_from_one_import_to_another` | Migration workflow | HIGH |
| `test_cross_workspace_table_references` | Tables may not exist | HIGH |

### 8.3 Bulk Operations
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_bulk_create_100_spaces` | Performance test | MEDIUM |
| `test_bulk_delete_with_rate_limit` | API throttling | HIGH |

---

## 9. Antipatterns to Test For

### 9.1 Resource Leaks
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_file_handles_closed` | No leaked file descriptors | HIGH |
| `test_http_connections_closed` | No connection leaks | HIGH |
| `test_thread_pool_shutdown` | ThreadPoolExecutor properly closed | HIGH |

### 9.2 Error Handling
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_exceptions_not_swallowed` | Don't catch and ignore | HIGH |
| `test_stack_traces_preserved` | raise from preserves context | MEDIUM |
| `test_partial_failure_rollback` | Clean up on partial failure | HIGH |

### 9.3 Time-based Tests
| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_retry_timing_not_flaky` | Use time mocking | MEDIUM |
| `test_no_hardcoded_sleep` | Sleeps should be configurable | LOW |

---

## 10. Missing Error Messages Tests

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_error_message_actionable` | Errors should tell user what to do | HIGH |
| `test_error_includes_context` | Include space_id, file path, etc. | MEDIUM |
| `test_validation_errors_list_all` | Don't fail on first, show all | MEDIUM |

---

## Priority Summary

| Priority | Count | Categories |
|----------|-------|------------|
| CRITICAL | 6 | Security (credentials), End-to-end |
| HIGH | 45+ | HTTP errors, Concurrency, API compliance |
| MEDIUM | 30+ | Edge cases, Output formats |
| LOW | 10+ | Nice-to-have, Performance |

---

## Recommended Implementation Order

1. **Security Tests** - Most critical, protect credentials
2. **HTTP Error Handling** - API reliability
3. **State Management** - Data integrity
4. **API Compliance** - Databricks API contract
5. **Edge Cases** - Robustness
6. **Performance** - Scale considerations

---

## References

- [Databricks Genie REST API](https://docs.databricks.com/api/workspace/genie)
- [Genie Space Management API](https://docs.databricks.com/api/workspace/genie/createspace)
- [Genie Conversation API](https://docs.databricks.com/genie/conversation-api)
- [Terraform Testing Patterns](https://www.terraform.io/docs/extend/testing)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
