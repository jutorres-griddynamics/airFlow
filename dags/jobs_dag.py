import logging
import random
import uuid
from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.hooks.postgres_hook import PostgresHook
from dags.operators.postgresqlcountrows import PostgreSQLCountRows

config = {
    'tables_name_1': {'schedule_interval': "@once", "start_date": datetime(2018, 10, 11),'provide_context':True},
    'tables_name_2': {'schedule_interval': "@once", "start_date": datetime(2018, 11, 11),'provide_context':True},
    'tables_name_3':{'schedule_interval': "@once", "start_date": datetime(2018, 1, 11),'provide_context':True}}



def create_dag(dag_id,
               schedule,
               dag_number,
               default_args,
               table_created):

    def check_table_exist(**kwargs):
        if True:
            return 'insert_row'
        else:
            return 'create_table'

    def xcom_call(**kwargs):
        run_id = kwargs['run_id']
        return kwargs['ti'].xcom_push(key='ended_id', value=f"{run_id} ended")
    def count_rows(sql_to_get_schema, sql_to_count_rows, table_name):
        hook = PostgresHook()
        # get schema name
        query = hook.get_records(sql=sql_to_get_schema)
        logging.info("THIS IS FIRST QUERY:")
        logging.info(query)
        for result in query:
            if 'airflow' in result:
                schema = result[0]
                logging.info("THIS IS THE SCHEMA:")
                logging.info(schema)
                break

        # check table exist
        query = hook.get_first(sql=sql_to_count_rows.format( table_name))
        if query:
            logging.info("Si se pudo:")
            logging.info(query)
            return query
        else:
            logging.info("No se pudo")

    def check_table_exist(sql_to_get_schema, sql_to_check_table_exist,
                          table_name):
        """ callable function to get schema name and after that check if table exist """
        hook = PostgresHook()
        # get schema name
        query = hook.get_records(sql=sql_to_get_schema)
        logging.info("THIS IS FIRST QUERY:")
        logging.info(query)
        for result in query:
            if 'airflow' in result:
                schema = result[0]
                logging.info("THIS IS THE SCHEMA:")
                logging.info(schema)
                break

        # check table exist
        query = hook.get_first(sql=sql_to_check_table_exist.format(schema, table_name))
        logging.info("THIS IS SECOND QUERY:")
        logging.info(query)
        if query:
            return "dummy_task"
        else:
            return "create_table"

    dag = DAG(dag_id,
              schedule_interval=schedule,
              default_args=default_args)

    with dag:
        print_process_start = DummyOperator(
            task_id='Process_Start',
            dag=dag)

        bash_task = BashOperator(task_id='bash_task', bash_command="whoami", do_xcom_push=True)
        #[2022-09-06, 10:29:15 CDT] {standard_task_runner.py:97} ERROR - Failed to execute job 3837 for task check_table_exist (The conn_id `postgres_default` isn't defined; 5319)
        # will success
        table_name_success = "my_table"
        check_table_exist = BranchPythonOperator(
            task_id='check_table_exist',
            python_callable=check_table_exist,
            op_args=["select * from pg_tables;",
                     "SELECT * FROM information_schema.tables "
                     "WHERE table_schema = '{}'"
                     "AND table_name = '{}';", table_name_success
                     ] ,
            provide_context=True,
            dag=dag)


        create_table = PostgresOperator(task_id='create_table',postgres_conn_id= 'postgres_default',sql='sql/create_table_script.sql' ,dag=dag)

        dummy_task = DummyOperator(task_id='dummy_task', dag=dag, trigger_rule="none_failed")

        insert_row = PostgresOperator(task_id='insert_row', sql='''INSERT INTO my_table VALUES
                (%s, '{{ ti.xcom_pull(task_ids='bash_task', key='return_value') }}', %s);''',
                parameters=(uuid.uuid4().int % 123456789, datetime.now()),trigger_rule='one_success', dag=dag)

        query_table = PostgreSQLCountRows(task_id='query_table',
                                        postgres_conn_id='postgres_default',
                                        database='airflow',
                                        table_name=table_name_success,
                                        do_xcom_push=True)


        print_process_start >> bash_task >> check_table_exist >> [create_table,dummy_task]
        create_table >> insert_row >> query_table
        dummy_task >> insert_row


    return dag

# build a dag for each number in range(10)
for n in config.keys():
    dag_id = str(n)
    default_args = config[n]

    schedule = config[n]['schedule_interval']
    dag_number = len(config)
    is_table_created = bool(random.getrandbits(1))
    globals()[dag_id] = create_dag(dag_id,
                                  schedule,
                                  dag_number,
                                  default_args,
                                  is_table_created)