from client import Client
from enum import Enum
from scheduler import Scheduler
from concurrent import futures


# State represents the different states that an alert can be in
class State(Enum):
    PASS = 1
    WARN = 2
    CRITICAL = 3


# Action represents the different actions that can be taken on an alert based on it's state
class Action(Enum):
    NOOP = 1
    NOTIFY_WARN = 2
    NOTIFY_CRITICAL = 3
    RESOLVE = 4


# AlertEngine exposes interfaces to manage execution of all alerts and maintain their state and corresponding actions
class AlertEngine:
    def __init__(self, parallelism=4):
        self.client = Client("")
        self.parallelism = parallelism
        self.alerts = []
        self._init_alerts()

    def _init_alerts(self):
        try:
            alerts = self.client.query_alerts()
            for alert in alerts:
                self.alerts.append(
                    Alert(
                        name=alert.get("name"),
                        query=alert.get("query"),
                        interval_secs=alert.get("intervalSecs"),
                        repeat_interval_secs=alert.get("repeatIntervalSecs"),
                        critical=alert["critical"],
                        warn=alert["warn"]
                    )
                )
            print("INFO:", alerts)
        except ConnectionError as e:
            raise ConnectionError("could not initialize alerts, got {} from alerts client query_alerts".format(e))

    def _schedule_alert_execution(self, alert):
        scheduler = Scheduler(interval=alert.interval_secs, function=self._execute, alert=alert)
        scheduler.start()

    def execute(self):
        with futures.ThreadPoolExecutor(max_workers=self.parallelism) as executor:
            for alert in self.alerts:
                executor.submit(self._schedule_alert_execution, alert)

    def _execute(self, alert):
        try:
            metric_val = self.client.query(target=alert.query)
        except ConnectionError as e:
            print("ERROR: error querying metric {} - {}".format(alert.query, e))
            return
        if not metric_val:
            raise KeyError("Invalid response for alert {}, query not found".format(alert.get("name")))
        action = Action.NOOP
        if metric_val <= alert.warn.value:
            action = alert.update(State.PASS)
        elif alert.warn.value < metric_val <= alert.critical.value:
            action = alert.update(State.WARN)
        else:
            action = alert.update(State.CRITICAL)
        # handle alert client errors gracefully instead of killing the thread/worker
        if action == Action.NOTIFY_WARN:
            print("INFO: Notifying alert {} in state WARN, current metric_val {}".format(
                alert, metric_val))
            try:
                self.client.notify(alert.name, alert.warn.message)
            except ConnectionError as e:
                print("ERROR: error notifying alert {} - {}".format(alert.name, e))
                return
        elif action == Action.NOTIFY_CRITICAL:
            print("INFO: Notifying alert {} im state CRITICAL, current metric_val {}".format(
                alert, metric_val))
            try:
                self.client.notify(alert.name, alert.critical.message)
            except ConnectionError as e:
                print("ERROR: error notifying alert {} - {}".format(alert.name, e))
                return
        elif action == Action.RESOLVE:
            print("INFO: Resolving alert {}, current metric_val {}".format(
                alert, metric_val))
            try:
                self.client.resolve(alert.name)
            except ConnectionError as e:
                print("ERROR: error resolving alert {} - {}".format(alert.name, e))
                return
        else:
            pass
            # print("No action to be taken on the alert {}".format(alert.name))


# Alert exposes interfaces to manage the state of a single alert
class Alert:
    def __init__(self, name, query, interval_secs, repeat_interval_secs, critical, warn):
        self.name = name
        self.query = query
        self.interval_secs = interval_secs
        self.repeat_interval_secs = repeat_interval_secs
        self.critical = Threshold(critical.get('value'), critical.get('message'))
        self.warn = Threshold(warn.get('value'), warn.get('message'))
        self.state = State.PASS
        self.num_secs_since_last_notification_in_warn_state = 0
        self.num_secs_since_last_notification_in_critical_state = 0

    def update(self, alert_state):
        action = Action.NOOP
        if self.state != alert_state:
            if alert_state == State.WARN:
                action = Action.NOTIFY_WARN
                self.num_secs_since_last_notification_in_warn_state = 0
                self.num_secs_since_last_notification_in_critical_state = 0
            elif alert_state == State.CRITICAL:
                action = Action.NOTIFY_CRITICAL
                self.num_secs_since_last_notification_in_critical_state = 0
                self.num_secs_since_last_notification_in_warn_state = 0
            elif alert_state == State.PASS:
                action = Action.RESOLVE
                self.num_secs_since_last_notification_in_critical_state = 0
                self.num_secs_since_last_notification_in_warn_state = 0
        else:
            if alert_state == State.WARN:
                self.num_secs_since_last_notification_in_warn_state += self.interval_secs
                print("INFO: alert {} continues to remain in WARN state, "
                      "not notifying until repeat_interval_secs".format(self))
                if self.num_secs_since_last_notification_in_warn_state >= self.repeat_interval_secs:
                    action = Action.NOTIFY_WARN
                    self.num_secs_since_last_notification_in_warn_state = 0
            elif alert_state == State.CRITICAL:
                self.num_secs_since_last_notification_in_critical_state += self.interval_secs
                print("INFO: alert {} continues to remain in CRITICAL state, "
                      "not notifying until repeat_interval_secs".format(self))
                if self.num_secs_since_last_notification_in_critical_state >= self.repeat_interval_secs:
                    action = Action.NOTIFY_CRITICAL
                    self.num_secs_since_last_notification_in_critical_state = 0
            else:
                pass
                # print("alert {} in state {}, nothing to do here".format(self.name, alert_state))
        self.state = alert_state
        return action

    def __repr__(self):
        return repr(vars(self))


# Threshold represents the values amd messaging associated with different alert levels (WARN and CRITICAL)
class Threshold:
    def __init__(self, critical_value, critical_message):
        self.value = critical_value
        self.message = critical_message

    def __repr__(self):
        return repr(vars(self))
