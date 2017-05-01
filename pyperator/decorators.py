def log_schedule(method):
    def inner(instance):
        try:
            instance.log.info('Component {}: Scheduled'.format(instance.name))
        except AttributeError:
            pass
        return method(instance)

    return inner