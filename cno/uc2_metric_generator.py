from uc2_settings import METRIC_TEMPLATE, METRIC_TEMPLATE_UC2_EXEC, METRIC_TEMPLATE_UC2_CONF

def generate_metric_uc2_exec(metric_value, timestamp, tmp, vce_id):
    #metric = METRIC_TEMPLATE_UC2_EXEC
    metric = tmp
    metric['execution']['value'] = metric_value
    metric['execution']['mac'] = vce_id
    #metric['metric']['timestamp'] = timestamp
    return metric


def generate_metric_uc2_conf(metric_value, timestamp, tmp, vce_id):
    metric_bitrate = {"bitrate": metric_value}
    #metric = METRIC_TEMPLATE_UC2_CONF
    metric = tmp
    metric['vce']['mac'] = vce_id
    metric['vce']['action'] = metric_bitrate
    #metric['vce']['timestamp'] = timestamp
    return metric

def generate_metric_uc2_vce(metric_value, timestamp, tmp, vce_id, video_bit_rates):
    metric = tmp
    metric['id'] = vce_id #str
    metric['utc_time'] = timestamp #int
    metric['metric_x'] = video_bit_rates[int(metric_value[2])] #int
    metric['metric_y'] = video_bit_rates[int(metric_value[3])] #int
    return metric
