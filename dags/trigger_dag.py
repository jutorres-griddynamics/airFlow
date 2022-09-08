from airflow import DAG
from datetime import datetime
from airflow.sensors.filesystem import FileSensor
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.python import PythonOperator,BranchPythonOperator
from airflow.utils.task_group import TaskGroup
from random import randint
from airflow.operators.bash import BashOperator
import logging
from airflow.models import Variable

FILE_PATH = '/opt/airflow/dags/test.txt'

path = Variable.get('path', default_var=f'{FILE_PATH}')


with DAG("trigger_sensor", start_date=datetime(2021,1,1),
         schedule_interval="@daily", catchup=False) as dag:

    def say_hi():
        return 'Hola Mundo!'

    fileSensor = FileSensor(
        task_id='waiting_for_run_file',
        poke_interval=10,
        fs_conn_id='my_file_system_practice',
        timeout=100,
        filepath=FILE_PATH
    )

    trigger_task = TriggerDagRunOperator(
        task_id='trigger_task',
        trigger_dag_id='dynamically_branching1'
    )


    with TaskGroup(group_id="process_results") as process_results:

        def print_result_fuc(**kwargs):
            logging.info("Aqui es donde deberia salir el resultado:")
            logging.info(kwargs['ti'].xcom_pull(dag_id='dynamically_branching1', task_ids='query_table', key='ended_id', include_prior_dates=True))
            return
        def get_context_exec_date(self, **kwargs):
            try:
                # 2022-09-01T 20:17:11.698569+00:00
                # 2022-09-01, 15:17:11
                logging.info("KWARGS"*200)
                logging.info(kwargs)
                logging.info('contexto'*200)
                logging.info(kwargs['context'])
                logging.info('TI'*200)
                logging.info(kwargs['ti'])
                value = kwargs['ti'].xcom_pull(dag_id='trigger_sensor', task_ids='trigger_task',
                                               key='trigger_execution_date_iso', include_prior_dates=True)
                logging.info(value)
                return datetime.fromisoformat(value)

            except Exception as e:
                    return logging.info('Pulling execution date failed')

        sensor_triggered_dag = ExternalTaskSensor(
            task_id='sensor_triggered_dag',
            poke_interval=10,
            timeout=180,
            soft_fail=False,
            external_dag_id='dynamically_branching1',
            external_task_id=None,
            execution_date_fn=get_context_exec_date)

        print_result = PythonOperator(
            task_id="print_result",
            python_callable= print_result_fuc
        )

        remove_file = BashOperator(task_id='remove_file', bash_command=f"rm {path}", trigger_rule="all_success")
        bash_create_timestamp_file = BashOperator(task_id='bash_create_timestamp_file', bash_command=f"echo finished_algowe", trigger_rule="all_success")

        sensor_triggered_dag>>print_result>>remove_file>>bash_create_timestamp_file

    fileSensor >> trigger_task >> process_results