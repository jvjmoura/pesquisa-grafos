"""
Cliente Neo4j para conexão e execução de queries Cypher.
"""

from __future__ import annotations

import os
from typing import Any

from neo4j import GraphDatabase


class Neo4jClient:
    """Wrapper para o driver Neo4j com métodos utilitários."""

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str = "neo4j",
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "stf_password_2026")
        self.database = database
        self._driver = GraphDatabase.driver(
            self.uri, auth=(self.username, self.password)
        )

    def close(self) -> None:
        """Fecha a conexão com o Neo4j."""
        self._driver.close()

    def run_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        """Executa uma query Cypher e retorna os resultados como lista de dicts.

        Args:
            query: Query Cypher a ser executada.
            parameters: Parâmetros para a query.

        Returns:
            Lista de dicionários com os resultados.
        """
        parameters = parameters or {}
        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def run_write(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        """Executa uma query Cypher de escrita (CREATE, MERGE, DELETE).

        Args:
            query: Query Cypher de escrita.
            parameters: Parâmetros para a query.
        """
        parameters = parameters or {}
        with self._driver.session(database=self.database) as session:
            session.execute_write(lambda tx: tx.run(query, parameters))

    def verify_connection(self) -> bool:
        """Verifica se a conexão com o Neo4j está ativa."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def clear_database(self) -> None:
        """Remove todos os nós e relações do banco (usar com cuidado)."""
        self.run_write("MATCH (n) DETACH DELETE n")

    def get_node_count(self) -> int:
        """Retorna o número total de nós no banco."""
        result = self.run_query("MATCH (n) RETURN count(n) AS total")
        return result[0]["total"] if result else 0

    def __enter__(self) -> Neo4jClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
