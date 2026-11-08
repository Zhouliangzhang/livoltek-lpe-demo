from backend.domain import pilot, validate

def fixture():
    from scripts.build_ci20_pilot import build
    m = build()
    ports = [p['port_id'] for p in m['ports'] if p['domain'] == 'RS485'][:2]
    row = dict(id='|'.join(sorted(ports)), ports=ports, domain='RS485', signature='draft', shared={'protocol': 'MODBUS_RTU'}, devices={p: {'role': 'SLAVE', 'address': str(i + 1)} for i, p in enumerate(ports)}, reference='', status='PENDING')
    m['project']['communication_settings'] = {'SIMULATION': [row]}
    return m, row

def test_plan_saves_pending_and_environments_are_separate():
    m, row = fixture()
    assert validate(m)['valid']
    assert validate(m)['warnings']
    assert 'REAL' not in m['project']['communication_settings']
    row['status'] = 'APPROVED'
    assert not validate(m)['valid']

def test_duplicate_addresses_and_individual_bus_override_rejected():
    m, row = fixture()
    for values in row['devices'].values():
        values['address'] = '01'
    assert not validate(m)['valid']
    m, row = fixture()
    next(iter(row['devices'].values()))['baud_rate'] = '9600'
    assert not validate(m)['valid']

def test_bad_parameters_and_multiple_masters_rejected():
    m, row = fixture()
    row['shared']['baud_rate'] = '-1'
    assert not validate(m)['valid']

    row['shared'].pop('baud_rate')
    for values in row['devices'].values():
        values.update(role='MASTER', address='')
    assert not validate(m)['valid']

def test_versioned_template_schema_preserves_source():
    m, _ = fixture()
    dm = m['device_models'][0]
    dm['communication_templates'] = [dict(id='TEST', version='1', master_data_version=dm['master_data_version'], domain='RS485', reference_doc='SIMULATION TEST ONLY', status='DRAFT', values={'baud_rate': 9600})]
    assert validate(m)['valid']
    del dm['communication_templates'][0]['reference_doc']
    assert not validate(m)['valid']
