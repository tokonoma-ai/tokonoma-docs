# Pin chart and application versions

Chart and application versions are independent. This guide uses chart `0.37.0` and application `0.68.0`; the chart defaults to the mutable application tag `latest`.

Run commands from an operator workstation with Helm 3.14+ and `kubectl`, in your customer working directory outside this repository. Follow [upgrade preparation](upgrading.md) before changing an existing release. For a first installation, set these pins in the [installation guide](install.md) instead.

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Intended cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `tokonoma-values.yaml` | Your saved nonsecret values file; required for the upgrade below. Keep existing Secret references and include any additional overlays you changed. |

Replace the context before running commands. Agents must ask if the target cluster or upgrade choice is unresolved.

Keep `mcp.image.tag: "0.68.0"` in your values file and `--version 0.37.0` in Helm commands. The unattended MCP and runner inherit the MCP image unless their images are overridden separately. Check existing overrides before upgrading.

```sh
helm upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context REPLACE_WITH_KUBE_CONTEXT --version 0.37.0 -n tokonoma \
  --reset-then-reuse-values --values tokonoma-values.yaml \
  --set-string mcp.image.tag=0.68.0 \
  --wait --timeout 10m
```

`--reset-then-reuse-values` preserves the release's previously supplied values, including credentials and Secret references, before applying these overrides. Expect `STATUS: deployed`.

Verify the configured image:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deployment toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].image}'
```

Expect the image tag to end in `:0.68.0`. This checks the configured version. To verify behavior, complete the health, licensed memory-read, and enabled-integration checks in [upgrading](upgrading.md).

Public registries: [chart and images](https://gallery.ecr.aws/tokonoma), [application image](https://gallery.ecr.aws/tokonoma/toko-mcp). Test a newer chart and image together before changing these pins.
