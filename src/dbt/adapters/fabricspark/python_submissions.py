from typing import Dict

from dbt.adapters.base import PythonJobHelper
from dbt.adapters.contracts.connection import Connection
from dbt_common.exceptions import DbtDatabaseError, DbtRuntimeError

from dbt.adapters.fabricspark.credentials import FabricSparkCredentials
from dbt.adapters.fabricspark.livysession import LivySessionManager


class BaseFabricSparkHelper(PythonJobHelper):
    """
    Implementation of PythonJobHelper for FabricSpark.
    Enables Python (PySpark) models to be executed via Livy sessions.
    """

    def __init__(self, parsed_model: Dict, credentials: FabricSparkCredentials) -> None:
        """
        Initialize Spark Job Submission helper.

        Parameters
        ----------
        parsed_model : Dict
            A dictionary containing the parsed model information, used to extract
            various configurations required for job submission.
        credentials : FabricSparkCredentials
            A FabricSparkCredentials object containing the credentials needed to
            access the Spark cluster, used to establish the connection.
        """
        self.credentials = credentials
        self.relation_name = parsed_model.get("relation_name")
        self.original_file_path = parsed_model.get("original_file_path")
        self.submission_method = parsed_model.get("config", {}).get("submission_method")
        self.connection = self._get_or_create_connection()

    def _get_or_create_connection(self) -> Connection:
        """
        Get the existing Livy connection, or create one using LivySessionManager
        if it does not exist.

        Returns
        -------
        Connection
            The active Livy connection.
        """
        # Reuse the existing Livy session connection
        livy_connection = LivySessionManager.connect(self.credentials)

        # Create a Connection object wrapper
        connection = Connection(
            type="fabricspark",
            name="python_submission",
            state="open",
            credentials=self.credentials,
            handle=livy_connection,
        )
        return connection

    def submit(self, compiled_code: str) -> None:
        """
        Submits compiled Python/PySpark code to the database and handles execution
        results or errors.

        Parameters
        ----------
        compiled_code : str
            The compiled Python code string to be executed.

        Raises
        ------
        DbtRuntimeError
            If the model creation fails.
        """
        cursor = self.connection.handle.cursor()
        try:
            cursor.execute(compiled_code, "pyspark")
            # Print output from PySpark execution
            for line in cursor.fetchall():
                print(line)
        except DbtDatabaseError as ex:
            raise DbtRuntimeError(
                f"Unable to create model {self.relation_name} "
                f"(file: {self.original_file_path}) with a {self.submission_method} "
                f"type submission. Caused by:\n{ex.msg}"
            )
