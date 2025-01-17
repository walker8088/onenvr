from voluptuous import Schema, Required, Optional, All, Range, Any

config_schema = Schema({
    Required('cameras'): [{
        Required('name'): str,
        Required('rtsp_url'): str,
        Optional('codec', default='copy'): str,
        Optional('interval', default=300): All(int, Range(min=60)),
    }],
    Optional('retention_days', default=7): All(int, Range(min=1)),
    Optional('concatenation', default=True): bool,
    Optional('concatenation_time', default='01:00'): str,
    Optional('deletion_time', default='02:00'): str
})
