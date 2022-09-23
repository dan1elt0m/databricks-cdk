import json
import logging
from typing import Optional

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, delete_request, get_request, patch_request, post_request

logger = logging.getLogger(__name__)


class Metastore(BaseModel):
    name: str
    storage_root: str
    owner: Optional[str]


class MetastoreProperties(BaseModel):
    workspace_url: str
    metastore: Metastore


class MetastoreResponse(CnfResponse):
    metastore_id: str
    global_metastore_id: str


def get_metastore_url(workspace_url: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/metastores"


def get_metastore_by_id(metastore_id: str, base_url: str) -> Optional[dict]:
    return get_request(f"{base_url}/{metastore_id}")


def get_metastore_by_name(metastore_name: str, base_url: str) -> Optional[dict]:
    results = get_request(base_url).get("metastores", [])
    for m in results:
        if m.get("name") == metastore_name:
            return m
    return None


def create_or_update_metastore(
    properties: MetastoreProperties, physical_resource_id: Optional[str]
) -> MetastoreResponse:
    """Create metastore at databricks"""
    current: Optional[dict] = None
    base_url = get_metastore_url(properties.workspace_url)
    if physical_resource_id is not None:
        current = get_metastore_by_id(physical_resource_id, base_url=base_url)
    if current is None:
        current = get_metastore_by_name(properties.metastore.name, base_url=base_url)
    if current is None:
        create_response = post_request(base_url, body=json.loads(properties.metastore.json()))
        metastore_id = create_response.get("metastore_id")
        global_metastore_id = create_response.get("global_metastore_id")
        return MetastoreResponse(
            metastore_id=metastore_id,
            global_metastore_id=global_metastore_id,
            physical_resource_id=metastore_id,
        )
    else:
        metastore_id = current.get("metastore_id")
        body = json.loads(properties.metastore.json())
        if current.get("storage_root") == f"{properties.metastore.storage_root}/{metastore_id}":
            del body["storage_root"]
        else:
            raise RuntimeError("storage_root can't be changed after first deployment")
        update_response = patch_request(f"{base_url}/{metastore_id}", body=body)
        global_metastore_id = update_response.get("global_metastore_id")
        return MetastoreResponse(
            metastore_id=metastore_id,
            global_metastore_id=global_metastore_id,
            physical_resource_id=metastore_id,
        )


def delete_metastore(properties: MetastoreProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes metastore at databricks"""
    base_url = get_metastore_url(properties.workspace_url)
    current = None
    if physical_resource_id is not None:
        current = get_metastore_by_id(physical_resource_id, base_url=base_url)
    if current is None:
        current = get_metastore_by_name(properties.metastore.name, base_url=base_url)
    if current is not None:
        metastore_id = current.get("metastore_id")
        delete_request(f"{base_url}/{metastore_id}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
