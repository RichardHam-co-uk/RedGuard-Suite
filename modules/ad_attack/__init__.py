"""
AD/Entra ID Attack Path Module
Integrates with BloodHound for attack path analysis.
"""
import logging
from typing import Optional, Dict, Any
from .bloodhound_client import BloodHoundClient

logger = logging.getLogger(__name__)

class ADAttackModule:
    """Analyzes Active Directory attack paths via BloodHound."""

    def __init__(self, server_url: str = "http://localhost:8080", api_token: str = ""):
        self.client = BloodHoundClient(server_url, api_token)
        self.connected = False

    def connect(self) -> bool:
        self.connected = self.client.health_check()
        return self.connected

    def find_shortest_paths_to_da(self, start_node: str) -> list:
        if not self.connected:
            raise RuntimeError("Not connected to BloodHound")
        # Cypher: MATCH p = shortestPath((n)-[:MemberOf|AdminTo*1..]->(m:Group {name:"DOMAIN ADMINS"})) RETURN p
        return self.client.run_cypher(f"MATCH p = shortestPath((n {{name: '{start_node}'}})-[:MemberOf|AdminTo*1..]->(m:Group {{name: 'DOMAIN ADMINS'}})) RETURN p")

    def find_sessions(self, computer: str) -> list:
        if not self.connected:
            raise RuntimeError("Not connected")
        return self.client.run_cypher(f"MATCH (c:Computer {{name: '{computer}'}})-[:HasSession]->(u:User) RETURN u.name")

    def find_dcom_connections(self, computer: str) -> list:
        if not self.connected:
            raise RuntimeError("Not connected")
        return self.client.run_cypher(f"MATCH (c:Computer {{name: '{computer}'}})-[:MemberOf|DcomRights*1..]->(p) RETURN p.name")

    def find_kerberoastable(self) -> list:
        if not self.connected:
            raise RuntimeError("Not connected")
        return self.client.run_cypher("MATCH (u:User {hasspn: true}) RETURN u.name, u.samaccountname, u.serviceprincipalnames")

    def health(self) -> Dict[str, Any]:
        return {"connected": self.connected}
