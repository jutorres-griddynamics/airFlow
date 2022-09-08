import logging
from airflow.models.baseoperator import BaseOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


class PostgreSQLCountRows(BaseOperator):

    def __init__(self, postgres_conn_id=str, database=str, table_name=str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.postgres_conn_id = postgres_conn_id
        self.database = database
        self.table_name = table_name


    def execute(self, **kwargs):
        hook = PostgresHook(postgres_conn_id=self.postgres_conn_id, schema=self.database)
        conn = hook.get_conn()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT (*) FROM {self.table_name}")
        results = cursor.fetchone()
        cursor.close()
        conn.close()
        return results