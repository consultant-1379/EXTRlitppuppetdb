#!/bin/bash

SVC_NAME="puppetdb"
RUN_DIR="/var/run/${SVC_NAME}"
LOG_DIR="/var/log/${SVC_NAME}"
INTERVAL_LONG="35"
INTERVAL_SHORT="5"
INTERVAL_RESTART="45"
MAX_ERRORS="3"
CURRENT_STATE=""
USING_SYSTEMD=0

function check_system {
    [ -d /run/systemd/system/ ] && USING_SYSTEMD=1
}

function get_current_state {
    if [ "${USING_SYSTEMD}" == "0" ];
    then
        CURRENT_STATE=$(/sbin/chkconfig --list "${SVC_NAME}" | \
                        /bin/awk '{print $7}' | \
                        /bin/awk -F':' '{print $2}' | \
                        /usr/bin/tr '[:upper:]' '[:lower:]' | \
                        /bin/awk '{$1=$1};1')
    else
        CURRENT_STATE=$(/usr/bin/systemctl is-enabled "${SVC_NAME}")
    fi
}

function log_daemon_log {
    DAEMON_LOG="${LOG_DIR}/${SVC_NAME}-daemon.log"
    if [ -f "${DAEMON_LOG}" ];
    then
        /bin/logger < "${DAEMON_LOG}"
        > "${DAEMON_LOG}"
    fi
}

function manage_pid_file {
    PID_FILE="${RUN_DIR}/${SVC_NAME}"
    [ "${USING_SYSTEMD}" == 1 -a -f "${PID_FILE}" ] && /bin/rm -f "${PID_FILE}"
}

function restart_svc {
    /bin/logger "Restarting the ${SVC_NAME} service"
    if [ "${USING_SYSTEMD}" == 0 ];
    then
        /sbin/service "${SVC_NAME}" restart > /dev/null 2>&1
    else
        /usr/bin/systemctl restart "${SVC_NAME}.service"
    fi
    /bin/sleep "${INTERVAL_RESTART}"
}

function manage_hprof_files {
    files=$(/bin/ls -t "${LOG_DIR}"/*.hprof* 2> /dev/null)
    count=$(/bin/echo "${files}" | /usr/bin/wc -w)
    if [ "${count}" -gt 1 ];
    then
        /bin/rm -f "${LOG_DIR}"/*.hprof.prev
    fi
}

error_count=0
interval=1

check_system

while true
do
    get_current_state

    if [ "${USING_SYSTEMD}" == 0 -a "${CURRENT_STATE}" == "on" ] || \
       [ "${USING_SYSTEMD}" == 1 -a "${CURRENT_STATE}" == "enabled" ];
    then
        interval="${INTERVAL_LONG}"

        if [ "${USING_SYSTEMD}" == 0 ];
        then
            /sbin/service "${SVC_NAME}" status > /dev/null 2>&1
            status=$?
        else
            /usr/bin/systemctl status "${SVC_NAME}.service" > /dev/null 2>&1
            status=$?
        fi

        if [ "${status}" != "0" ];
        then
            error_count=$(( error_count + 1 ))
            interval="${INTERVAL_SHORT}"
            /bin/logger "The ${SVC_NAME} service is not running (${error_count}/${MAX_ERRORS})"
        else
            [ "${error_count}" -ne 0 ] && /bin/logger "The ${SVC_NAME} service resumed without a restart"
            error_count=0
        fi

        if [ "${error_count}" -eq "${MAX_ERRORS}" ];
        then
            log_daemon_log
            manage_pid_file
            manage_hprof_files
            restart_svc
            error_count=0
            continue
        fi
    else
        error_count=0
    fi
    /bin/sleep "${interval}"
done
