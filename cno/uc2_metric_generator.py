from uc2_settings import METRIC_TEMPLATE, METRIC_TEMPLATE_UC2_EXEC, METRIC_TEMPLATE_UC2_CONF


def generate_metric_uc2_exec(metric_value, timestamp, tmp):
    #metric = METRIC_TEMPLATE_UC2_EXEC  #
    metric = tmp
    metric['execution']['value'] = metric_value
    #metric['metric']['timestamp'] = timestamp
    return metric


def generate_metric_uc2_conf(metric_value, timestamp, tmp):
    metric_bitrate = {"bitrate": metric_value}
    #metric = METRIC_TEMPLATE_UC2_CONF
    metric = tmp
    metric['vce']['action'] = metric_bitrate
    #metric['vce']['timestamp'] = timestamp
    return metric
