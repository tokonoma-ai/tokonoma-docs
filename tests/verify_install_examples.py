#!/usr/bin/env python3
"""Offline Helm and YAML checks for the customer installation examples.

Requires Python 3.10+, PyYAML, and Helm. Does not contact a cluster, fetch chart
packages, create Secrets, or call any model or telemetry provider. All credential
references and values are test fixtures. The chart must have dependencies present.

Example:
  python3 tests/verify_install_examples.py /path/to/charts/tokonoma --docs-root .
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import yaml


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resource(documents: list[dict], kind: str, name: str) -> dict:
    matches = [d for d in documents if d.get('kind') == kind and d.get('metadata', {}).get('name') == name]
    check(len(matches) == 1, f'Expected exactly one {kind}/{name}, got {len(matches)}')
    return matches[0]


def environment(documents: list[dict], name: str) -> dict:
    containers = resource(documents, 'Deployment', name)['spec']['template']['spec']['containers']
    check(len(containers) == 1, f'{name}: expected one application container')
    entries = containers[0]['env']
    check(len({e['name'] for e in entries}) == len(entries), f'{name}: duplicate environment variable')
    return {e['name']: e for e in entries}


def check_collector(path: Path) -> dict:
    config = yaml.safe_load(path.read_text())
    pipelines = config['service']['pipelines']
    check(set(pipelines) == {'logs', 'traces'}, 'Customer collector must forward logs/traces only; metrics need a separate destination')
    receiver = config['receivers']['otlp']['protocols']['grpc']
    check(receiver['endpoint'] == '0.0.0.0:4317', 'Customer receiver must accept OTLP/gRPC on 4317')
    exporters = config['exporters']
    check(len(exporters) == 1, 'Expected one customer OTLP exporter')
    exporter_name, exporter = next(iter(exporters.items()))
    check(exporter_name.split('/')[0] == 'otlp', 'Quickwit requires the OTLP/gRPC exporter, not otlphttp')
    check(exporter['endpoint'] == 'toko-indexer.tokonoma.svc.cluster.local:7281', 'Unexpected customer ingest endpoint')
    check(exporter.get('tls', {}).get('insecure') is True, 'Example should explicitly identify its private plaintext transport')
    check(exporter.get('headers') == {
        'qw-otel-logs-index': 'REPLACE_WITH_CUSTOMER-logs',
        'qw-otel-traces-index': 'REPLACE_WITH_CUSTOMER-traces',
    }, 'Customer collector must select distinct customer logs/traces indexes')
    for signal, pipeline in pipelines.items():
        check(pipeline['receivers'] == ['otlp'], f'{signal}: unexpected receivers')
        check(pipeline['exporters'] == [exporter_name], f'{signal}: unexpected exporter')
        processors = pipeline['processors']
        check(processors == ['memory_limiter', 'batch'], f'{signal}: memory limiter must precede batch')
        for name in processors:
            check(name in config['processors'], f'{signal}: missing processor {name}')
    check(config['processors']['memory_limiter']['limit_mib'] > 0, 'Collector memory limit must be positive')
    return {'result': 'passed', 'validation': 'YAML and semantic checks only; collector binary validation and live ingest not run'}


def fixtures(source: dict) -> dict:
    base = copy.deepcopy(source)
    # Do not replace this block: an all-comment llm: block parses as null and
    # deletes Helm's model defaults. That was the original example regression.
    check(isinstance(base.get('llm'), dict), 'examples/values.yaml: llm must be a mapping, not null; retain an explicit provider field')
    check(base['llm'].get('provider') == 'anthropic', 'The standard example should select anthropic explicitly')
    base['llm']['apiKeySecret'] = {'name': 'render-only-model', 'key': 'apiKey'}
    base['postgres'] = {'auth': {'existingSecret': 'toko-postgres', 'secretKey': 'password'}}
    base['mcp']['auth']['clients'] = [{
        'id': 'render-only-runner', 'origin': 'configured', 'enabled': True,
        'grantTypes': ['client_credentials'], 'scopes': ['toko-mcp/query'],
        'tokenEndpointAuthMethod': 'client_secret_post',
        'secretRef': {'name': 'render-only-runner-oauth', 'key': 'clientSecret',
                      'checksum': hashlib.sha256(b'render-only-not-a-real-secret').hexdigest()},
    }]
    base['mcp']['slack']['tokenSecret'] = {
        'name': 'render-only-slack', 'botTokenKey': 'botToken', 'appTokenKey': 'appToken',
    }
    base['runner']['tokoMcp'] = {'oauthClientSecretRef': {
        'name': 'render-only-runner-oauth', 'clientIdKey': 'clientId', 'key': 'clientSecret',
    }}
    base['runner']['detection']['scope'] = {'cluster': 'render-only-cluster', 'namespaces': ['render-only-app']}
    return base


def case_values(base: dict, platform: bool, exposed: bool, provider: str, inline: bool = False) -> dict:
    values = copy.deepcopy(base)
    values['telemetryPlatform'] = platform
    # Preserve the example's provider for Anthropic; change it only for the
    # explicit Bedrock alternative under test. Never supply a model override.
    if provider == 'bedrock':
        values['llm']['provider'] = 'bedrock'
        values['llm']['region'] = 'us-west-2'
    if inline:
        values['llm'].pop('apiKeySecret', None)
        values.setdefault('credentials', {})['anthropicApiKey'] = 'render-only-not-a-real-anthropic-key'
    if platform:
        values['customer'] = 'render-only'
        values['region'] = 'us-west-2'
        values['objectStorage'] = {'serviceAccountName': 'tokonoma-sa'}
        values['runner']['mcpServers'] = []
        values['prometheus'] = {'enabled': True}
        values['otelCollector'] = {'enabled': True}
    else:
        values['runner']['mcpServers'] = [{
            'name': 'telemetry', 'kind': 'telemetry', 'url': 'https://telemetry.example.com/mcp',
            'expectedTools': ['search_logs'], 'authSecretRef': {'name': 'render-only-telemetry', 'key': 'token'},
        }]
    if exposed:
        values['domain'] = 'mcp.example.com'
        values['mcp']['auth']['baseUrl'] = 'https://mcp.example.com'
        values['mcp']['ingress'] = {'enabled': True, 'className': 'nginx',
                                     'tls': {'enabled': True, 'secretName': 'render-only-mcp-tls'}}
    return values


def validate_render(documents: list[dict], platform: bool, exposed: bool, provider: str,
                    expected_model: str, inline: bool) -> None:
    primary = environment(documents, 'toko-mcp')
    sibling = environment(documents, 'toko-mcp-unattended')
    check(('TOKO_MCP_DISABLE_TELEMETRY_TOOLS' not in primary) == platform, 'Primary telemetry gate mismatch')
    check(('TOKO_MCP_DISABLE_TELEMETRY_TOOLS' not in sibling) == platform, 'Sibling telemetry gate mismatch')
    for name in ('SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'):
        check(name in primary and name not in sibling, f'{name}: only the primary should connect to Slack')
    ingresses = [d for d in documents if d['kind'] == 'Ingress']
    check(bool(ingresses) == exposed, 'MCP ingress choice changed')
    if exposed:
        check(len(ingresses) == 1, 'Expected one MCP ingress')
        check(ingresses[0]['spec']['tls'][0]['hosts'] == ['mcp.example.com'], 'MCP TLS host mismatch')
    check(all(d['spec']['type'] == 'ClusterIP' for d in documents if d['kind'] == 'Service'), 'Internal services must stay ClusterIP')
    runner_config = yaml.safe_load(resource(documents, 'ConfigMap', 'toko-runner')['data']['runner.yaml'])['runner']
    check(runner_config['detection']['enabled'] is True, 'Detection must remain enabled')
    check(runner_config['destinations']['slackApp']['enabled'] is True, 'Slack destination must remain enabled')
    check(runner_config['tokoMcp']['url'] == 'http://toko-mcp-unattended:8000', 'Runner must target the sibling')
    check(len(runner_config['mcpServers']) == (0 if platform else 1), 'Unexpected additional MCP connections')
    if platform:
        for env in (primary, sibling):
            check(env['PROMETHEUS_URL']['value'] == 'http://toko-prometheus-server', 'Bundled Prometheus not wired')
            check(env['QUICKWIT_BASE_URL']['value'] == 'http://toko-searcher:7280', 'Searcher not wired')
            check(env['DEFAULT_LOGS_INDEX']['value'] == 'render-only-logs', 'Customer logs index mismatch')
            check(env['DEFAULT_TRACES_INDEX']['value'] == 'render-only-traces', 'Customer traces index mismatch')
        indexes = resource(documents, 'ConfigMap', 'toko-telemetry-indexes')['data']
        check(set(indexes) == {'render-only-logs.yaml', 'render-only-traces.yaml'}, 'Customer indexes not bootstrapped')
        service = resource(documents, 'Service', 'toko-indexer')
        check(any(p['port'] == 7281 for p in service['spec']['ports']), 'OTLP gRPC port not exposed internally')
    for name in ('toko-mcp', 'toko-mcp-unattended', 'toko-runner'):
        env = environment(documents, name)
        check(('AWS_BEARER_TOKEN_BEDROCK' in env) == (provider == 'bedrock'), f'{name}: Bedrock key routing mismatch')
        check(('ANTHROPIC_API_KEY' in env) == (provider == 'anthropic'), f'{name}: Anthropic key routing mismatch')
        check(env['ANTHROPIC_MODEL']['value'] == expected_model, f'{name}: chart default model was not retained')
        if inline:
            check(env['ANTHROPIC_API_KEY']['valueFrom']['secretKeyRef']['name'] == 'toko-anthropic', f'{name}: inline credential not selected')
    if inline:
        secret = resource(documents, 'Secret', 'toko-anthropic')
        check(secret['stringData']['apiKey'] == 'render-only-not-a-real-anthropic-key', 'Inline credential Secret mismatch')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('chart', type=Path, help='Unpacked chart directory containing Chart.yaml and vendored dependencies')
    parser.add_argument('--docs-root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output-dir', type=Path, help='Keep render/lint evidence here (default: new temporary directory)')
    parser.add_argument('--helm', default='helm', help='Helm executable or path')
    args = parser.parse_args()
    chart = args.chart.resolve()
    docs = args.docs_root.resolve()
    output = args.output_dir.resolve() if args.output_dir else Path(tempfile.mkdtemp(prefix='tokonoma-install-examples-'))
    output.mkdir(parents=True, exist_ok=True)
    source_text = (docs / 'examples/values.yaml').read_text()
    source = yaml.safe_load(source_text)
    base = fixtures(source)
    chart_values = yaml.safe_load((chart / 'values.yaml').read_text())
    expected_model = source['llm'].get('model') or chart_values['llm']['model']
    check(bool(expected_model), 'The chart must supply a default llm.model')
    (output / 'example-source.yaml').write_text(source_text)
    report = {'chart_version': yaml.safe_load((chart / 'Chart.yaml').read_text())['version'],
              'helm_version': subprocess.check_output([args.helm, 'version', '--short'], text=True).strip(),
              'source_sha256': hashlib.sha256(source_text.encode()).hexdigest(),
              'collector': check_collector(docs / 'examples/customer-otel-collector.yaml'),
              'cases': [], 'not_run': ['live Kubernetes deployment', 'third-party auth', 'live telemetry ingestion', 'collector binary validation']}
    cases = [(p, e, provider, False) for p in (False, True) for e in (False, True) for provider in ('anthropic', 'bedrock')]
    cases.append((False, False, 'anthropic', True))
    for platform, exposed, provider, inline in cases:
        name = f'{"platform" if platform else "external"}-{"exposed" if exposed else "private"}-{provider}' + ('-inline' if inline else '')
        values = case_values(base, platform, exposed, provider, inline)
        path = output / f'{name}.yaml'
        path.write_text(yaml.safe_dump(values, sort_keys=False))
        render = subprocess.run([args.helm, 'template', 'toko', str(chart), '--namespace', 'tokonoma', '--values', str(path)], text=True, capture_output=True)
        (output / f'{name}.rendered.yaml').write_text(render.stdout)
        (output / f'{name}.stderr').write_text(render.stderr)
        check(render.returncode == 0, f'{name}: helm template failed: {render.stderr}')
        documents = [d for d in yaml.safe_load_all(render.stdout) if d]
        validate_render(documents, platform, exposed, provider, expected_model, inline)
        lint = subprocess.run([args.helm, 'lint', str(chart), '--values', str(path)], text=True, capture_output=True)
        (output / f'{name}.lint.txt').write_text(lint.stdout + lint.stderr)
        check(lint.returncode == 0, f'{name}: helm lint failed: {lint.stdout}{lint.stderr}')
        report['cases'].append({'case': name, 'render': 'passed', 'yaml_assertions': 'passed', 'lint': 'passed', 'objects': len(documents)})
        print(f'PASS {name}')
    # Exercise upgrade rendering with preserved native credentials and both additions.
    upgraded = case_values(base, True, True, 'anthropic')
    upgrade_path = output / 'upgrade-platform-and-access.yaml'
    upgrade_path.write_text(yaml.safe_dump(upgraded, sort_keys=False))
    upgraded_render = subprocess.run([args.helm, 'template', 'toko', str(chart), '--namespace', 'tokonoma',
                                     '--is-upgrade', '--values', str(upgrade_path)], text=True, capture_output=True)
    check(upgraded_render.returncode == 0, upgraded_render.stderr)
    validate_render([d for d in yaml.safe_load_all(upgraded_render.stdout) if d], True, True, 'anthropic', expected_model, False)
    report['cases'].append({'case': 'upgrade-platform-and-access', 'render': 'passed', 'yaml_assertions': 'passed'})
    print('PASS upgrade-platform-and-access (offline rendering, not release-state lookup)')

    # Model a saved Anthropic configuration as a lower-priority values layer.
    # The documented explicit clears must remove it when moving to Bedrock.
    legacy = case_values(base, False, False, 'anthropic', True)
    legacy['runner']['engine'] = {'apiKeySecret': {'name': 'old-anthropic', 'key': 'apiKey'}}
    legacy['mcp']['memoryLlm'] = {'apiKeySecret': {'name': 'old-anthropic', 'key': 'apiKey'}}
    legacy['runner']['extraEnv'] = [{'name': 'CLAUDE_CODE_USE_BEDROCK', 'value': '1'}]
    legacy_path = output / 'saved-anthropic-values.yaml'
    legacy_path.write_text(yaml.safe_dump(legacy, sort_keys=False))
    clearing = case_values(base, False, False, 'bedrock')
    clearing['credentials'] = {'anthropicApiKey': ''}
    clearing['runner']['engine'] = {'apiKeySecret': None}
    clearing['mcp']['memoryLlm'] = {'apiKeySecret': None}
    clearing['runner']['extraEnv'] = []
    clearing['mcp']['extraEnv'] = []
    clearing_path = output / 'bedrock-explicit-clears.yaml'
    clearing_path.write_text(yaml.safe_dump(clearing, sort_keys=False))
    migration = subprocess.run([args.helm, 'template', 'toko', str(chart), '--namespace', 'tokonoma',
                                '--is-upgrade', '-f', str(legacy_path), '-f', str(clearing_path)], text=True, capture_output=True)
    check(migration.returncode == 0, migration.stderr)
    validate_render([d for d in yaml.safe_load_all(migration.stdout) if d], False, False, 'bedrock', expected_model, False)
    report['cases'].append({'case': 'bedrock-explicit-clears', 'render': 'passed', 'yaml_assertions': 'passed'})
    print('PASS bedrock-explicit-clears (saved-values layer simulation)')
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS customer collector YAML/semantics. Evidence: {output}')


if __name__ == '__main__':
    main()
