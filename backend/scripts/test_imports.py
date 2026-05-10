import sys
sys.path.insert(0, '/AI-F/AI-f/backend')
test_modules = [
    'tests.test_hsm', 'tests.test_pqc', 'tests.test_validation',
    'tests.test_key_rotation', 'tests.test_edge_device', 'tests.test_grpc',
    'tests.test_enroll', 'tests.test_recognize', 'tests.test_multimodal',
    'tests.test_spoof_detection', 'tests.test_soar', 'tests.test_billing',
    'tests.test_payments', 'tests.test_payments_webhook', 'tests.test_saas',
    'tests.test_webhooks', 'tests.test_rate_limit', 'tests.test_jwt_revocation',
    'tests.test_tee_security', 'tests.test_tee_full', 'tests.test_federated_learning',
    'tests.test_benchmark', 'tests.test_integration', 'tests.test_validation_framework',
    'tests.test_performance', 'tests.test_oauth', 'tests.test_public_enrich',
    'tests.e2e.test_e2e',
    'tests.integration.test_migrations', 'tests.integration.test_replication',
    'tests.integration.test_database', 'tests.integration.test_redis',
    'tests.integration.test_vector_search', 'tests.integration.test_recognition_e2e',
    'tests.integration.test_webhooks_integration', 'tests.integration.test_celery',
    'tests.integration.test_api_contract', 'tests.integration.test_onnx_models',
]
for mod_name in test_modules:
    try:
        __import__(mod_name)
        print(f'OK:   {mod_name}')
    except Exception as e:
        err = str(e).split('\n')[0][:80]
        print(f'FAIL: {mod_name}: {err}')