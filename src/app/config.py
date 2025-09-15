import os
import yaml
import logging
from schema import config_schema

def setup_logging():
    level = logging.DEBUG if os.environ.get('DEBUG') == 'true' else logging.INFO
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    # Specifically suppress werkzeug logs
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    return logger

def load_config(set_conf_path):
    logger = logging.getLogger(__name__)
    
    config_path = f'{set_conf_path}/config.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Validate config
    config = config_schema(config)

    # Log configuration details if DEBUG is enabled
    if os.environ.get('DEBUG') == 'true':
        logger.debug("======== OneNVR Configuration ========")
        logger.debug(f"Videos retention period: {config['retention_days']} day(s)")
        logger.debug(f"Concatenation mode: {'Enabled' if config['concatenation'] else 'Disabled'}")
        if config['concatenation']:
            logger.debug(f"Daily concatenation time: {config['concatenation_time']}")
        logger.debug(f"Cleanup time: {config['deletion_time']}")
        logger.debug("Configured cameras:")
        for camera in config['cameras']:
            logger.debug(f"- {camera['name']}:")
            logger.debug(f"  RTSP URL: {camera['rtsp_url']}")
            logger.debug(f"  Codec: {camera['codec']}")
            logger.debug(f"  Segment interval: {camera['interval']} seconds")
        logger.debug("======================================")
    
    config['config_path'] = set_conf_path
        
    return config
