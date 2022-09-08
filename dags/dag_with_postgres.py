from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator



with DAG("my_dag_postgres2", start_date=datetime(2021,1,1),
         schedule_interval="@once", catchup=False) as dag:

    task1 = PostgresOperator(
        task_id= 'create_postgre_table',
        postgres_conn_id='postgres_localhost',
        sql='''
        create table if not exists dag_runs (
            dt date,
            dag_id character varying,
            primary key (dt,dag_id)
        ) 
        '''
    )

    task2 = PostgresOperator(
        task_id='insert_into_table',
        postgres_conn_id='postgres_localhost',
        sql='''
            insert into dag_runs (dt, dag_id) values ('{{ ds }}', '{{ dag.dag_id}}')
            '''
    )

    task1 >> task2