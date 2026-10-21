# Inputs and placeholders

Replace every `REPLACE_WITH_...` marker with your value before running commands, including inside paths and URLs. Edit the text directly; do not use exports or wrappers.

Use the YAML comments for configuration fields and each guide's input table for command inputs. Agents must use supplied or verified values and ask for missing decisions. Request protected file paths or Secret references; keep secret contents out of chat.

## Common inputs

| Input | Meaning and source |
| --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | Exact kubeconfig context for the target cluster. Obtain it from the cluster owner and verify it with `kubectl config get-contexts`. |
| `REPLACE_WITH_DOCS_DIRECTORY` | Absolute path to this downloaded documentation folder, including `references/` and `examples/`. |
| `REPLACE_WITH_SECRET_DIRECTORY` | Absolute protected directory on the workstation running Helm. It is outside this repository and contains only the credential files required by the selected guides. |
| `REPLACE_WITH_CUSTOMER` | Organization slug used for telemetry index and default bucket names. Choose it before creating those resources: lowercase letter first, then lowercase letters, digits or hyphens, maximum 42 characters. |
| `REPLACE_WITH_REGION`, `REPLACE_WITH_PROJECT`, `REPLACE_WITH_CLUSTER` | Existing cloud region, Google Cloud project ID, and Kubernetes service's cloud cluster name, supplied by the platform owner. A cloud cluster name is not necessarily its kubeconfig context. |

## Feature-specific inputs

Feature guides list required identifiers and provider settings. Copy them from the provider or ask its administrator. Use hostnames your organization controls; `example.com` is illustrative.

Keep quotes around paths, especially those containing spaces. Substitute your actual release and namespace for `tokonoma` consistently.

New installations use the latest released chart and its application image defaults. For configuration changes, replace `REPLACE_WITH_INSTALLED_CHART_VERSION` with the existing chart version using [configuration checks](upgrading.md#before-changing-configuration).

## Configuration and provider syntax

Save YAML under the guide's filename in your working directory. Record values-file order: later files override keys and replace lists. Keep the base file when adding overlays.

Keep Datadog notification variables such as `$ID` and `$TOKONOMA_TOKEN` intact. They are provider syntax, not shell inputs.

For the complete sequence, return to [installation](install.md). For configuration fields, read the [base](../examples/memory-values.yaml) or [runner](../examples/runner-grafana-values.yaml) example comments. Use [endpoints](endpoints.md) for service addresses.
